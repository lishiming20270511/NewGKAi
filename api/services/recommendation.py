"""
推荐引擎核心服务

实现 T2.4 (位次估算 + 四层填充) + T2.5 (概率计算) + T2.6 (16维度聚合)

数据流:
  estimate_rank → build_candidate_pool_four_tiers → batch_query_admission
  → calc_rank_prob → calc_weighted_prob → assign_tier
  → sort_and_slice → aggregate_16_dimensions → detect_data_gaps
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..redis_client import get_redis

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# 城市 → 省份映射表 (60+ 城市)
# ──────────────────────────────────────────────────────────────────────────────
CITY_TO_PROVINCE: dict[str, str] = {
    "北京": "北京", "上海": "上海", "天津": "天津", "重庆": "重庆",
    "广州": "广东", "深圳": "广东", "东莞": "广东", "佛山": "广东",
    "成都": "四川", "武汉": "湖北", "西安": "陕西", "南京": "江苏",
    "杭州": "浙江", "宁波": "浙江", "温州": "浙江", "苏州": "江苏",
    "无锡": "江苏", "南通": "江苏", "徐州": "江苏",
    "郑州": "河南", "洛阳": "河南", "开封": "河南",
    "长沙": "湖南", "合肥": "安徽", "福州": "福建", "厦门": "福建",
    "南昌": "江西", "济南": "山东", "青岛": "山东", "烟台": "山东",
    "哈尔滨": "黑龙江", "长春": "吉林", "沈阳": "辽宁", "大连": "辽宁",
    "石家庄": "河北", "保定": "河北", "唐山": "河北",
    "太原": "山西", "呼和浩特": "内蒙古", "南宁": "广西",
    "海口": "海南", "三亚": "海南", "贵阳": "贵州", "昆明": "云南",
    "西宁": "青海", "银川": "宁夏", "乌鲁木齐": "新疆",
    "兰州": "甘肃", "拉萨": "西藏",
    "济宁": "山东", "潍坊": "山东",
    "汕头": "广东", "珠海": "广东",
    "绍兴": "浙江", "金华": "浙江",
    "芜湖": "安徽", "蚌埠": "安徽",
    "泉州": "福建", "漳州": "福建",
    "赣州": "江西", "九江": "江西",
    "株洲": "湖南", "岳阳": "湖南",
    "宜昌": "湖北", "荆州": "湖北",
    "绵阳": "四川", "南充": "四川",
    "咸阳": "陕西", "宝鸡": "陕西",
}

# 城市 → 邻省映射（用于 L3）
CITY_NEIGHBOR_PROVINCES: dict[str, list[str]] = {
    "郑州": ["湖北", "陕西", "山西", "安徽", "山东"],
    "武汉": ["湖南", "河南", "安徽", "江西", "陕西"],
    "西安": ["四川", "河南", "山西", "甘肃", "湖北"],
    "成都": ["重庆", "云南", "贵州", "陕西"],
    "南京": ["安徽", "浙江", "上海", "山东"],
    "杭州": ["上海", "江苏", "安徽", "福建", "江西"],
    "广州": ["福建", "湖南", "广西", "江西", "海南"],
    "深圳": ["广东", "福建", "湖南"],
    "长沙": ["湖北", "江西", "广东", "广西", "贵州"],
    "合肥": ["江苏", "浙江", "江西", "湖北", "山东"],
    "南昌": ["湖北", "安徽", "浙江", "广东", "湖南"],
    "济南": ["河北", "河南", "安徽", "江苏"],
    "沈阳": ["吉林", "内蒙古", "河北"],
    "哈尔滨": ["吉林", "内蒙古"],
    "长春": ["黑龙江", "内蒙古", "辽宁"],
    "重庆": ["四川", "贵州", "云南", "湖北", "陕西"],
    "北京": ["河北", "天津", "山西"],
    "上海": ["江苏", "浙江"],
    "天津": ["河北", "北京"],
    "石家庄": ["山西", "北京", "天津", "山东", "河南"],
}

# 省份 → 沿海/优先扩展省份
PROVINCE_EXPAND: dict[str, list[str]] = {
    "河南": ["湖北", "陕西", "安徽", "山东", "河北", "江苏", "浙江"],
    "湖北": ["河南", "湖南", "安徽", "江西", "四川", "陕西"],
    "四川": ["重庆", "云南", "贵州", "陕西", "湖北"],
    "山东": ["江苏", "河北", "安徽", "河南"],
    "广东": ["湖南", "福建", "广西", "江西"],
    "江苏": ["上海", "浙江", "安徽", "山东"],
    "浙江": ["上海", "江苏", "安徽", "福建"],
    "河北": ["北京", "天津", "山西", "辽宁", "山东"],
    "陕西": ["河南", "四川", "甘肃", "山西", "湖北"],
    "安徽": ["江苏", "浙江", "湖北", "河南", "江西"],
}

# Tier 阈值
TIER_BOOST_MIN = 30.0
TIER_SOLID_MIN = 60.0
TIER_SAFE_MIN = 85.0
LOW_SCORE_BOUNDARY = 400
LOW_SCORE_TIER_MIN = 5.0


# ──────────────────────────────────────────────────────────────────────────────
# 数据结构
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class SchoolRecord:
    school_id: int
    name: str
    province: str
    city: str
    level: str
    school_type: str
    is_985: bool
    is_211: bool
    is_double_first: bool
    is_intended: bool = False
    is_intended_city: bool = False

    # 填充于 PHASE 2
    rank_prob: Optional[float] = None
    weighted_prob: Optional[float] = None
    tier: Optional[int] = None          # 0=冲刺 1=稳妥 2=保底
    tier_label: Optional[str] = None
    admission_data: dict = field(default_factory=dict)
    dimensions: dict = field(default_factory=dict)
    data_quality: str = "no_data"


@dataclass
class RecommendRequest:
    province: str
    score: int
    subject_category: str           # 理科/文科/物理/历史/综合
    rank: Optional[int] = None
    city_preference: list[str] = field(default_factory=list)
    intended_schools: list[str] = field(default_factory=list)
    major_preference: list[str] = field(default_factory=list)
    personality: list[str] = field(default_factory=list)
    economic_level: str = "一般"    # 较为困难/一般/良好/比较优越


# ──────────────────────────────────────────────────────────────────────────────
# PHASE 0: 位次估算
# ──────────────────────────────────────────────────────────────────────────────

async def estimate_rank(
    province: str, score: int, category: str, db: AsyncSession
) -> Optional[int]:
    cache_key = f"recommend:rank:{province}:2025:{category}:{score}"
    try:
        r = get_redis()
        cached = await r.get(cache_key)
        if cached:
            return int(cached)
    except Exception:
        r = None

    # Category fallback order: exact match → 综合
    # Old gaokao: 理科/文科; new gaokao: 物理/历史; combined: 综合
    _CAT_MAP = {"理科": "物理", "文科": "历史"}
    categories_to_try = [category]
    if category != "综合":
        mapped = _CAT_MAP.get(category)
        if mapped and mapped != category:
            categories_to_try.append(mapped)
        categories_to_try.append("综合")

    for year in [2025, 2024, 2023]:
        for cat in categories_to_try:
            row = await db.execute(
                text("""
                    SELECT cumulative_count FROM yifenyidang
                    WHERE province = :prov AND year = :yr
                      AND category = :cat AND score <= :score
                    ORDER BY score DESC LIMIT 1
                """),
                {"prov": province, "yr": year, "cat": cat, "score": score},
            )
            result = row.mappings().first()
            if result:
                rank = int(result["cumulative_count"])
                try:
                    if r:
                        await r.setex(cache_key, 86400, str(rank))
                except Exception:
                    pass
                return rank
    return None


# ──────────────────────────────────────────────────────────────────────────────
# PHASE 1: 候选池四层填充
# ──────────────────────────────────────────────────────────────────────────────

def _extract_city(name: str) -> str:
    import re
    patterns = [
        # 直辖市 (4)
        r"^(北京|上海|天津|重庆)",
        # 省会 + 计划单列市 + 主要城市 (~70)
        r"^(哈尔滨|长春|沈阳|大连|石家庄|济南|青岛|郑州|南京|杭州|武汉|成都|西安"
        r"|广州|深圳|南昌|合肥|福州|厦门|长沙|昆明|贵阳|南宁|海口|太原|呼和浩特"
        r"|西宁|银川|乌鲁木齐|兰州|徐州|苏州|无锡|宁波|温州|汕头"
        # 河南地级市
        r"|洛阳|开封|焦作|新乡|信阳|南阳|安阳|平顶山|许昌|商丘|周口|驻马店|漯河|濮阳|鹤壁|三门峡"
        # 湖北地级市
        r"|宜昌|荆州|黄石|襄阳|十堰|孝感|黄冈|荆门|咸宁|鄂州|随州"
        # 湖南地级市
        r"|株洲|岳阳|湘潭|衡阳|邵阳|常德|郴州|永州|怀化|娄底|益阳|吉首"
        # 四川地级市
        r"|绵阳|南充|自贡|泸州|德阳|乐山|宜宾|达州|广元|遂宁|内江|攀枝花"
        # 安徽地级市
        r"|芜湖|蚌埠|马鞍山|安庆|黄山|滁州|六安|淮北|铜陵|宣城|池州|亳州"
        # 福建地级市
        r"|泉州|漳州|龙岩|三明|南平|莆田"
        # 江西地级市
        r"|赣州|九江|宜春|景德镇|萍乡|吉安|上饶|抚州|新余"
        # 陕西地级市
        r"|咸阳|宝鸡|渭南|汉中|延安|安康|榆林|商洛"
        # 山东地级市
        r"|济宁|潍坊|临沂|泰安|淄博|聊城|日照|德州|滨州|菏泽|枣庄|东营|威海"
        # 江苏地级市
        r"|常州|南通|扬州|镇江|泰州|盐城|淮安|连云港|宿迁"
        # 浙江地级市
        r"|嘉兴|湖州|绍兴|金华|衢州|舟山|台州|丽水"
        # 广东地级市
        r"|东莞|佛山|中山|珠海|惠州|江门|肇庆|茂名|湛江|梅州|韶关|清远|揭阳|潮州|阳江|河源|汕尾|云浮"
        # 辽宁地级市
        r"|鞍山|抚顺|本溪|锦州|丹东|营口|辽阳|盘锦|铁岭|朝阳|葫芦岛"
        # 吉林地级市
        r"|吉林|四平|通化|延吉|松原|白城|辽源|白山"
        # 黑龙江地级市
        r"|大庆|齐齐哈尔|牡丹江|佳木斯|鸡西|鹤岗|双鸭山|伊春|七台河|黑河|绥化"
        # 河北地级市
        r"|保定|唐山|廊坊|承德|沧州|邯郸|邢台|秦皇岛|衡水|张家口"
        # 山西地级市
        r"|大同|长治|临汾|运城|晋中|吕梁|晋城|朔州|忻州"
        # 广西地级市
        r"|桂林|柳州|玉林|北海|梧州|钦州|贵港|百色|河池"
        # 贵州地级市
        r"|遵义|毕节|铜仁|六盘水|安顺"
        # 云南地级市
        r"|大理|曲靖|玉溪|丽江|保山|昭通|普洱|临沧|红河|文山|楚雄"
        # 甘肃地级市
        r"|天水|酒泉|武威|平凉|张掖|庆阳|陇南|白银|定西"
        # 内蒙古地级市
        r"|包头|赤峰|鄂尔多斯|通辽|呼伦贝尔|乌兰察布|巴彦淖尔|乌海"
        # 新疆地级市 (非自治区首府)
        r"|石河子|克拉玛依|昌吉|伊宁|库尔勒|喀什|阿克苏)"
        # Special: 三字城市名 (3-char cities)
        r"^(秦皇岛|驻马店|平顶山|三门峡|哈尔滨|景德镇|连云港|张家口|马鞍山|"
        r"攀枝花|六盘水|牡丹江|佳木斯|齐齐哈尔|呼和浩特|乌鲁木齐|石河子|呼伦贝尔|"
        r"鄂尔多斯|巴彦淖尔|克拉玛依|乌兰察布)",
    ]
    for p in patterns:
        m = re.match(p, name)
        if m:
            return m.group(0)
    return ""


def _get_city_provinces(cities: list[str]) -> list[str]:
    provinces = []
    for c in cities:
        if c in CITY_TO_PROVINCE:
            pv = CITY_TO_PROVINCE[c]
            if pv not in provinces:
                provinces.append(pv)
    return provinces


def _get_neighbor_provinces(cities: list[str], exclude: list[str]) -> list[str]:
    seen = set(exclude)
    result = []
    for c in cities:
        for pv in CITY_NEIGHBOR_PROVINCES.get(c, []):
            if pv not in seen:
                seen.add(pv)
                result.append(pv)
    return result


async def _fetch_schools_by_provinces(
    provinces: list[str], db: AsyncSession, exclude_ids: set[int]
) -> list[SchoolRecord]:
    if not provinces:
        return []
    placeholders = ", ".join(f":p{i}" for i in range(len(provinces)))
    params = {f"p{i}": p for i, p in enumerate(provinces)}
    rows = await db.execute(
        text(f"""
            SELECT school_id, name, province, level, school_type,
                   is_985, is_211, is_double_first
            FROM schools
            WHERE province IN ({placeholders})
            ORDER BY is_985 DESC, is_211 DESC, is_double_first DESC
            LIMIT 300
        """),
        params,
    )
    result = []
    for r in rows.mappings():
        if r["school_id"] in exclude_ids:
            continue
        result.append(SchoolRecord(
            school_id=r["school_id"],
            name=r["name"],
            province=r["province"],
            city=_extract_city(r["name"]) or r["province"],
            level=r["level"] or "",
            school_type=r["school_type"] or "",
            is_985=bool(r["is_985"]),
            is_211=bool(r["is_211"]),
            is_double_first=bool(r["is_double_first"]),
        ))
    return result


async def build_candidate_pool(
    req: RecommendRequest, db: AsyncSession
) -> tuple[list[SchoolRecord], list[SchoolRecord]]:
    """
    Returns (special_attention, candidate_pool_15)
    special_attention: intended schools, shown independently
    candidate_pool_15: up to 15 schools for recommendation
    """
    # ── 特别关注区：精确名称匹配意向学校 ──
    special_attention: list[SchoolRecord] = []
    intended_ids: set[int] = set()
    for school_name in req.intended_schools:
        row = await db.execute(
            text("""
                SELECT school_id, name, province, level, school_type,
                       is_985, is_211, is_double_first
                FROM schools WHERE name = :name LIMIT 1
            """),
            {"name": school_name},
        )
        r = row.mappings().first()
        if r:
            sr = SchoolRecord(
                school_id=r["school_id"],
                name=r["name"],
                province=r["province"],
                city=_extract_city(r["name"]) or r["province"],
                level=r["level"] or "",
                school_type=r["school_type"] or "",
                is_985=bool(r["is_985"]),
                is_211=bool(r["is_211"]),
                is_double_first=bool(r["is_double_first"]),
                is_intended=True,
            )
            special_attention.append(sr)
            intended_ids.add(r["school_id"])

    # ── 四层填充推荐池 ──
    seen_ids = set(intended_ids)
    pool: list[SchoolRecord] = []

    # L1 意向城市
    city_provinces = _get_city_provinces(req.city_preference)
    l1_schools = await _fetch_schools_by_provinces(city_provinces, db, seen_ids)
    for s in l1_schools:
        s.is_intended_city = True
        pool.append(s)
        seen_ids.add(s.school_id)

    # L2 本省
    if req.province not in city_provinces:
        l2_schools = await _fetch_schools_by_provinces([req.province], db, seen_ids)
        pool.extend(l2_schools)
        for s in l2_schools:
            seen_ids.add(s.school_id)

    # L3 邻省
    neighbor_provs = _get_neighbor_provinces(req.city_preference, list(seen_ids))
    if not neighbor_provs:
        # Fallback: use province expand table
        neighbor_provs = [p for p in PROVINCE_EXPAND.get(req.province, []) if p not in city_provinces]
    l3_schools = await _fetch_schools_by_provinces(neighbor_provs[:4], db, seen_ids)
    pool.extend(l3_schools)
    for s in l3_schools:
        seen_ids.add(s.school_id)

    # L4 全国兜底 (up to 105 candidates total)
    if len(pool) < 105:
        needed = 105 - len(pool)
        exclude_provs = city_provinces + [req.province] + neighbor_provs
        all_rows = await db.execute(
            text("""
                SELECT school_id, name, province, level, school_type,
                       is_985, is_211, is_double_first
                FROM schools
                ORDER BY is_985 DESC, is_211 DESC, is_double_first DESC
                LIMIT :lim
            """),
            {"lim": needed + len(seen_ids) + 50},
        )
        for r in all_rows.mappings():
            if r["school_id"] in seen_ids:
                continue
            if r["province"] in exclude_provs:
                continue
            pool.append(SchoolRecord(
                school_id=r["school_id"],
                name=r["name"],
                province=r["province"],
                city=_extract_city(r["name"]) or r["province"],
                level=r["level"] or "",
                school_type=r["school_type"] or "",
                is_985=bool(r["is_985"]),
                is_211=bool(r["is_211"]),
                is_double_first=bool(r["is_double_first"]),
            ))
            seen_ids.add(r["school_id"])
            if len(pool) >= 105:
                break

    return special_attention, pool[:105]


# ──────────────────────────────────────────────────────────────────────────────
# PHASE 2a: 批量查询录取数据
# ──────────────────────────────────────────────────────────────────────────────

async def batch_query_admission(
    school_ids: list[int], province: str, db: AsyncSession
) -> dict[int, list[dict]]:
    """Returns {school_id: [{year, min_rank, min_score, batch}, ...]}"""
    if not school_ids:
        return {}

    result: dict[int, list[dict]] = {sid: [] for sid in school_ids}
    cached_ids: set[int] = set()

    # Try L1 Redis cache per school
    try:
        r = get_redis()
        for sid in school_ids:
            ck = f"recommend:admission:{province}:{sid}"
            val = await r.get(ck)
            if val:
                result[sid] = json.loads(val)
                cached_ids.add(sid)
    except Exception:
        pass

    remaining = [sid for sid in school_ids if sid not in cached_ids]
    if not remaining:
        return result

    placeholders = ", ".join(f":id{i}" for i in range(len(remaining)))
    params = {f"id{i}": v for i, v in enumerate(remaining)}
    params["prov"] = province

    rows = await db.execute(
        text(f"""
            SELECT school_id, year, min_rank, min_score, batch
            FROM admission_history
            WHERE school_id IN ({placeholders})
              AND province = :prov
              AND year >= 2022
            ORDER BY school_id, year DESC
        """),
        params,
    )
    for row in rows.mappings():
        sid = row["school_id"]
        result[sid].append({
            "year": row["year"],
            "min_rank": row["min_rank"],
            "min_score": row["min_score"],
            "batch": row["batch"],
        })

    # Cache results
    try:
        r = get_redis()
        for sid in remaining:
            if result[sid]:
                ck = f"recommend:admission:{province}:{sid}"
                await r.setex(ck, 3600, json.dumps(result[sid]))
    except Exception:
        pass

    return result


# ──────────────────────────────────────────────────────────────────────────────
# PHASE 2b-2c: 概率计算
# ──────────────────────────────────────────────────────────────────────────────

def calc_rank_prob(student_rank: int, history: list[dict]) -> Optional[float]:
    if not history or student_rank is None:
        return None

    years = sorted(history, key=lambda x: x["year"], reverse=True)[:3]
    ranks = [y["min_rank"] for y in years if y.get("min_rank") and y["min_rank"] > 0]
    if not ranks:
        return None

    # Use median for stability
    ranks_sorted = sorted(ranks)
    school_rank = ranks_sorted[len(ranks_sorted) // 2]

    if student_rank <= school_rank:
        # Student rank is better — high probability
        gap_ratio = (school_rank - student_rank) / school_rank
        prob = 85.0 + gap_ratio * 14.0
    else:
        # Student rank is worse — linear decay
        prob = 85.0 * (school_rank / student_rank)

    # Trend adjustment: if min_rank has been tightening year-over-year
    if len(years) >= 2:
        latest = years[0].get("min_rank")
        oldest = years[-1].get("min_rank")
        if latest and oldest and latest < oldest:
            prob *= 0.95  # Tightening trend → -5%

    return max(1.0, min(99.0, prob))


def _major_match_score(major_preference: list[str], school: SchoolRecord) -> float:
    """Returns 0-20 (percentage) based on major match quality."""
    if not major_preference:
        return 10.0  # Neutral when no preference
    # In MVP without major_ranks data, use school tier as proxy
    if school.is_985:
        return 18.0
    if school.is_211 or school.is_double_first:
        return 15.0
    return 10.0


def _employment_score(school: SchoolRecord) -> float:
    """Returns 0-15 (percentage). Without employment_data, use school tier as proxy."""
    if school.is_985:
        return 14.0
    if school.is_211:
        return 12.0
    if school.is_double_first:
        return 11.0
    return 9.0


def _city_pref_score(school: SchoolRecord, city_preference: list[str]) -> float:
    """Returns 0-10 (percentage)."""
    if not city_preference:
        return 5.0
    city = school.city or school.province
    if any(city in cp or cp in city for cp in city_preference):
        return 10.0
    if school.is_intended_city:
        return 8.0
    return 3.0


def _personality_score(school: SchoolRecord, personality: list[str]) -> float:
    """Returns 0-10 (percentage) based on personality vs school type."""
    if not personality:
        return 5.0
    stype = (school.school_type or "").lower() + school.name.lower()
    score = 5.0
    for trait in personality:
        if trait in ("外向活泼", "社交沟通", "领导管理"):
            if any(k in stype for k in ("综合", "文", "师范", "财经", "政法", "语言")):
                score = 10.0
        elif trait in ("沉稳内敛", "逻辑分析", "钻研学术"):
            if any(k in stype for k in ("理工", "工业", "科技", "理学", "工学")):
                score = 10.0
        elif trait == "艺术创作":
            if any(k in stype for k in ("艺术", "设计", "传媒", "美")):
                score = 10.0
        elif trait == "动手实践":
            if any(k in stype for k in ("工业", "工程", "应用", "职业", "技术")):
                score = 10.0
    return score


def _economic_score(school: SchoolRecord, economic_level: str) -> float:
    """Returns 0-10 (percentage) based on economic fit."""
    if economic_level == "较为困难":
        sname = school.name.lower()
        stype = (school.school_type or "").lower()
        if "师范" in sname or "师范" in stype:
            return 10.0
        # Public schools assumed lower tuition
        if "公办" in stype or school.is_985 or school.is_211:
            return 8.0
        return 5.0
    return 5.0  # Neutral for other economic levels


def calc_weighted_prob(
    req: RecommendRequest, rank_prob: float, school: SchoolRecord
) -> float:
    major = _major_match_score(req.major_preference, school)
    employ = _employment_score(school)
    city = _city_pref_score(school, req.city_preference)
    personality = _personality_score(school, req.personality)
    economic = _economic_score(school, req.economic_level)

    weighted = (
        rank_prob * 0.35
        + major * (100 / 20) * 0.20
        + employ * (100 / 15) * 0.15
        + city * (100 / 10) * 0.10
        + personality * (100 / 10) * 0.10
        + economic * (100 / 10) * 0.10
    )
    return max(1.0, min(99.0, round(weighted, 1)))


# ──────────────────────────────────────────────────────────────────────────────
# PHASE 3: Tier分层
# ──────────────────────────────────────────────────────────────────────────────

def assign_tier(rank_prob: float, score: int) -> tuple[int, str]:
    low_score = score < LOW_SCORE_BOUNDARY
    boost_min = LOW_SCORE_TIER_MIN if low_score else TIER_BOOST_MIN

    if boost_min <= rank_prob < TIER_SOLID_MIN:
        return 0, "冲刺"
    elif TIER_SOLID_MIN <= rank_prob < TIER_SAFE_MIN:
        return 1, "稳妥"
    elif rank_prob >= TIER_SAFE_MIN:
        return 2, "保底"
    else:
        return 0, "冲刺"  # Below threshold → treat as aggressive pick


# ──────────────────────────────────────────────────────────────────────────────
# PHASE 4: 排序 + 选15所
# ──────────────────────────────────────────────────────────────────────────────

def sort_and_slice(schools: list[SchoolRecord], personality: list[str]) -> list[SchoolRecord]:
    """Guarantees 5+5+5 tier distribution. When a tier is short, fills from
    adjacent tiers (closest rankProb match) to maintain the 15-school count."""
    def sort_key(s: SchoolRecord):
        tier = s.tier if s.tier is not None else 3
        intended_city_flag = 0 if s.is_intended_city else 1
        rank_prob_neg = -(s.rank_prob or 0)
        personality_neg = -_personality_score(s, personality)
        weighted_neg = -(s.weighted_prob or 0)
        return (tier, intended_city_flag, rank_prob_neg, personality_neg, weighted_neg)

    schools_sorted = sorted(schools, key=sort_key)

    # Group by tier (sorted within each tier by preference)
    tiers: dict[int, list[SchoolRecord]] = {0: [], 1: [], 2: []}
    for s in schools_sorted:
        t = s.tier if s.tier is not None else 0
        tiers[t].append(s)

    selected: list[SchoolRecord] = []
    used_ids: set[int] = set()

    def _take(tier_list: list[SchoolRecord], n: int) -> list[SchoolRecord]:
        result = []
        for s in tier_list:
            if s.school_id in used_ids:
                continue
            result.append(s)
            used_ids.add(s.school_id)
            if len(result) >= n:
                break
        return result

    # Tier 0: 冲刺 (5) — shortfall filled from tier 1
    selected += _take(tiers[0], 5)
    if len(selected) < 5:
        selected += _take(tiers[1], 5 - len(selected))

    # Tier 1: 稳妥 (5) — shortfall filled from tier 2, then tier 0 remaining
    solid_taken = _take(tiers[1], 5)
    if len(solid_taken) < 5:
        solid_taken += _take(tiers[2], 5 - len(solid_taken))
    if len(solid_taken) < 5:
        solid_taken += _take(tiers[0], 5 - len(solid_taken))
    selected += solid_taken

    # Tier 2: 保底 (5) — shortfall filled from tier 1 remaining, then tier 0
    safe_taken = _take(tiers[2], 5)
    if len(safe_taken) < 5:
        safe_taken += _take(tiers[1], 5 - len(safe_taken))
    if len(safe_taken) < 5:
        safe_taken += _take(tiers[0], 5 - len(safe_taken))
    selected += safe_taken

    # Final fallback: if still < 15, fill from any remaining school
    if len(selected) < 15:
        for t in [0, 1, 2]:
            for s in tiers[t]:
                if s.school_id in used_ids:
                    continue
                selected.append(s)
                used_ids.add(s.school_id)
                if len(selected) >= 15:
                    break
            if len(selected) >= 15:
                break

    return selected[:15]


# ──────────────────────────────────────────────────────────────────────────────
# PHASE 2d / T2.6: 16维度数据聚合
# ──────────────────────────────────────────────────────────────────────────────

# Fallback city descriptions (used when city_analysis table has no data)
_CITY_ANALYSIS_FALLBACK: dict[str, str] = {
    "北京": "北京(超一线)，政治/科技/文化中心，就业最广，起薪高，消费高，留存率≥70%",
    "上海": "上海(超一线)，金融/贸易/互联网中心，外资机会多，起薪高，消费极高",
    "广州": "广州(一线)，商贸/制造业/互联网，外贸机会多，气候宜人，生活成本中高",
    "深圳": "深圳(一线)，科技/互联网/金融，创业氛围浓，高薪，生活成本高",
    "成都": "成都(新一线)，科技/电子/游戏/文创，宜居，生活成本适中，留存率高",
    "武汉": "武汉(新一线)，光电/汽车/互联网，理工科需求旺，起薪适中",
    "西安": "西安(新一线)，航空航天/军工/软件，高校密集，就业竞争激烈但成本低",
    "南京": "南京(新一线)，电子信息/软件/化工，国企机会多，江苏经济强",
    "杭州": "杭州(新一线)，互联网/电商/金融科技，阿里系生态，薪资水平高",
    "郑州": "郑州(新一线)，物流/电商/食品/交通枢纽，发展快速，生活成本低",
    "长沙": "长沙(新一线)，传媒/娱乐/工程机械，生活气息浓，幸福感高，起薪适中",
    "重庆": "重庆(直辖市)，制造业/汽车/化工，西部经济中心，生活成本低",
}


async def aggregate_16_dimensions(
    school: SchoolRecord, history: list[dict], req: RecommendRequest, db: AsyncSession
) -> dict:
    dims: dict = {}

    # ── 维度1-6,9: 基于录取历史数据 ──────────────────────────────────────────
    if history:
        years = sorted(history, key=lambda x: x["year"], reverse=True)
        latest = years[0]
        dims["latest_year"] = latest["year"]
        dims["latest_min_rank"] = latest.get("min_rank")
        dims["latest_min_score"] = latest.get("min_score")

        scores = [y["min_score"] for y in years if y.get("min_score")]
        if len(scores) >= 2:
            diff = scores[0] - scores[-1]
            if diff > 3:
                trend, trend_detail = "rising", f"分数线逐年上升 (+{diff}分趋势)"
            elif diff < -3:
                trend, trend_detail = "falling", f"分数线逐年下降 (-{abs(diff)}分趋势)"
            else:
                trend, trend_detail = "stable", "分数线近年稳定"
        else:
            trend, trend_detail = "unknown", "数据不足，趋势未知"
        dims["trend"] = trend
        dims["trend_detail"] = trend_detail
        dims["years_available"] = sorted([y["year"] for y in years], reverse=True)
    else:
        dims["trend"] = "unknown"
        dims["trend_detail"] = "暂无录取数据"
        dims["years_available"] = []

    dims["admission_trend"] = dims.get("trend_detail", "数据不足")

    # ── 维度7: 推荐专业（school_majors + major_similarity 映射）─────────────
    recommended_major = None
    major_match_type = "none"
    if req.major_preference:
        for pref in req.major_preference:
            # 1) 精确匹配该校专业
            r7 = await db.execute(
                text("""
                    SELECT major_name, major_level FROM school_majors
                    WHERE school_id = :sid AND major_name = :major LIMIT 1
                """),
                {"sid": school.school_id, "major": pref},
            )
            exact = r7.mappings().first()
            if exact:
                recommended_major = exact["major_name"]
                dims["major_level"] = exact["major_level"] or "普通"
                major_match_type = "exact"
                break

            # 2) 相似专业映射
            r7s = await db.execute(
                text("""
                    SELECT ms.target_major, ms.similarity, sm.major_level
                    FROM major_similarity ms
                    LEFT JOIN school_majors sm
                        ON sm.school_id = :sid AND sm.major_name = ms.target_major
                    WHERE ms.source_major = :major AND sm.school_id IS NOT NULL
                    ORDER BY ms.similarity DESC LIMIT 1
                """),
                {"sid": school.school_id, "major": pref},
            )
            similar = r7s.mappings().first()
            if similar:
                recommended_major = similar["target_major"]
                dims["major_similarity"] = float(similar["similarity"])
                dims["major_level"] = similar["major_level"] or "普通"
                major_match_type = "similar"
                dims["major_note"] = f"相近专业（与{pref}相似度{int(float(similar['similarity'])*100)}%）"
                break

        # 3) Fallback: 该校任意专业
        if not recommended_major:
            r7f = await db.execute(
                text("SELECT major_name FROM school_majors WHERE school_id = :sid LIMIT 1"),
                {"sid": school.school_id},
            )
            row_f = r7f.mappings().first()
            if row_f:
                recommended_major = row_f["major_name"]
                major_match_type = "fallback"

    dims["recommended_major"] = recommended_major or req.major_preference[0] if req.major_preference else "综合类专业"
    dims["major_match_type"] = major_match_type

    # ── 维度8: 学费（school_tuition，冷门院校显示"查询中"）──────────────────
    tuition_major = recommended_major or "__default__"
    r8 = await db.execute(
        text("""
            SELECT tuition_per_year, duration_years, data_source, data_year
            FROM school_tuition
            WHERE school_id = :sid
              AND (major_name = :major OR major_name = '__default__')
            ORDER BY (major_name = :major) DESC, data_year DESC
            LIMIT 1
        """),
        {"sid": school.school_id, "major": tuition_major},
    )
    tuition_row = r8.mappings().first()
    if tuition_row:
        per_yr = tuition_row["tuition_per_year"]
        yrs = tuition_row["duration_years"] or 4
        total = per_yr * yrs
        dims["tuition"] = f"{per_yr:,}元/年"
        dims["tuition_total"] = f"{yrs}年约{total//10000:.1f}万" if total >= 10000 else f"{yrs}年约{total:,}元"
        dims["tuition_fit"] = _tuition_fit(per_yr, req.economic_level)
        dims["tuition_source"] = tuition_row["data_source"] or "官网"
        dims["tuition_year"] = tuition_row["data_year"]
        dims["tuition_data_quality"] = "real"
    else:
        # Fallback estimates until crawler fills the gap
        stype = (school.school_type or "").lower()
        if "公办" in stype or school.is_985 or school.is_211:
            dims["tuition"] = "4500-6000元/年"
            dims["tuition_total"] = "4年约2-2.4万"
            dims["tuition_fit"] = "中等家庭可接受"
        elif "民办" in stype or "独立学院" in stype:
            dims["tuition"] = "15000-30000元/年"
            dims["tuition_total"] = "4年约6-12万"
            dims["tuition_fit"] = "需考虑家庭经济承受能力"
        else:
            dims["tuition"] = "5000-8000元/年"
            dims["tuition_total"] = "4年约2-3.2万"
            dims["tuition_fit"] = "中等家庭可接受"
        dims["tuition_data_quality"] = "estimated"

    # ── 维度11: 就业率（school_employment）───────────────────────────────────
    r11 = await db.execute(
        text("""
            SELECT employment_rate, graduate_rate, data_source, data_year
            FROM school_employment WHERE school_id = :sid
        """),
        {"sid": school.school_id},
    )
    emp = r11.mappings().first()
    if emp and emp["employment_rate"] is not None:
        er = emp["employment_rate"]
        gr = emp["graduate_rate"]
        yr = emp["data_year"] or "未知"
        src = emp["data_source"] or "学校官网"
        dims["employment_rate"] = f"{er:.1f}%"
        dims["graduate_rate"] = f"{gr:.1f}%" if gr is not None else None
        dims["employment_source"] = f"{src}·{yr}年数据"
        dims["employment_data_quality"] = "real"
    else:
        if school.is_985:
            dims["employment_rate"] = "92-97%"
        elif school.is_211:
            dims["employment_rate"] = "88-94%"
        else:
            dims["employment_rate"] = "82-90%"
        dims["employment_source"] = "按院校层次估算"
        dims["employment_data_quality"] = "estimated"

    # ── 维度12-13: 薪资数据（school_salary）──────────────────────────────────
    r12 = await db.execute(
        text("""
            SELECT salary_start_min, salary_start_max, salary_3yr_min, salary_3yr_max,
                   data_source, data_year
            FROM school_salary
            WHERE school_id = :sid
              AND (major_name = :major OR major_name = '__default__')
            ORDER BY (major_name = :major) DESC, data_year DESC
            LIMIT 1
        """),
        {"sid": school.school_id, "major": recommended_major or "__default__"},
    )
    sal = r12.mappings().first()
    if sal and sal["salary_start_min"] is not None:
        s_min, s_max = sal["salary_start_min"], sal["salary_start_max"] or sal["salary_start_min"]
        t_min = sal["salary_3yr_min"]
        t_max = sal["salary_3yr_max"] or (t_min if t_min else None)
        yr = sal["data_year"] or "未知"
        dims["avg_salary_start"] = f"{s_min//100*100}-{s_max//100*100}元/月" if s_min != s_max else f"{s_min}元/月"
        dims["avg_salary_3yr"] = f"{t_min//100*100}-{t_max//100*100}元/月" if (t_min and t_max and t_min != t_max) else (f"{t_min}元/月" if t_min else "–")
        dims["salary_source"] = f"{sal['data_source'] or '第三方调研'}·{yr}年数据"
        dims["salary_data_quality"] = "real"
    else:
        if school.is_985:
            dims["avg_salary_start"] = "8000-14000元/月"
            dims["avg_salary_3yr"] = "15000-25000元/月"
        elif school.is_211:
            dims["avg_salary_start"] = "6500-11000元/月"
            dims["avg_salary_3yr"] = "12000-18000元/月"
        else:
            dims["avg_salary_start"] = "4500-7000元/月"
            dims["avg_salary_3yr"] = "7000-12000元/月"
        dims["salary_source"] = "按院校层次估算"
        dims["salary_data_quality"] = "estimated"

    dims["core_positions"] = "见该校就业报告"
    dims["trend_5yr"] = "数据收集中"

    # ── 维度15: 城市分析（city_analysis 表）─────────────────────────────────
    city = school.city or school.province
    r15 = await db.execute(
        text("""
            SELECT location, advantage, development, main_business, city_level
            FROM city_analysis WHERE city_name = :city
        """),
        {"city": city},
    )
    ca = r15.mappings().first()
    if ca:
        city_level = ca["city_level"] or "二线"
        dims["city_analysis"] = {
            "location": ca["location"],
            "advantage": ca["advantage"],
            "disadvantage": ca["development"],
            "job_market": ca["main_business"],
            "livability": f"{city_level}城市，生活成本{'较高' if city_level == '一线' else '适中' if city_level == '新一线' else '较低'}，宜居指数{'良好' if city_level in ('一线', '新一线') else '稳定'}",
            "city_level": city_level,
        }
        dims["city_data_quality"] = "real"
    else:
        fallback = _CITY_ANALYSIS_FALLBACK.get(city, f"{city}，城市发展稳定，就业机会适中")
        dims["city_analysis"] = {"summary": fallback}
        dims["city_data_quality"] = "estimated"

    # ── 维度16: AI点评 (异步生成，MVP先返回null) ──────────────────────────────
    dims["ai_review"] = None

    return dims


# ──────────────────────────────────────────────────────────────────────────────
# BATCHED 16-dimension aggregation — replaces per-school N+1 queries
# ──────────────────────────────────────────────────────────────────────────────

async def batch_aggregate_dimensions(
    schools: list[SchoolRecord],
    admission_map: dict[int, list[dict]],
    req: RecommendRequest,
    db: AsyncSession,
) -> None:
    """Batch all per-table queries into 6 round-trips instead of 6×N."""
    if not schools:
        return
    sids = [s.school_id for s in schools]
    sid_set = set(sids)
    major_pref = req.major_preference

    # ── 1) school_majors (batch) ──
    placeholders = ", ".join(f":id{i}" for i in range(len(sids)))
    params = {f"id{i}": v for i, v in enumerate(sids)}
    rows = await db.execute(
        text(f"SELECT school_id, major_name, major_level FROM school_majors WHERE school_id IN ({placeholders})"),
        params,
    )
    majors_by_school: dict[int, list[dict]] = {sid: [] for sid in sid_set}
    for r in rows.mappings():
        majors_by_school.setdefault(r["school_id"], []).append(dict(r))

    # ── 2) major_similarity (batch — all source_major x all sids) ──
    similarity_map: dict[tuple[int, str], dict] = {}
    if major_pref:
        # We need: for each (school_id, source_major), find best similar target
        # Batch: JOIN school_majors ON major_similarity.target_major = school_majors.major_name
        # WHERE school_majors.school_id IN (...) AND major_similarity.source_major IN (...)
        mplaceholders = ", ".join(f":m{i}" for i in range(len(major_pref)))
        sparams = {**params, **{f"m{i}": v for i, v in enumerate(major_pref)}}
        sim_rows = await db.execute(
            text(f"""
                SELECT sm.school_id, ms.source_major, ms.target_major, ms.similarity, sm.major_level
                FROM major_similarity ms
                JOIN school_majors sm ON sm.major_name = ms.target_major
                WHERE sm.school_id IN ({placeholders})
                  AND ms.source_major IN ({mplaceholders})
                ORDER BY ms.similarity DESC
            """),
            sparams,
        )
        for r in sim_rows.mappings():
            key = (r["school_id"], r["source_major"])
            if key not in similarity_map:
                similarity_map[key] = dict(r)

    # ── 3) school_tuition (batch) ──
    trows = await db.execute(
        text(f"""
            SELECT school_id, major_name, tuition_per_year, duration_years, data_source, data_year
            FROM school_tuition WHERE school_id IN ({placeholders})
        """),
        params,
    )
    tuition_by_school: dict[int, list[dict]] = {sid: [] for sid in sid_set}
    for r in trows.mappings():
        tuition_by_school.setdefault(r["school_id"], []).append(dict(r))

    # ── 4) school_employment (batch) ──
    erows = await db.execute(
        text(f"""
            SELECT school_id, employment_rate, graduate_rate, data_source, data_year
            FROM school_employment WHERE school_id IN ({placeholders})
        """),
        params,
    )
    emp_by_school: dict[int, dict] = {}
    for r in erows.mappings():
        emp_by_school.setdefault(r["school_id"], dict(r))

    # ── 5) school_salary (batch) ──
    srows = await db.execute(
        text(f"""
            SELECT school_id, major_name, salary_start_min, salary_start_max,
                   salary_3yr_min, salary_3yr_max, data_source, data_year
            FROM school_salary WHERE school_id IN ({placeholders})
        """),
        params,
    )
    salary_by_school: dict[int, list[dict]] = {sid: [] for sid in sid_set}
    for r in srows.mappings():
        salary_by_school.setdefault(r["school_id"], []).append(dict(r))

    # ── 6) city_analysis (batch — by city name) ──
    cities = list({s.city or s.province for s in schools if s.city or s.province})
    ca_map: dict[str, dict] = {}
    if cities:
        cplaceholders = ", ".join(f":c{i}" for i in range(len(cities)))
        cparams = {f"c{i}": v for i, v in enumerate(cities)}
        carows = await db.execute(
            text(f"SELECT city_name, location, advantage, development, main_business, city_level "
                 f"FROM city_analysis WHERE city_name IN ({cplaceholders})"),
            cparams,
        )
        for r in carows.mappings():
            ca_map[r["city_name"]] = dict(r)

    # ── Assemble dimensions per school ──
    for school in schools:
        dims: dict = {}
        history = admission_map.get(school.school_id, [])

        # Dims 1-6,9: admission data
        if history:
            years = sorted(history, key=lambda x: x["year"], reverse=True)
            latest = years[0]
            dims["latest_year"] = latest["year"]
            dims["latest_min_rank"] = latest.get("min_rank")
            dims["latest_min_score"] = latest.get("min_score")
            scores = [y["min_score"] for y in years if y.get("min_score")]
            if len(scores) >= 2:
                diff = scores[0] - scores[-1]
                if diff > 3:
                    trend, trend_detail = "rising", f"分数线逐年上升 (+{diff}分趋势)"
                elif diff < -3:
                    trend, trend_detail = "falling", f"分数线逐年下降 (-{abs(diff)}分趋势)"
                else:
                    trend, trend_detail = "stable", "分数线近年稳定"
            else:
                trend, trend_detail = "unknown", "数据不足，趋势未知"
            dims["trend"] = trend
            dims["trend_detail"] = trend_detail
            dims["years_available"] = sorted([y["year"] for y in years], reverse=True)
        else:
            dims["trend"] = "unknown"
            dims["trend_detail"] = "暂无录取数据"
            dims["years_available"] = []
        dims["admission_trend"] = dims.get("trend_detail", "数据不足")

        # Dim 7: recommended major
        school_majors = majors_by_school.get(school.school_id, [])
        major_names = {m["major_name"] for m in school_majors}
        recommended_major = None
        major_match_type = "none"

        if major_pref:
            for pref in major_pref:
                if pref in major_names:
                    match = next(m for m in school_majors if m["major_name"] == pref)
                    recommended_major = pref
                    dims["major_level"] = match["major_level"] or "普通"
                    major_match_type = "exact"
                    break
                sim_key = (school.school_id, pref)
                if sim_key in similarity_map:
                    sim = similarity_map[sim_key]
                    recommended_major = sim["target_major"]
                    dims["major_similarity"] = float(sim["similarity"])
                    dims["major_level"] = sim["major_level"] or "普通"
                    major_match_type = "similar"
                    dims["major_note"] = f"相近专业（与{pref}相似度{int(float(sim['similarity'])*100)}%）"
                    break
            if not recommended_major and school_majors:
                fallback = school_majors[0]
                recommended_major = fallback["major_name"]
                major_match_type = "fallback"

        dims["recommended_major"] = recommended_major or (major_pref[0] if major_pref else "综合类专业")
        dims["major_match_type"] = major_match_type

        # Dim 8: tuition
        tuition_entries = tuition_by_school.get(school.school_id, [])
        target_major = recommended_major or "__default__"
        tuition_row = next((t for t in tuition_entries if t["major_name"] == target_major), None)
        if not tuition_row:
            tuition_row = next((t for t in tuition_entries if t["major_name"] == "__default__"), None)
        if not tuition_row:
            tuition_row = tuition_entries[0] if tuition_entries else None

        if tuition_row:
            per_yr = tuition_row["tuition_per_year"]
            yrs = tuition_row["duration_years"] or 4
            total = per_yr * yrs
            dims["tuition"] = f"{per_yr:,}元/年"
            dims["tuition_total"] = f"{yrs}年约{total//10000:.1f}万" if total >= 10000 else f"{yrs}年约{total:,}元"
            dims["tuition_fit"] = _tuition_fit(per_yr, req.economic_level)
            dims["tuition_source"] = tuition_row["data_source"] or "官网"
            dims["tuition_year"] = tuition_row["data_year"]
            dims["tuition_data_quality"] = "real"
        else:
            stype = (school.school_type or "").lower()
            if "公办" in stype or school.is_985 or school.is_211:
                dims["tuition"] = "4500-6000元/年"
                dims["tuition_total"] = "4年约2-2.4万"
                dims["tuition_fit"] = "中等家庭可接受"
            elif "民办" in stype or "独立学院" in stype:
                dims["tuition"] = "15000-30000元/年"
                dims["tuition_total"] = "4年约6-12万"
                dims["tuition_fit"] = "需考虑家庭经济承受能力"
            else:
                dims["tuition"] = "5000-8000元/年"
                dims["tuition_total"] = "4年约2-3.2万"
                dims["tuition_fit"] = "中等家庭可接受"
            dims["tuition_data_quality"] = "estimated"

        # Dim 11: employment
        emp = emp_by_school.get(school.school_id)
        if emp and emp.get("employment_rate") is not None:
            er = emp["employment_rate"]
            gr = emp.get("graduate_rate")
            yr = emp.get("data_year") or "未知"
            src = emp.get("data_source") or "学校官网"
            dims["employment_rate"] = f"{er:.1f}%"
            dims["graduate_rate"] = f"{gr:.1f}%" if gr is not None else None
            dims["employment_source"] = f"{src}·{yr}年数据"
            dims["employment_data_quality"] = "real"
        else:
            if school.is_985:
                dims["employment_rate"] = "92-97%"
            elif school.is_211:
                dims["employment_rate"] = "88-94%"
            else:
                dims["employment_rate"] = "82-90%"
            dims["employment_source"] = "按院校层次估算"
            dims["employment_data_quality"] = "estimated"

        # Dim 12-13: salary
        sal_entries = salary_by_school.get(school.school_id, [])
        sal_row = next((s for s in sal_entries if s.get("major_name") == target_major), None)
        if not sal_row:
            sal_row = next((s for s in sal_entries if s.get("major_name") == "__default__"), None)
        if not sal_row:
            sal_row = sal_entries[0] if sal_entries else None

        if sal_row and sal_row.get("salary_start_min") is not None:
            s_min, s_max = sal_row["salary_start_min"], sal_row.get("salary_start_max") or sal_row["salary_start_min"]
            t_min = sal_row.get("salary_3yr_min")
            t_max = sal_row.get("salary_3yr_max") or (t_min if t_min else None)
            yr = sal_row.get("data_year") or "未知"
            dims["avg_salary_start"] = f"{s_min//100*100}-{s_max//100*100}元/月" if s_min != s_max else f"{s_min}元/月"
            dims["avg_salary_3yr"] = f"{t_min//100*100}-{t_max//100*100}元/月" if (t_min and t_max and t_min != t_max) else (f"{t_min}元/月" if t_min else "–")
            dims["salary_source"] = f"{sal_row.get('data_source') or '第三方调研'}·{yr}年数据"
            dims["salary_data_quality"] = "real"
        else:
            if school.is_985:
                dims["avg_salary_start"] = "8000-14000元/月"
                dims["avg_salary_3yr"] = "15000-25000元/月"
            elif school.is_211:
                dims["avg_salary_start"] = "6500-11000元/月"
                dims["avg_salary_3yr"] = "12000-18000元/月"
            else:
                dims["avg_salary_start"] = "4500-7000元/月"
                dims["avg_salary_3yr"] = "7000-12000元/月"
            dims["salary_source"] = "按院校层次估算"
            dims["salary_data_quality"] = "estimated"

        dims["core_positions"] = "见该校就业报告"
        dims["trend_5yr"] = "数据收集中"

        # Dim 15: city analysis
        city = school.city or school.province
        ca = ca_map.get(city)
        if ca:
            city_level = ca.get("city_level") or "二线"
            dims["city_analysis"] = {
                "location": ca["location"],
                "advantage": ca["advantage"],
                "disadvantage": ca["development"],
                "job_market": ca["main_business"],
                "livability": f"{city_level}城市，生活成本{'较高' if city_level == '一线' else '适中' if city_level == '新一线' else '较低'}，宜居指数{'良好' if city_level in ('一线', '新一线') else '稳定'}",
                "city_level": city_level,
            }
            dims["city_data_quality"] = "real"
        else:
            fallback = _CITY_ANALYSIS_FALLBACK.get(city, f"{city}，城市发展稳定，就业机会适中")
            dims["city_analysis"] = {"summary": fallback}
            dims["city_data_quality"] = "estimated"

        # Dim 16: AI点评
        dims["ai_review"] = None

        school.dimensions = dims


def _tuition_fit(per_year: int, economic_level: str) -> str:
    if economic_level in ("较为困难",):
        return "高于建议范围，请谨慎评估" if per_year > 8000 else "家庭可接受"
    if economic_level in ("良好", "比较优越"):
        return "家庭完全可接受"
    return "中等家庭可接受" if per_year <= 10000 else "需提前规划费用"


# ──────────────────────────────────────────────────────────────────────────────
# PHASE 5: 数据缺口检测 (v4.0 — 6种数据类型)
# ──────────────────────────────────────────────────────────────────────────────

async def detect_data_gaps(
    school_id: int, province: str, history: list[dict], db: AsyncSession
) -> str:
    years = [y["year"] for y in history if y.get("min_rank")]
    if len(years) >= 4:
        quality = "full"
    elif len(years) >= 1:
        missing = [y for y in [2022, 2023, 2024, 2025] if y not in years]
        await _create_admission_tasks(school_id, province, missing, db)
        quality = "partial"
    else:
        await _create_admission_tasks(school_id, province, [2022, 2023, 2024, 2025], db)
        quality = "no_data" if not history else "partial"

    # Trigger other crawl tasks asynchronously (best-effort)
    await _ensure_major_task(school_id, db)
    await _ensure_tuition_task(school_id, db)
    await _ensure_employment_task(school_id, db)
    await _ensure_salary_task(school_id, db)
    return quality


async def _get_school_info(school_id: int, db: AsyncSession) -> tuple[str, str]:
    try:
        row = await db.execute(
            text("SELECT name FROM schools WHERE id = :sid"),
            {"sid": school_id},
        )
        name = row.scalar() or str(school_id)
    except Exception:
        name = str(school_id)
    return name, str(school_id)


async def _create_admission_tasks(
    school_id: int, province: str, years: list[int], db: AsyncSession
) -> None:
    school_name, school_code = await _get_school_info(school_id, db)
    for year in years:
        try:
            await db.execute(
                text("""
                    INSERT IGNORE INTO school_admission_crawl_tasks
                        (school_name, school_code, year, status)
                    VALUES (:name, :code, :yr, 'pending')
                """),
                {"name": school_name, "code": school_code, "yr": year},
            )
        except Exception:
            pass


async def _ensure_major_task(school_id: int, db: AsyncSession) -> None:
    try:
        r = await db.execute(
            text("SELECT COUNT(*) AS cnt FROM school_majors WHERE school_id = :sid"),
            {"sid": school_id},
        )
        if (r.scalar() or 0) == 0:
            school_name, school_code = await _get_school_info(school_id, db)
            await db.execute(
                text("""
                    INSERT IGNORE INTO school_major_crawl_tasks
                        (school_id, school_name, school_code, status)
                    VALUES (:sid, :name, :code, 'pending')
                """),
                {"sid": school_id, "name": school_name, "code": school_code},
            )
    except Exception:
        pass


async def _ensure_tuition_task(school_id: int, db: AsyncSession) -> None:
    try:
        r = await db.execute(
            text("SELECT COUNT(*) AS cnt FROM school_tuition WHERE school_id = :sid"),
            {"sid": school_id},
        )
        if (r.scalar() or 0) == 0:
            school_name, school_code = await _get_school_info(school_id, db)
            await db.execute(
                text("""
                    INSERT IGNORE INTO school_tuition_crawl_tasks
                        (school_id, school_name, school_code, status)
                    VALUES (:sid, :name, :code, 'pending')
                """),
                {"sid": school_id, "name": school_name, "code": school_code},
            )
    except Exception:
        pass


async def _ensure_employment_task(school_id: int, db: AsyncSession) -> None:
    try:
        r = await db.execute(
            text("SELECT COUNT(*) AS cnt FROM school_employment WHERE school_id = :sid"),
            {"sid": school_id},
        )
        if (r.scalar() or 0) == 0:
            school_name, school_code = await _get_school_info(school_id, db)
            await db.execute(
                text("""
                    INSERT IGNORE INTO school_employment_crawl_tasks
                        (school_id, school_name, school_code, status)
                    VALUES (:sid, :name, :code, 'pending')
                """),
                {"sid": school_id, "name": school_name, "code": school_code},
            )
    except Exception:
        pass


async def _ensure_salary_task(school_id: int, db: AsyncSession) -> None:
    try:
        r = await db.execute(
            text("SELECT COUNT(*) AS cnt FROM school_salary WHERE school_id = :sid"),
            {"sid": school_id},
        )
        if (r.scalar() or 0) == 0:
            school_name, school_code = await _get_school_info(school_id, db)
            await db.execute(
                text("""
                    INSERT IGNORE INTO school_salary_crawl_tasks
                        (school_id, school_name, school_code, status)
                    VALUES (:sid, :name, :code, 'pending')
                """),
                {"sid": school_id, "name": school_name, "code": school_code},
            )
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
# 主入口：generate_recommendation
# ──────────────────────────────────────────────────────────────────────────────

async def generate_recommendation(req: RecommendRequest, db: AsyncSession) -> dict:
    # L3 全量结果缓存 key (deterministic hash)
    cache_payload = json.dumps({
        "province": req.province,
        "score": req.score,
        "subject": req.subject_category,
        "rank": req.rank,
        "city_pref": sorted(req.city_preference),
        "intended": sorted(req.intended_schools),
        "major": sorted(req.major_preference),
        "personality": sorted(req.personality),
        "economic": req.economic_level,
    }, sort_keys=True, ensure_ascii=False)
    cache_key = f"recommend:result:{hashlib.md5(cache_payload.encode()).hexdigest()}"

    try:
        r = get_redis()
        cached = await r.get(cache_key)
        if cached:
            result = json.loads(cached)
            result["cache_hit"] = True
            return result
    except Exception:
        pass

    # PHASE 0: 位次估算
    rank = req.rank
    rank_source = "provided"
    if rank is None:
        rank = await estimate_rank(req.province, req.score, req.subject_category, db)
        rank_source = "estimated"

    # PHASE 1: 候选池
    special_attention, candidates = await build_candidate_pool(req, db)

    # PHASE 2: 批量查询录取数据
    all_ids = [s.school_id for s in candidates]
    for s in special_attention:
        if s.school_id not in all_ids:
            all_ids.append(s.school_id)

    admission_map = await batch_query_admission(all_ids, req.province, db)

    # PHASE 2: 概率计算 (special_attention)
    for s in special_attention:
        history = admission_map.get(s.school_id, [])
        if rank:
            rp = calc_rank_prob(rank, history)
            s.rank_prob = rp if rp is not None else 0.0
            s.weighted_prob = calc_weighted_prob(req, s.rank_prob, s) if s.rank_prob else 0.0
        else:
            s.rank_prob = 0.0
            s.weighted_prob = 0.0
        s.data_quality = await detect_data_gaps(s.school_id, req.province, history, db)
        s.admission_data = _build_admission_summary(history)

    # PHASE 2: 概率计算 (推荐池)
    scored: list[SchoolRecord] = []
    for s in candidates:
        history = admission_map.get(s.school_id, [])
        if rank:
            rp = calc_rank_prob(rank, history)
            if rp is None:
                # No data — estimate from peer schools in same tier
                rp = _estimate_from_peers(s, scored, req.score)
            s.rank_prob = rp
        else:
            s.rank_prob = 50.0  # No rank available
        s.weighted_prob = calc_weighted_prob(req, s.rank_prob, s)
        s.tier, s.tier_label = assign_tier(s.rank_prob, req.score)
        s.data_quality = await detect_data_gaps(s.school_id, req.province, history, db)
        s.admission_data = _build_admission_summary(history)
        scored.append(s)

    # PHASE 3+4: Tier排序 + 截取15所
    selected = sort_and_slice(scored, req.personality)

    # PHASE 2d: 16维度数据聚合 (batched — only for selected 15 + special_attention)
    schools_for_dims = selected + [s for s in special_attention if s.school_id not in {x.school_id for x in selected}]
    await batch_aggregate_dimensions(schools_for_dims, admission_map, req, db)

    await db.commit()

    # 统计
    q_full = sum(1 for s in selected if s.data_quality == "full")
    q_partial = sum(1 for s in selected if s.data_quality == "partial")
    q_estimated = sum(1 for s in selected if s.data_quality in ("estimated", "no_data"))

    result = {
        "student_rank": rank,
        "rank_source": rank_source,
        "special_attention": [_school_to_dict(s) for s in special_attention],
        "schools": [_school_to_dict(s) for s in selected],
        "tier_summary": {
            "boost": {"count": sum(1 for s in selected if s.tier == 0), "range": "30%-60%"},
            "solid": {"count": sum(1 for s in selected if s.tier == 1), "range": "60%-85%"},
            "safe":  {"count": sum(1 for s in selected if s.tier == 2), "range": "≥85%"},
        },
        "data_quality_summary": {
            "full_count": q_full,
            "partial_count": q_partial,
            "estimated_count": q_estimated,
        },
        "cache_hit": False,
    }

    # Cache result for 10 minutes
    try:
        r = get_redis()
        await r.setex(cache_key, 600, json.dumps(result, ensure_ascii=False))
    except Exception:
        pass

    return result


def _build_admission_summary(history: list[dict]) -> dict:
    if not history:
        return {"data_quality": "no_data"}
    years = sorted(history, key=lambda x: x["year"], reverse=True)
    latest = years[0]
    scores = [y["min_score"] for y in years if y.get("min_score")]
    if len(scores) >= 2:
        diff = scores[0] - scores[-1]
        trend = "rising" if diff > 3 else ("falling" if diff < -3 else "stable")
        detail = "→".join(str(s) for s in reversed(scores)) + f" ({'↑' if trend=='rising' else '↓' if trend=='falling' else '→'})"
    else:
        trend = "unknown"
        detail = str(scores[0]) if scores else "–"
    return {
        "latest_year": latest["year"],
        "latest_min_rank": latest.get("min_rank"),
        "latest_min_score": latest.get("min_score"),
        "trend": trend,
        "trend_detail": detail,
        "years_available": sorted([y["year"] for y in years], reverse=True),
    }


def _estimate_from_peers(
    school: SchoolRecord, peers: list[SchoolRecord], score: int
) -> float:
    """Estimate rank_prob from peers with similar tier/985/211 status."""
    tier_peers = [
        p.rank_prob for p in peers
        if p.rank_prob is not None
        and p.is_985 == school.is_985
        and p.is_211 == school.is_211
    ]
    if tier_peers:
        return round(sum(tier_peers) / len(tier_peers), 1)
    return 50.0  # Conservative default


def _school_to_dict(s: SchoolRecord) -> dict:
    tags = []
    if s.is_985:
        tags.append("985")
    if s.is_211:
        tags.append("211")
    if s.is_double_first:
        tags.append("双一流")
    if not tags:
        tags.append(s.level or "本科")

    d = {
        "school_id": s.school_id,
        "name": s.name,
        "province": s.province,
        "city": s.city,
        "tags": tags,
        "rank_prob": round(s.rank_prob, 1) if s.rank_prob is not None else 0.0,
        "weighted_prob": round(s.weighted_prob, 1) if s.weighted_prob is not None else 0.0,
        "is_intended": s.is_intended,
        "is_intended_city": s.is_intended_city,
        "admission_data": s.admission_data,
        "data_quality": s.data_quality,
        "dimensions": s.dimensions,
        "ai_review": None,
    }
    if s.tier is not None:
        d["tier"] = s.tier
        d["tier_label"] = s.tier_label
    if s.is_intended and s.rank_prob == 0.0:
        d["note"] = "您的成绩无法达到该校录取线"
    return d
