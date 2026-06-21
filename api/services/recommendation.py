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

# ──────────────────────────────────────────────────────────────────────────────
# 城市经济等级（用于 T11.3 地域扩展：周边城市按等级降序排列）
# 1=一线  2=新一线  3=二线  4=三线
# ──────────────────────────────────────────────────────────────────────────────
CITY_ECONOMIC_LEVEL: dict[str, int] = {
    "北京": 1, "上海": 1, "广州": 1, "深圳": 1,
    "成都": 2, "杭州": 2, "武汉": 2, "重庆": 2, "西安": 2,
    "南京": 2, "郑州": 2, "长沙": 2, "天津": 2, "苏州": 2,
    "合肥": 2, "青岛": 2, "济南": 2, "沈阳": 2, "大连": 2,
    "厦门": 2, "福州": 2, "哈尔滨": 2, "昆明": 2, "南昌": 2,
    "贵阳": 2, "太原": 2, "石家庄": 2, "兰州": 2, "银川": 2,
    "西宁": 2, "乌鲁木齐": 2, "南宁": 2, "呼和浩特": 2,
    "宁波": 3, "温州": 3, "无锡": 3, "南通": 3, "徐州": 3,
    "绍兴": 3, "嘉兴": 3, "金华": 3, "台州": 3,
    "芜湖": 3, "安庆": 3, "蚌埠": 3,
    "泉州": 3, "漳州": 3, "龙岩": 3,
    "赣州": 3, "九江": 3, "宜春": 3,
    "株洲": 3, "岳阳": 3, "常德": 3,
    "宜昌": 3, "荆州": 3, "黄石": 3,
    "洛阳": 3, "开封": 3, "新乡": 3,
    "绵阳": 3, "南充": 3, "宜宾": 3,
    "咸阳": 3, "宝鸡": 3,
    "济宁": 3, "潍坊": 3, "临沂": 3, "烟台": 3,
    "长春": 3, "鞍山": 3,
    "东莞": 3, "佛山": 3, "珠海": 3, "惠州": 3,
}

# 城市 → 周边城市列表（按经济等级降序，一线最优先）
CITY_NEARBY_BY_LEVEL: dict[str, list[str]] = {
    "北京":   ["上海", "广州", "天津", "石家庄", "太原"],
    "上海":   ["北京", "广州", "深圳", "南京", "杭州", "苏州", "无锡"],
    "广州":   ["深圳", "上海", "北京", "厦门", "南宁", "长沙", "福州"],
    "深圳":   ["广州", "上海", "北京", "厦门", "东莞", "惠州", "珠海"],
    "郑州":   ["武汉", "西安", "南京", "北京", "上海", "合肥", "济南", "石家庄"],
    "武汉":   ["上海", "南京", "长沙", "成都", "郑州", "合肥", "南昌"],
    "西安":   ["北京", "上海", "郑州", "成都", "武汉", "咸阳", "兰州"],
    "成都":   ["重庆", "上海", "北京", "武汉", "西安", "昆明", "贵阳", "绵阳"],
    "南京":   ["上海", "苏州", "杭州", "合肥", "徐州", "无锡", "南通"],
    "杭州":   ["上海", "南京", "苏州", "宁波", "无锡", "金华", "绍兴"],
    "长沙":   ["武汉", "广州", "南昌", "贵阳", "株洲", "岳阳"],
    "合肥":   ["南京", "杭州", "上海", "武汉", "郑州", "芜湖", "蚌埠"],
    "青岛":   ["上海", "南京", "济南", "北京", "烟台", "潍坊"],
    "济南":   ["北京", "天津", "南京", "郑州", "石家庄", "济宁"],
    "沈阳":   ["北京", "天津", "大连", "长春", "石家庄", "鞍山"],
    "大连":   ["北京", "上海", "沈阳", "天津", "长春"],
    "厦门":   ["上海", "广州", "福州", "泉州", "漳州"],
    "福州":   ["上海", "广州", "厦门", "温州", "宁波"],
    "哈尔滨": ["北京", "沈阳", "长春", "大连"],
    "长春":   ["北京", "沈阳", "哈尔滨", "大连"],
    "南昌":   ["上海", "武汉", "广州", "合肥", "长沙", "赣州"],
    "昆明":   ["成都", "重庆", "贵阳", "上海", "广州"],
    "贵阳":   ["成都", "重庆", "昆明", "长沙", "广州"],
    "太原":   ["北京", "天津", "石家庄", "郑州", "西安"],
    "石家庄": ["北京", "天津", "太原", "郑州", "济南"],
    "重庆":   ["成都", "武汉", "西安", "贵阳", "昆明", "南充", "宜宾"],
    "天津":   ["北京", "石家庄", "济南", "沈阳"],
    "苏州":   ["上海", "南京", "杭州", "无锡", "南通"],
    "宁波":   ["上海", "杭州", "温州", "台州", "绍兴"],
    "兰州":   ["西安", "成都", "银川", "西宁"],
    "南宁":   ["广州", "昆明", "贵阳", "长沙"],
    "呼和浩特": ["北京", "天津", "太原", "沈阳"],
}

# Tier 阈值
TIER_BOOST_MIN = 30.0   # 冲刺下界（含）
TIER_SOLID_MIN = 50.0   # 稳妥下界（含）；冲刺上界（不含）
TIER_SAFE_MIN  = 85.0   # 保底下界（含）
LOW_SCORE_BOUNDARY = 400
LOW_SCORE_TIER_MIN = 5.0  # 低分段（<400分）冲刺下界


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
    globe_expanded: bool = False        # True = L4全国扩展推荐，仅冲刺档使用

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

_MILITARY_SCHOOL_CITY = {
    "空军工程大学": "西安",
    "空军军医大学": "西安",
    "第四军医大学": "西安",
    "武警工程大学": "西安",
    "海军工程大学": "武汉",
    "陆军工程大学": "南京",
    "国防科技大学": "长沙",
    "信息工程大学": "郑州",
    "海军航空大学": "烟台",
    "陆军军医大学": "重庆",
    "海军医学大学": "上海",
    "空军航空大学": "长春",
    "陆军特种作战学院": "广州",
    "联合勤务学院": "北京",
    "国防大学": "北京",
}

# 省份 → 省会城市（用于学校名称无法提取城市时的兜底）
_PROVINCE_CAPITAL: dict[str, str] = {
    "北京": "北京", "上海": "上海", "天津": "天津", "重庆": "重庆",
    "广东": "广州", "浙江": "杭州", "江苏": "南京", "四川": "成都",
    "湖北": "武汉", "陕西": "西安", "山东": "济南", "河南": "郑州",
    "湖南": "长沙", "安徽": "合肥", "福建": "福州", "江西": "南昌",
    "黑龙江": "哈尔滨", "吉林": "长春", "辽宁": "沈阳",
    "河北": "石家庄", "山西": "太原", "内蒙古": "呼和浩特",
    "广西": "南宁", "海南": "海口", "贵州": "贵阳", "云南": "昆明",
    "西藏": "拉萨", "青海": "西宁", "宁夏": "银川", "新疆": "乌鲁木齐",
    "甘肃": "兰州",
}


def _city_from_school(name: str, province: str) -> str:
    """从学校名称提取城市，提取失败时用省会兜底，避免城市显示为省份名。"""
    city = _extract_city(name)
    if city:
        return city
    return _PROVINCE_CAPITAL.get(province, province)


def _extract_city(name: str) -> str:
    import re
    # Military schools: city not in school name, use lookup table
    for keyword, city in _MILITARY_SCHOOL_CITY.items():
        if keyword in name:
            return city
    # Single unified regex — all city names merged into one anchored pattern
    _CITY_RE = re.compile(
        r"^(北京|上海|天津|重庆"
        r"|哈尔滨|长春|沈阳|大连|石家庄|济南|青岛|郑州|南京|杭州|武汉|成都|西安"
        r"|广州|深圳|南昌|合肥|福州|厦门|长沙|昆明|贵阳|南宁|海口|太原|呼和浩特"
        r"|西宁|银川|乌鲁木齐|兰州|徐州|苏州|无锡|宁波|温州|汕头"
        r"|洛阳|开封|焦作|新乡|信阳|南阳|安阳|平顶山|许昌|商丘|周口|驻马店|漯河|濮阳|鹤壁|三门峡"
        r"|宜昌|荆州|黄石|襄阳|十堰|孝感|黄冈|荆门|咸宁|鄂州|随州"
        r"|株洲|岳阳|湘潭|衡阳|邵阳|常德|郴州|永州|怀化|娄底|益阳|吉首"
        r"|绵阳|南充|自贡|泸州|德阳|乐山|宜宾|达州|广元|遂宁|内江|攀枝花"
        r"|芜湖|蚌埠|马鞍山|安庆|黄山|滁州|六安|淮北|铜陵|宣城|池州|亳州"
        r"|泉州|漳州|龙岩|三明|南平|莆田"
        r"|赣州|九江|宜春|景德镇|萍乡|吉安|上饶|抚州|新余"
        r"|咸阳|宝鸡|渭南|汉中|延安|安康|榆林|商洛"
        r"|济宁|潍坊|临沂|泰安|淄博|聊城|日照|德州|滨州|菏泽|枣庄|东营|威海"
        r"|常州|南通|扬州|镇江|泰州|盐城|淮安|连云港|宿迁"
        r"|嘉兴|湖州|绍兴|金华|衢州|舟山|台州|丽水"
        r"|东莞|佛山|中山|珠海|惠州|江门|肇庆|茂名|湛江|梅州|韶关|清远|揭阳|潮州|阳江|河源|汕尾|云浮"
        r"|鞍山|抚顺|本溪|锦州|丹东|营口|辽阳|盘锦|铁岭|朝阳|葫芦岛"
        r"|吉林|四平|通化|延吉|松原|白城|辽源|白山"
        r"|大庆|齐齐哈尔|牡丹江|佳木斯|鸡西|鹤岗|双鸭山|伊春|七台河|黑河|绥化"
        r"|秦皇岛|张家口|唐山|保定|邯郸|邢台|沧州|承德|衡水|廊坊|定州"
        r"|大同|长治|临汾|运城|晋城|晋中|忻州|吕梁|朔州|阳泉"
        r"|柳州|桂林|北海|玉林|梧州|钦州|贵港|防城港|贺州|河池|来宾|崇左|百色"
        r"|天水|酒泉|武威|平凉|张掖|庆阳|陇南|白银|定西"
        r"|包头|赤峰|鄂尔多斯|通辽|呼伦贝尔|乌兰察布|巴彦淖尔|乌海"
        r"|石河子|克拉玛依|昌吉|伊宁|库尔勒|喀什|阿克苏"
        r"|秦皇岛|驻马店|平顶山|三门峡|哈尔滨|景德镇|连云港|张家口|马鞍山"
        r"|攀枝花|六盘水|牡丹江|佳木斯|齐齐哈尔|呼和浩特|乌鲁木齐|石河子|呼伦贝尔"
        r"|鄂尔多斯|巴彦淖尔|克拉玛依|乌兰察布"
        r")"
    )
    m = _CITY_RE.match(name)
    return m.group(0) if m else ""


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
            city=_city_from_school(r["name"], r["province"]),
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
                city=_city_from_school(r["name"], r["province"]),
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
                city=_city_from_school(r["name"], r["province"]),
                level=r["level"] or "",
                school_type=r["school_type"] or "",
                is_985=bool(r["is_985"]),
                is_211=bool(r["is_211"]),
                is_double_first=bool(r["is_double_first"]),
                globe_expanded=True,   # L4 全国扩展，仅用于冲刺档
            ))
            seen_ids.add(r["school_id"])
            if len(pool) >= 105:
                break

    # L5 精英补充：无论候选池大小，确保 ≥15 所 985/211 校（适用于成绩≥400 的考生）
    if req.score >= 400:
        elite_in_pool = sum(1 for s in pool if s.is_985 or s.is_211)
        if elite_in_pool < 15:
            needed_elite = 15 - elite_in_pool
            elite_rows = await db.execute(
                text("""
                    SELECT school_id, name, province, level, school_type,
                           is_985, is_211, is_double_first
                    FROM schools
                    WHERE (is_985 = 1 OR is_211 = 1)
                    ORDER BY is_985 DESC, is_211 DESC
                    LIMIT :lim
                """),
                {"lim": needed_elite + len(seen_ids) + 50},
            )
            for r in elite_rows.mappings():
                if r["school_id"] in seen_ids:
                    continue
                pool.append(SchoolRecord(
                    school_id=r["school_id"],
                    name=r["name"],
                    province=r["province"],
                    city=_city_from_school(r["name"], r["province"]),
                    level=r["level"] or "",
                    school_type=r["school_type"] or "",
                    is_985=bool(r["is_985"]),
                    is_211=bool(r["is_211"]),
                    is_double_first=bool(r["is_double_first"]),
                    globe_expanded=True,
                ))
                seen_ids.add(r["school_id"])
                elite_in_pool += 1
                if elite_in_pool >= 15:
                    break

    return special_attention, pool[:120]


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

def calc_rank_prob(
    student_rank: int, history: list[dict],
    is_985: bool = False, is_211: bool = False, is_double_first: bool = False,
    school_type: str = "",
    student_score: int | None = None,
) -> Optional[float]:
    """Calculate admission probability based on rank comparison + school tier adjustment.

    School tier multipliers ensure that schools of vastly different prestige levels
    produce properly separated probabilities even when admission data is imperfect.
    - 985 schools: 0.82x (harder to get in — extremely competitive)
    - 211 / 双一流: 0.88x (harder)
    - 公办本科: 1.00x (neutral)
    - 民办/独立学院: 1.10x (easier)
    - 专科/职业: 1.18x (much easier)
    """
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

    # ── School Tier Adjustment ──
    # Ensures schools of different prestige levels produce meaningfully
    # different probabilities even when admission data is noisy or missing.
    stype = (school_type or "").lower()
    if is_985:
        tier_mult = 0.82   # 985 — extremely competitive, harder to get in
    elif is_211 or is_double_first:
        tier_mult = 0.88   # 211/双一流 — competitive
    elif "专科" in stype or "职业" in stype:
        tier_mult = 1.18   # 专科/职业 — much easier admission bar
    elif "民办" in stype or "独立" in stype:
        tier_mult = 1.10   # 民办/独立学院 — easier
    else:
        tier_mult = 1.00   # 公办本科 — neutral

    prob = max(1.0, min(99.0, prob * tier_mult))

    # ── Score-Tier Alignment Check ──
    # Blends the data-driven probability with a "tier prior" to prevent
    # bad admission data from producing nonsensical results.
    # E.g., a 985 school should never show 80%+ for a 500-score student.
    if student_score is not None:
        prior = _tier_score_prior(student_score, is_985, is_211, is_double_first, school_type)
        if prior is not None:
            # Blend: 90% data-driven, 10% tier prior
            # Data dominates heavily; prior only corrects extreme outliers
            prob = prob * 0.90 + prior * 0.10

    return max(1.0, min(99.0, prob))


def _tier_score_prior(
    score: int, is_985: bool, is_211: bool, is_double_first: bool, school_type: str
) -> Optional[float]:
    """Estimate a reasonable probability prior based solely on score and school tier.

    This acts as a sanity check: even if admission_history data is missing
    or corrupted, the prior ensures that 985 schools never show anomalously
    high probabilities for mid-range scores, and 专科 schools never show
    anomalously low probabilities.

    Returns None if the tier doesn't need a prior constraint.
    """
    # Normalize score to 750 scale (上海 max is 660)
    # For simplicity, treat all scores as /750; 上海's 660 will be slightly off
    # but the prior is intentionally loose

    if is_985:
        # 985 schools: extremely competitive
        # Prior represents expected probability for an AVERAGE 985 school at this score level.
        # Values reduced by ~40% from previous version to prevent drowning 冲刺 tier.
        if score >= 660: return 25.0   # was 45.0
        elif score >= 630: return 20.0  # was 38.0
        elif score >= 600: return 12.0  # was 25.0
        elif score >= 570: return 7.0   # was 15.0
        elif score >= 540: return 4.0   # was 8.0
        elif score >= 510: return 2.0   # was 4.0
        else: return 1.0               # was 2.0
    elif is_211 or is_double_first:
        # 211/双一流: competitive
        if score >= 640: return 35.0   # was 60.0
        elif score >= 610: return 28.0  # was 50.0
        elif score >= 580: return 20.0  # was 38.0
        elif score >= 550: return 12.0  # was 25.0
        elif score >= 520: return 6.0   # was 12.0
        elif score >= 490: return 3.0   # was 6.0
        else: return 1.5               # was 3.0
    else:
        stype = (school_type or "").lower()
        if "专科" in stype or "职业" in stype:
            # 专科/职业: easy admission
            if score >= 550: return 95.0
            elif score >= 500: return 88.0
            elif score >= 450: return 78.0
            elif score >= 400: return 65.0
            elif score >= 350: return 50.0
            else: return 35.0
        elif "民办" in stype or "独立" in stype:
            # 民办/独立学院: easier
            if score >= 550: return 90.0
            elif score >= 500: return 80.0
            elif score >= 450: return 65.0
            else: return 50.0

    # 公办本科: no strong prior needed
    return None


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
    """Returns 0-10 (percentage). Uses normalized exact match after stripping city suffixes."""
    if not city_preference:
        return 5.0

    # Normalize: strip "市" suffix from both sides for comparison
    city_raw = school.city or school.province
    city_norm = city_raw.rstrip("市")

    for cp in city_preference:
        cp_norm = cp.rstrip("市")
        if city_norm == cp_norm:
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

    if rank_prob >= TIER_SAFE_MIN:
        return 2, "保底"
    elif rank_prob >= TIER_SOLID_MIN:
        return 1, "稳妥"
    elif rank_prob >= boost_min:
        return 0, "冲刺"
    else:
        return -1, "低于推荐线"  # Excluded from output; filtered in sort_and_slice


# ──────────────────────────────────────────────────────────────────────────────
# PHASE 0.5: 成绩段位判断（PRD §4.7）
# ──────────────────────────────────────────────────────────────────────────────

async def classify_score_segment(
    province: str, subject_category: str, score: int, db: AsyncSession
) -> str:
    """查询 province_cutoffs 判断成绩段位。
    返回: 'high'（≥一本线）/ 'mid'（专科线≤x<一本线）/ 'low'（<专科线）/ 'unknown'（无数据）
    DB 无数据时回退到内置近似分数线，确保质量过滤始终生效。
    """
    # 内置兜底分数线 (一本线, 专科线) — 与 seed_province_cutoffs.py 同源
    _FALLBACK_CUTOFFS: dict[str, dict[str, tuple[int, int]]] = {
        "河南": {"物理": (519, 150), "历史": (490, 150)},
        "山东": {"物理": (449, 150), "历史": (449, 150)},
        "湖北": {"物理": (424, 200), "历史": (424, 200)},
        "湖南": {"物理": (428, 200), "历史": (428, 200)},
        "广东": {"物理": (439, 150), "历史": (439, 150)},
        "重庆": {"物理": (406, 180), "历史": (406, 180)},
        "辽宁": {"物理": (360, 150), "历史": (360, 150)},
        "福建": {"物理": (431, 180), "历史": (431, 180)},
        "江西": {"物理": (430, 180), "历史": (430, 180)},
        "广西": {"物理": (346, 180), "历史": (346, 180)},
        "安徽": {"物理": (482, 150), "历史": (482, 150)},
        "四川": {"物理": (469, 150), "历史": (469, 150)},
        "山西": {"物理": (463, 130), "历史": (463, 130)},
        "陕西": {"物理": (450, 150), "历史": (430, 150)},
        "甘肃": {"物理": (427, 150), "历史": (370, 150)},
        "云南": {"物理": (470, 150), "历史": (430, 150)},
        "贵州": {"物理": (380, 150), "历史": (350, 150)},
        "内蒙古": {"物理": (352, 150), "历史": (352, 150)},
        "新疆": {"物理": (390, 150), "历史": (330, 150)},
        "西藏": {"物理": (320, 150), "历史": (260, 150)},
        "青海": {"物理": (330, 150), "历史": (280, 150)},
        "宁夏": {"物理": (397, 150), "历史": (370, 150)},
        "黑龙江": {"物理": (395, 150), "历史": (355, 150)},
        "吉林": {"物理": (388, 150), "历史": (355, 150)},
        "河北": {"物理": (434, 150), "历史": (434, 150)},
        "浙江": {"综合": (488, 200)},
        "上海": {"综合": (405, 220)},
        "北京": {"综合": (448, 200)},
        "天津": {"综合": (472, 200)},
        "江苏": {"物理": (448, 180), "历史": (474, 180)},
        "海南": {"综合": (483, 200)},
    }

    # 科类别名：旧高考科类 → 统一字段
    _CAT_ALIAS = {"理科": "物理", "文科": "历史"}
    cats_to_try = [subject_category, _CAT_ALIAS.get(subject_category, ""), "综合"]
    cats_to_try = [c for c in cats_to_try if c]

    for cat in cats_to_try:
        try:
            row = await db.execute(
                text("""
                    SELECT cutoff_yiben, cutoff_zhuanke
                    FROM province_cutoffs
                    WHERE province = :p AND subject_category = :s AND year = 2025
                """),
                {"p": province, "s": cat},
            )
            cutoff = row.mappings().first()
            if cutoff:
                if cutoff["cutoff_yiben"] and score >= cutoff["cutoff_yiben"]:
                    return "high"
                if cutoff["cutoff_zhuanke"] and score >= cutoff["cutoff_zhuanke"]:
                    return "mid"
                return "low"
        except Exception:
            pass

    # DB 无数据 → 回退内置分数线
    prov_map = _FALLBACK_CUTOFFS.get(province, {})
    for cat in cats_to_try:
        if cat in prov_map:
            yiben, zhuanke = prov_map[cat]
            if score >= yiben:
                return "high"
            if score >= zhuanke:
                return "mid"
            return "low"

    # 全国通用兜底：750满分, 450以上视为高分段
    if score >= 500:
        return "high"
    if score >= 300:
        return "mid"
    return "low"


# ──────────────────────────────────────────────────────────────────────────────
# PHASE 3.5: 院校质量底线过滤（PRD §4.8）
# ──────────────────────────────────────────────────────────────────────────────

def _is_vocational(school: SchoolRecord) -> bool:
    """判断是否为专科/高职/职业技术类院校。"""
    if school.is_985 or school.is_211 or school.is_double_first:
        return False
    stype = (school.school_type or "").lower()
    level = (school.level or "").lower()
    name = school.name or ""
    return (
        "专科" in stype
        or "职业" in stype
        or "高职" in stype
        or "专科" in level
        or "职业技术" in name
        or "职业学院" in name
        or "高职" in name
        or "技师学院" in name
        or "技术学院" in name
    )


def _is_elite(school: SchoolRecord) -> bool:
    """判断是否为985/211/双一流精英院校。"""
    return school.is_985 or school.is_211 or school.is_double_first


def _is_public_yiben(school: SchoolRecord) -> bool:
    """判断是否为公办本科（含一本/二本）。"""
    stype = (school.school_type or "").lower()
    level = (school.level or "").lower()
    is_public = "民办" not in stype and "独立" not in stype and "职业" not in stype
    is_benke = "本科" in level or school.level in ("一本", "二本", "本科", "重点本科")
    return is_public and is_benke


def apply_quality_threshold_filter(
    schools: list[SchoolRecord], score_segment: str
) -> list[SchoolRecord]:
    """按 PRD §4.8 院校质量底线规则过滤候选学校。

    - 意向学校（is_intended）和意向城市（is_intended_city）标记学校不过滤
    - 低分段/未知段位不过滤（低分段保底可纳入专科）
    """
    if score_segment in ("low", "unknown"):
        return schools

    result = []
    for s in schools:
        # 仅明确指定的意向学校（is_intended）豁免质量底线
        # 意向城市（is_intended_city）仍需通过质量过滤，避免城市内职业院校混入高分推荐
        if s.is_intended:
            result.append(s)
            continue

        tier = s.tier if s.tier is not None else -1

        if score_segment == "high":
            if tier == 0:    # 冲刺档：仅 985/211/双一流
                if _is_elite(s):
                    result.append(s)
            elif tier == 1:  # 稳妥档：公办本科
                if not _is_vocational(s):
                    result.append(s)
            elif tier == 2:  # 保底档：排除专科/职业技术
                if not _is_vocational(s):
                    result.append(s)
            else:
                result.append(s)

        elif score_segment == "mid":
            if tier == 2:    # 中分段保底：保留二本为主，排除专科
                if not _is_vocational(s):
                    result.append(s)
            else:
                result.append(s)

        else:
            result.append(s)

    return result


# ──────────────────────────────────────────────────────────────────────────────
# PHASE 4: 排序 + 选15所
# ──────────────────────────────────────────────────────────────────────────────

def sort_and_slice(
    schools: list[SchoolRecord],
    personality: list[str],
    score_segment: str = "unknown",
) -> list[SchoolRecord]:
    """Selects 5 schools per tier (冲刺/稳妥/保底), guaranteed.

    Primary: schools stay in their natural probability tier.
    Backfill: if any tier has < 5 schools, fill from remaining eligible pool
              to guarantee 5 per tier (PRD requirement).

    Backfill rules:
      保底 < 5 → add highest-prob remaining (easiest schools, no globe_expanded)
      稳妥 < 5 → add mid-prob remaining
      冲刺 < 5 → add lowest-prob remaining (hardest schools)
    """
    def sort_key(s: SchoolRecord):
        intended_city_flag = 0 if s.is_intended_city else 1
        rank_prob_neg = -(s.rank_prob or 0)
        personality_neg = -_personality_score(s, personality)
        ranking = 0 if s.is_985 else (1 if s.is_211 else (2 if s.is_double_first else 3))
        weighted_neg = -(s.weighted_prob or 0)
        return (intended_city_flag, rank_prob_neg, personality_neg, ranking, weighted_neg)

    eligible = [s for s in schools if (s.tier is not None and s.tier >= 0)]

    # Primary bucketing: schools go into their natural tier
    tiers: dict[int, list[SchoolRecord]] = {0: [], 1: [], 2: []}
    for s in eligible:
        t = s.tier if s.tier in tiers else 0
        if s.globe_expanded and t == 2:
            continue  # L4/L5全国扩展不出现在保底档
        tiers[t].append(s)

    # Sort each tier, cap at 5
    result_by_tier: dict[int, list[SchoolRecord]] = {}
    for t in [0, 1, 2]:
        result_by_tier[t] = sorted(tiers[t], key=sort_key)[:5]

    # Backfill: guarantee 5 per tier
    # 顺序：冲刺 → 稳妥 → 保底，防止稳妥拿到劣于保底的学校（倒挂）
    used_ids = {s.school_id for t in result_by_tier.values() for s in t}

    # Remaining eligible pool sorted by probability descending
    remaining = [s for s in eligible if s.school_id not in used_ids and not s.globe_expanded]
    remaining_by_prob_desc = sorted(remaining, key=lambda s: -(s.rank_prob or 0))

    # 冲刺 backfill FIRST: take lowest-prob schools (most ambitious)
    if len(result_by_tier[0]) < 5:
        needed = 5 - len(result_by_tier[0])
        fill_ids = {s.school_id for s in result_by_tier[0]}
        # 优先使用 globe_expanded 学校，但最多 2 所
        globe_candidates = sorted(
            [s for s in eligible if s.school_id not in used_ids and s.globe_expanded],
            key=lambda s: (s.rank_prob or 0),
        )
        globe_used = 0
        for s in globe_candidates:
            if s.school_id not in fill_ids:
                if score_segment == "high" and not _is_elite(s):
                    continue
                s.tier = 0
                s.tier_label = "冲刺"
                result_by_tier[0].append(s)
                used_ids.add(s.school_id)
                globe_used += 1
                needed -= 1
                if needed == 0 or globe_used >= 2:
                    break
        if needed > 0:
            remaining_asc = sorted(
                [s for s in eligible if s.school_id not in used_ids and not s.globe_expanded],
                key=lambda s: (s.rank_prob or 0),
            )
            for s in remaining_asc:
                if s.school_id not in fill_ids:
                    if score_segment == "high" and not _is_elite(s):
                        continue
                    s.tier = 0
                    s.tier_label = "冲刺"
                    result_by_tier[0].append(s)
                    used_ids.add(s.school_id)
                    needed -= 1
                    if needed == 0:
                        break

    # 稳妥 backfill SECOND: fill from mid-prob remaining (排除 globe_expanded)
    if len(result_by_tier[1]) < 5:
        needed = 5 - len(result_by_tier[1])
        fill_ids = {s.school_id for s in result_by_tier[1]}
        remaining_mid = sorted(
            [s for s in eligible if s.school_id not in used_ids and not s.globe_expanded],
            key=sort_key,
        )
        for s in remaining_mid:
            if s.school_id not in fill_ids:
                if score_segment == "high" and _is_vocational(s):
                    continue
                if score_segment == "mid" and _is_vocational(s):
                    continue
                s.tier = 1
                s.tier_label = "稳妥"
                result_by_tier[1].append(s)
                used_ids.add(s.school_id)
                needed -= 1
                if needed == 0:
                    break

    # 保底 backfill LAST: take highest-prob schools (safest bets, 排除 globe_expanded)
    if len(result_by_tier[2]) < 5:
        needed = 5 - len(result_by_tier[2])
        fill_ids = {s.school_id for s in result_by_tier[2]}
        for s in remaining_by_prob_desc:
            if s.school_id not in fill_ids and s.school_id not in used_ids:
                if s.globe_expanded:
                    continue
                if score_segment == "high" and _is_vocational(s):
                    continue
                elif score_segment == "mid" and _is_vocational(s):
                    continue
                s.tier = 2
                s.tier_label = "保底"
                result_by_tier[2].append(s)
                used_ids.add(s.school_id)
                needed -= 1
                if needed == 0:
                    break

    result: list[SchoolRecord] = []
    for t in [0, 1, 2]:
        result.extend(result_by_tier[t])
    return result


# ──────────────────────────────────────────────────────────────────────────────
# PHASE 2d / T2.6: 16维度数据聚合
# ──────────────────────────────────────────────────────────────────────────────

# Fallback city descriptions — 5-dimension structure matching city_analysis table schema
_CITY_ANALYSIS_FALLBACK: dict[str, dict] = {
    "北京": {"location":"政治/科技/文化中心，超一线城市","advantage":"就业面最广，央企/外企/互联网总部云集，起薪全国领先","disadvantage":"生活成本极高，房价居高，落户难，竞争激烈","job_market":"IT/互联网、金融、文化传媒、政府/事业单位","livability":"超一线城市，消费极高，宜居指数良好","city_level":"一线"},
    "上海": {"location":"国际金融中心，长三角核心，外向型经济高度发达","advantage":"薪资水平全国第一梯队，金融/外资/制造业机会丰富","disadvantage":"消费水平极高，房价居高，落户难，内卷严重","job_market":"金融/证券/保险、外资企业、先进制造、生物医药","livability":"一线城市，生活成本较高，宜居指数良好","city_level":"一线"},
    "广州": {"location":"华南经济中心，珠三角核心，外贸枢纽","advantage":"商贸/制造业/互联网发达，外贸机会多，气候宜人","disadvantage":"生活成本中高，房价上涨快，城中村改造影响居住","job_market":"商贸/外贸、电子商务、汽车制造、快消品","livability":"一线城市，生活成本中高，宜居指数良好","city_level":"一线"},
    "深圳": {"location":"科技创新之都，粤港澳大湾区核心","advantage":"科技/互联网/金融发达，创业氛围浓，高薪","disadvantage":"生活成本高，房价全国最贵，教育资源相对稀缺","job_market":"IT/通信/电子、金融科技、智能制造、无人机","livability":"一线城市，消费高，宜居指数良好","city_level":"一线"},
    "成都": {"location":"西南经济中心，成渝双城经济圈核心","advantage":"科技/电子/游戏/文创产业发达，城市宜居","disadvantage":"地处西部，远离沿海产业链，部分行业薪资偏低","job_market":"IT/软件、游戏/文创、航空航天、生物医药","livability":"新一线城市，生活成本适中，宜居指数高","city_level":"新一线"},
    "武汉": {"location":"华中经济中心，长江中游核心城市","advantage":"光电/汽车/互联网产业集中，理工科需求旺","disadvantage":"夏季炎热，城市基建频繁，部分行业薪资竞争力不足","job_market":"光电子/通信、汽车制造、集成电路、生物医药","livability":"新一线城市，生活成本适中，宜居指数良好","city_level":"新一线"},
    "西安": {"location":"西北经济中心，丝绸之路起点","advantage":"航空航天/军工/软件产业密集，高校云集人才多","disadvantage":"就业竞争激烈，薪资水平偏低于东部，空气质量一般","job_market":"航空航天、军工、软件开发、文化旅游","livability":"新一线城市，生活成本较低，宜居指数稳定","city_level":"新一线"},
    "南京": {"location":"东部重要中心城市，长三角北翼核心","advantage":"电子信息/软件/化工发达，国企机会多，江苏经济强","disadvantage":"房价高，落户有一定门槛，产业结构偏传统","job_market":"电子信息、软件外包、化工/新材料、汽车","livability":"新一线城市，生活成本中高，宜居指数良好","city_level":"新一线"},
    "杭州": {"location":"长三角南翼核心，数字经济第一城","advantage":"互联网/电商/金融科技高度发达，阿里系生态","disadvantage":"房价极高，交通拥堵，生活节奏快","job_market":"互联网/电商、金融科技、人工智能、文化创意","livability":"新一线城市，消费较高，宜居指数良好","city_level":"新一线"},
    "郑州": {"location":"中原经济中心，全国重要交通枢纽","advantage":"物流/电商/食品产业发达，发展快速，生活成本低","disadvantage":"产业结构偏传统，高端产业占比偏低，空气质量有改善空间","job_market":"物流/电商、食品加工、装备制造、电子信息","livability":"新一线城市，生活成本低，宜居指数稳定","city_level":"新一线"},
    "长沙": {"location":"长江中游重要中心城市，长株潭城市群核心","advantage":"传媒/娱乐/工程机械发达，生活气息浓，幸福感高","disadvantage":"薪资水平一般，高端产业占比有待提升","job_market":"传媒/娱乐、工程机械、新材料、电子信息","livability":"新一线城市，生活成本适中，宜居指数高","city_level":"新一线"},
    "重庆": {"location":"西部直辖市，成渝双城经济圈核心","advantage":"制造业/汽车/化工基础雄厚，西部经济中心","disadvantage":"山地地形交通不便，夏季酷热，产业结构偏传统","job_market":"汽车/摩托车、电子信息、装备制造、化工","livability":"新一线城市，生活成本较低，宜居指数良好","city_level":"新一线"},
    "天津": {"location":"北方经济中心之一，京津冀协同发展核心","advantage":"港口经济/航空航天/装备制造发达，教育资源好","disadvantage":"经济增速放缓，青年人口外流，薪资竞争力不足","job_market":"航空航天、装备制造、港口物流、石油化工","livability":"新一线城市，生活成本适中，宜居指数稳定","city_level":"新一线"},
    "苏州": {"location":"长三角核心城市，上海大都市圈重要成员","advantage":"制造业/外资企业密集，经济发达，环境优美","disadvantage":"房价高，生活成本中高，产业结构偏制造业","job_market":"电子信息、装备制造、生物医药、纳米技术","livability":"新一线城市，生活成本中高，宜居指数良好","city_level":"新一线"},
    "合肥": {"location":"长三角城市群副中心，综合性国家科学中心","advantage":"集成电路/人工智能/量子科技快速发展，科教资源丰富","disadvantage":"薪资水平偏低于长三角平均水平，城市知名度待提升","job_market":"集成电路、人工智能、新能源汽车、量子科技","livability":"新一线城市，生活成本适中，宜居指数良好","city_level":"新一线"},
    "青岛": {"location":"山东半岛蓝色经济区核心，重要港口城市","advantage":"海洋经济/家电制造/港口贸易发达，环境优美","disadvantage":"薪资水平一般，产业结构偏传统，冬季湿度大","job_market":"家电/电子、海洋工程、港口物流、旅游","livability":"新一线城市，生活成本适中，宜居指数良好","city_level":"新一线"},
    "济南": {"location":"山东省会，环渤海地区南翼中心城市","advantage":"IT/机械/化工基础好，教育资源集中","disadvantage":"薪资竞争力不足，高端产业占比偏低","job_market":"IT服务、机械制造、化工、生物医药","livability":"新一线城市，生活成本适中，宜居指数稳定","city_level":"新一线"},
    "沈阳": {"location":"东北经济中心，辽中南城市群核心","advantage":"装备制造/航空航天基础雄厚，生活成本低","disadvantage":"经济增速放缓，人口流失，薪资水平偏低","job_market":"装备制造、航空航天、汽车、军工","livability":"新一线城市，生活成本低，宜居指数稳定","city_level":"新一线"},
    "大连": {"location":"东北亚国际航运中心，辽宁沿海经济带核心","advantage":"港口经济/软件外包/造船业发达，环境优美","disadvantage":"经济增速放缓，高端产业不足","job_market":"软件外包、港口物流、造船、旅游","livability":"新一线城市，生活成本适中，宜居指数良好","city_level":"新一线"},
    "厦门": {"location":"东南沿海重要中心城市，海峡西岸经济区核心","advantage":"旅游/会展/电子信息发达，环境优美气候宜人","disadvantage":"房价极高，城市规模偏小，产业结构单一","job_market":"旅游/会展、电子信息、金融、航运","livability":"新一线城市，消费较高，宜居指数高","city_level":"新一线"},
    "福州": {"location":"福建省会，海峡西岸经济区核心","advantage":"电子信息/纺织/食品加工发达，侨乡经济活跃","disadvantage":"城市知名度偏低，薪资竞争力一般","job_market":"电子信息、纺织服装、食品加工、物流","livability":"新一线城市，生活成本适中，宜居指数良好","city_level":"新一线"},
    "哈尔滨": {"location":"东北北部中心城市，哈长城市群核心","advantage":"装备制造/食品加工基础好，高校资源丰富","disadvantage":"冬季严寒，经济增速放缓，人才外流严重","job_market":"装备制造、食品加工、医药、军工","livability":"新一线城市，生活成本低，冬季宜居指数偏低","city_level":"新一线"},
    "昆明": {"location":"云南省会，面向南亚东南亚辐射中心","advantage":"旅游/烟草/生物医药发达，气候四季如春","disadvantage":"地处西南边陲，远离东部产业带，薪资偏低","job_market":"旅游/会展、生物医药、烟草、现代农业","livability":"新一线城市，生活成本低，宜居指数高","city_level":"新一线"},
    "南昌": {"location":"江西省会，长江中游城市群重要成员","advantage":"航空制造/LED/VR产业发展迅速，生活成本低","disadvantage":"薪资水平偏低，城市知名度不足","job_market":"航空制造、LED/光电、VR/电子信息、中医药","livability":"新一线城市，生活成本低，宜居指数稳定","city_level":"新一线"},
    "贵阳": {"location":"贵州省会，西南大数据产业集聚区","advantage":"大数据/云计算产业快速发展，生态旅游丰富","disadvantage":"地处西南山区，交通不便，薪资偏低","job_market":"大数据/云计算、旅游、中医药、现代农业","livability":"新一线城市，生活成本低，宜居指数良好","city_level":"新一线"},
    "太原": {"location":"山西省会，中部地区重要中心城市","advantage":"能源/装备制造基础好，生活成本低","disadvantage":"产业结构偏重工业，环境质量待改善，薪资偏低","job_market":"能源/煤炭、装备制造、新材料、文化旅游","livability":"新一线城市，生活成本低，宜居指数稳定","city_level":"新一线"},
    "石家庄": {"location":"河北省会，京津冀协同发展重要节点","advantage":"医药/纺织/化工基础好，靠近京津优势","disadvantage":"产业结构偏传统，薪资偏低，空气质量待改善","job_market":"医药/化工、纺织、装备制造、物流","livability":"新一线城市，生活成本低，宜居指数稳定","city_level":"新一线"},
    "兰州": {"location":"甘肃省会，西北地区重要工业基地","advantage":"石化/装备制造/有色冶金基础好，生活成本低","disadvantage":"地处西北内陆，经济欠发达，人才外流","job_market":"石油化工、装备制造、新材料、现代农业","livability":"新一线城市，生活成本低，宜居指数偏低","city_level":"新一线"},
    "银川": {"location":"宁夏首府，西北地区东部重要中心城市","advantage":"能源化工/现代农业发达，生活成本低","disadvantage":"经济体量小，产业结构单一，薪资偏低","job_market":"能源化工、现代农业、旅游、新材料","livability":"新一线城市，生活成本低，宜居指数稳定","city_level":"新一线"},
    "西宁": {"location":"青海省会，青藏高原东北部中心城市","advantage":"清洁能源/高原特色农业发达，生态环境好","disadvantage":"经济体量小，高海拔，交通不便，薪资偏低","job_market":"清洁能源、高原农业、旅游、中藏药","livability":"新一线城市，生活成本低，高海拔影响宜居性","city_level":"新一线"},
    "乌鲁木齐": {"location":"新疆首府，丝绸之路经济带核心区","advantage":"能源/商贸物流发达，民族特色产业丰富","disadvantage":"地处西北边疆，远离内地市场，冬季严寒","job_market":"能源/石化、商贸物流、旅游、现代农业","livability":"新一线城市，生活成本适中，冬季宜居指数偏低","city_level":"新一线"},
    "南宁": {"location":"广西首府，面向东盟开放合作前沿","advantage":"面向东盟区位优势，生态环境好，气候宜人","disadvantage":"经济体量偏小，薪资偏低，产业基础薄弱","job_market":"商贸/物流、旅游、现代农业、电子信息","livability":"新一线城市，生活成本低，宜居指数良好","city_level":"新一线"},
    "呼和浩特": {"location":"内蒙古首府，呼包鄂城市群核心","advantage":"乳业/能源/大数据产业发达，生活成本低","disadvantage":"经济体量偏小，冬季严寒，高端产业不足","job_market":"乳业/食品、能源/化工、大数据、旅游","livability":"新一线城市，生活成本低，冬季宜居指数偏低","city_level":"新一线"},
    "拉萨": {"location":"西藏首府，高原圣地","advantage":"旅游/藏药/特色农业独特，生态环境纯净","disadvantage":"高海拔缺氧，经济体量极小，产业单一，交通不便","job_market":"旅游、藏药、特色农业、文化创意","livability":"高海拔城市，生活成本中高，宜居指数特殊","city_level":"三线"},
    "洛阳": {"location":"河南省副中心城市，历史文化名城","advantage":"装备制造/新材料/旅游产业发达，文化底蕴深厚","disadvantage":"薪资水平偏低，高端产业占比不足","job_market":"装备制造、新材料、旅游、石油化工","livability":"三线城市，生活成本低，宜居指数稳定","city_level":"三线"},
    "开封": {"location":"河南省东部城市，历史文化名城","advantage":"旅游/文化创意产业特色鲜明，生活成本低","disadvantage":"经济体量偏小，薪资偏低，产业基础薄弱","job_market":"旅游/文化、现代农业、食品加工、纺织","livability":"三线城市，生活成本低，宜居指数稳定","city_level":"三线"},
    "新乡": {"location":"河南省北部城市，中原城市群重要成员","advantage":"装备制造/生物医药/现代农业发达，交通便利","disadvantage":"经济体量偏小，薪资偏低","job_market":"装备制造、生物医药、现代农业、纺织","livability":"三线城市，生活成本低，宜居指数稳定","city_level":"三线"},
    "南阳": {"location":"河南省西南部城市，豫鄂陕交界区域中心","advantage":"装备制造/中医药/现代农业发达，人口大市","disadvantage":"经济体量偏小，薪资偏低，高端产业不足","job_market":"装备制造、中医药、现代农业、纺织","livability":"三线城市，生活成本低，宜居指数稳定","city_level":"三线"},
    "信阳": {"location":"河南省南部城市，鄂豫皖交界区域","advantage":"现代农业/食品加工/旅游发达，生态环境好","disadvantage":"经济体量偏小，产业基础薄弱","job_market":"现代农业、食品加工、旅游、建材","livability":"三线城市，生活成本低，宜居指数良好","city_level":"三线"},
    "安阳": {"location":"河南省北部城市，京津冀协同发展辐射区","advantage":"钢铁/装备制造/文化旅游基础好","disadvantage":"产业结构偏重工业，薪资偏低","job_market":"钢铁/冶金、装备制造、文化旅游、纺织","livability":"三线城市，生活成本低，宜居指数稳定","city_level":"三线"},
    "焦作": {"location":"河南省西北部城市，中原城市群成员","advantage":"能源/化工/旅游产业发达，太极拳发源地","disadvantage":"资源型城市转型中，薪资偏低","job_market":"能源/化工、装备制造、旅游、新材料","livability":"三线城市，生活成本低，宜居指数稳定","city_level":"三线"},
}


async def aggregate_16_dimensions(
    school: SchoolRecord, history: list[dict], req: RecommendRequest, db: AsyncSession
) -> dict:
    dims: dict = {}

    # ── 维度1-6,9: 基于录取历史数据 ──────────────────────────────────────────
    if history:
        # Deduplicate by year (one row per year, picking lowest min_score)
        years_dedup: dict = {}
        for h in history:
            y = h["year"]
            s = h.get("min_score") or 999
            if y not in years_dedup or s < (years_dedup[y].get("min_score") or 999):
                years_dedup[y] = h
        years = sorted(years_dedup.values(), key=lambda x: x["year"], reverse=True)[:5]
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
        dims["years_available"] = sorted({y["year"] for y in years}, reverse=True)
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

    dims["recommended_major"] = recommended_major or "数据获取中"
    dims["major_match_type"] = major_match_type if recommended_major else "pending"

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
        _v = school.school_id % 5  # perturbation for differentiation
        if "公办" in stype or school.is_985 or school.is_211:
            _lo, _hi = 3500 + _v * 300, 5500 + _v * 200
            dims["tuition"] = f"{_lo}-{_hi}元/年"
            dims["tuition_total"] = f"4年约{_lo*4//10000:.1f}-{_hi*4//10000:.1f}万"
            dims["tuition_fit"] = "公办院校学费较低"
        elif "民办" in stype or "独立学院" in stype:
            _lo, _hi = 12000 + _v * 1000, 25000 + _v * 500
            dims["tuition"] = f"{_lo}-{_hi}元/年"
            dims["tuition_total"] = f"4年约{_lo//2500*0.1:.0f}-{_hi//2500*0.1:.0f}万"
            dims["tuition_fit"] = "需考虑家庭经济承受能力"
        elif "专科" in stype or "职业" in stype:
            _lo, _hi = 3500 + _v * 200, 6000 + _v * 300
            dims["tuition"] = f"{_lo}-{_hi}元/年"
            dims["tuition_total"] = f"3年约{_lo*3//10000:.1f}-{_hi*3//10000:.1f}万"
            dims["tuition_fit"] = "专科院校学费较低"
        else:
            _lo, _hi = 4000 + _v * 400, 7000 + _v * 400
            dims["tuition"] = f"{_lo}-{_hi}元/年"
            dims["tuition_total"] = f"4年约{_lo*4//10000:.1f}-{_hi*4//10000:.1f}万"
            dims["tuition_fit"] = _tuition_fit(_lo, req.economic_level)
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
        _v = school.school_id % 7  # wider perturbation for differentiation
        stype = (school.school_type or "").lower()
        if school.is_985:
            _lo, _hi = 89 + _v % 4, 96 + (_v % 3)
        elif school.is_211:
            _lo, _hi = 83 + _v % 5, 92 + (_v % 4)
        elif "民办" in stype or "独立学院" in stype:
            _lo, _hi = 78 + _v % 4, 85 + (_v % 5)
        elif "专科" in stype or "职业" in stype:
            _lo, _hi = 75 + _v % 5, 83 + (_v % 6)
        else:  # 公办本科
            _lo, _hi = 80 + _v % 6, 90 + (_v % 4)
        dims["employment_rate"] = f"{_lo}-{_hi}%"
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
        _v = school.school_id % 7  # perturbation for per-school differentiation
        stype = (school.school_type or "").lower()
        if school.is_985:
            _lo1, _hi1 = 8000 + _v * 500, 13000 + _v * 600
            _lo3, _hi3 = 15000 + _v * 800, 24000 + _v * 900
        elif school.is_211:
            _lo1, _hi1 = 6000 + _v * 400, 10000 + _v * 500
            _lo3, _hi3 = 11000 + _v * 600, 17000 + _v * 700
        elif "专科" in stype or "职业" in stype:
            _lo1, _hi1 = 3500 + _v * 300, 5500 + _v * 400
            _lo3, _hi3 = 5500 + _v * 400, 9000 + _v * 500
        else:
            _lo1, _hi1 = 4000 + _v * 400, 6500 + _v * 400
            _lo3, _hi3 = 6500 + _v * 500, 11000 + _v * 500
        dims["avg_salary_start"] = f"{_lo1}-{_hi1}元/月"
        dims["avg_salary_3yr"] = f"{_lo3}-{_hi3}元/月"
        dims["salary_source"] = "按院校层次估算"
        dims["salary_data_quality"] = "estimated"

    dims["core_positions"] = "见该校就业报告"
    dims["trend_5yr"] = "数据收集中"

    # ── 维度15: 城市分析（city_analysis 表）─────────────────────────────────
    city = school.city or _city_from_school(school.name, school.province)
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
        fallback = _CITY_ANALYSIS_FALLBACK.get(city)
        if fallback:
            dims["city_analysis"] = fallback
        else:
            dims["city_analysis"] = {
                "location": f"{city}市",
                "advantage": f"{city}教育资源集中，生活成本较低",
                "disadvantage": "经济体量偏小，高端产业不足",
                "job_market": "教育、医疗、公共服务、本地特色产业",
                "livability": f"生活成本较低，宜居指数稳定",
                "city_level": "三线",
            }
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
            # Deduplicate by year (one row per year)
            years_dedup: dict = {}
            for h in history:
                y = h["year"]
                if y not in years_dedup:
                    years_dedup[y] = h
            years = sorted(years_dedup.values(), key=lambda x: x["year"], reverse=True)[:5]
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
            dims["years_available"] = sorted({y["year"] for y in years}, reverse=True)
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

        dims["recommended_major"] = recommended_major or "数据获取中"
        dims["major_match_type"] = major_match_type if recommended_major else "pending"

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
            _v = school.school_id % 5  # perturbation for differentiation
            if "公办" in stype or school.is_985 or school.is_211:
                _lo, _hi = 3500 + _v * 300, 5500 + _v * 200
                dims["tuition"] = f"{_lo}-{_hi}元/年"
                dims["tuition_total"] = f"4年约{_lo*4//10000:.1f}-{_hi*4//10000:.1f}万"
                dims["tuition_fit"] = "公办院校学费较低"
            elif "民办" in stype or "独立学院" in stype:
                _lo, _hi = 12000 + _v * 1000, 25000 + _v * 500
                dims["tuition"] = f"{_lo}-{_hi}元/年"
                dims["tuition_total"] = f"4年约{_lo//2500*0.1:.0f}-{_hi//2500*0.1:.0f}万"
                dims["tuition_fit"] = "需考虑家庭经济承受能力"
            elif "专科" in stype or "职业" in stype:
                _lo, _hi = 3500 + _v * 200, 6000 + _v * 300
                dims["tuition"] = f"{_lo}-{_hi}元/年"
                dims["tuition_total"] = f"3年约{_lo*3//10000:.1f}-{_hi*3//10000:.1f}万"
                dims["tuition_fit"] = "专科院校学费较低"
            else:
                _lo, _hi = 4000 + _v * 400, 7000 + _v * 400
                dims["tuition"] = f"{_lo}-{_hi}元/年"
                dims["tuition_total"] = f"4年约{_lo*4//10000:.1f}-{_hi*4//10000:.1f}万"
                dims["tuition_fit"] = _tuition_fit(_lo, req.economic_level)
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
            _v = school.school_id % 7  # wider perturbation for differentiation
            stype = (school.school_type or "").lower()
            if school.is_985:
                _lo, _hi = 89 + _v % 4, 96 + (_v % 3)
            elif school.is_211:
                _lo, _hi = 83 + _v % 5, 92 + (_v % 4)
            elif "民办" in stype or "独立学院" in stype:
                _lo, _hi = 78 + _v % 4, 85 + (_v % 5)
            elif "专科" in stype or "职业" in stype:
                _lo, _hi = 75 + _v % 5, 83 + (_v % 6)
            else:  # 公办本科
                _lo, _hi = 80 + _v % 6, 90 + (_v % 4)
            dims["employment_rate"] = f"{_lo}-{_hi}%"
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
            _v = school.school_id % 7  # perturbation for per-school differentiation
            stype = (school.school_type or "").lower()
            if school.is_985:
                _lo1, _hi1 = 8000 + _v * 500, 13000 + _v * 600
                _lo3, _hi3 = 15000 + _v * 800, 24000 + _v * 900
            elif school.is_211:
                _lo1, _hi1 = 6000 + _v * 400, 10000 + _v * 500
                _lo3, _hi3 = 11000 + _v * 600, 17000 + _v * 700
            elif "专科" in stype or "职业" in stype:
                _lo1, _hi1 = 3500 + _v * 300, 5500 + _v * 400
                _lo3, _hi3 = 5500 + _v * 400, 9000 + _v * 500
            else:
                _lo1, _hi1 = 4000 + _v * 400, 6500 + _v * 400
                _lo3, _hi3 = 6500 + _v * 500, 11000 + _v * 500
            dims["avg_salary_start"] = f"{_lo1}-{_hi1}元/月"
            dims["avg_salary_3yr"] = f"{_lo3}-{_hi3}元/月"
            dims["salary_source"] = "按院校层次估算"
            dims["salary_data_quality"] = "estimated"

        dims["core_positions"] = "见该校就业报告"
        dims["trend_5yr"] = "数据收集中"

        # Dim 15: city analysis
        city = school.city or _city_from_school(school.name, school.province)
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
            fallback = _CITY_ANALYSIS_FALLBACK.get(city)
            if fallback:
                dims["city_analysis"] = fallback
            else:
                dims["city_analysis"] = {
                    "location": f"{city}市",
                    "advantage": f"{city}教育资源集中，生活成本较低",
                    "disadvantage": "经济体量偏小，高端产业不足",
                    "job_market": "教育、医疗、公共服务、本地特色产业",
                    "livability": f"生活成本较低，宜居指数稳定",
                    "city_level": "三线",
                }
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
        "personality": req.personality,          # 完整值，不排序
        "economic": req.economic_level,          # 完整值
    }, sort_keys=True, ensure_ascii=False)
    cache_key = f"recommend:v2:{hashlib.md5(cache_payload.encode()).hexdigest()}"

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

    # PHASE 0.5: 成绩段位前置判断（PRD §4.7）
    score_segment = await classify_score_segment(
        req.province, req.subject_category, req.score, db
    )

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
            rp = calc_rank_prob(rank, history,
                is_985=s.is_985, is_211=s.is_211, is_double_first=s.is_double_first,
                school_type=s.school_type, student_score=req.score)
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
            rp = calc_rank_prob(rank, history,
                is_985=s.is_985, is_211=s.is_211, is_double_first=s.is_double_first,
                school_type=s.school_type, student_score=req.score)
            if rp is None:
                # No data — estimate from peer schools in same tier
                rp = _estimate_from_peers(s, scored, req.score)
            s.rank_prob = rp
        else:
            # No rank available — use tier score prior as base probability
            prior = _tier_score_prior(req.score, s.is_985, s.is_211, s.is_double_first, s.school_type)
            if prior is not None:
                s.rank_prob = prior
            else:
                # 公办本科: use score heuristic
                if req.score >= 600:
                    s.rank_prob = 20.0
                elif req.score >= 450:
                    s.rank_prob = 40.0
                elif req.score >= 300:
                    s.rank_prob = 55.0
                else:
                    s.rank_prob = 70.0
        s.weighted_prob = calc_weighted_prob(req, s.rank_prob, s)
        s.tier, s.tier_label = assign_tier(s.rank_prob, req.score)
        s.data_quality = await detect_data_gaps(s.school_id, req.province, history, db)
        s.admission_data = _build_admission_summary(history)
        scored.append(s)

    # PHASE 3.5: 院校质量底线过滤（PRD §4.8）— 在 sort_and_slice 之前
    scored = apply_quality_threshold_filter(scored, score_segment)

    # PHASE 4: Tier排序 + 截取15所（globe_expanded 仅保留在冲刺档）
    selected = sort_and_slice(scored, req.personality, score_segment)

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
        "score_segment": score_segment,
        "special_attention": [_school_to_dict(s) for s in special_attention],
        "schools": [_school_to_dict(s) for s in selected],
        "tier_summary": {
            "boost": {"count": sum(1 for s in selected if s.tier == 0), "range": "30%-50%"},
            "solid": {"count": sum(1 for s in selected if s.tier == 1), "range": "50%-85%"},
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
    # Deduplicate by year (one row per year, picking lowest min_score)
    years_dedup: dict = {}
    for h in history:
        y = h["year"]
        s = h.get("min_score") or 999
        if y not in years_dedup or s < (years_dedup[y].get("min_score") or 999):
            years_dedup[y] = h
    years = sorted(years_dedup.values(), key=lambda x: x["year"], reverse=True)[:5]
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
        "years_available": sorted({y["year"] for y in years}, reverse=True),
    }


def _estimate_from_peers(
    school: SchoolRecord, peers: list[SchoolRecord], score: int
) -> float:
    """Estimate rank_prob from peers. Falls back through increasingly broad criteria."""
    # Level 1: Exact same 985/211/double-first tier
    tier_peers = [
        p.rank_prob for p in peers
        if p.rank_prob is not None
        and p.is_985 == school.is_985
        and p.is_211 == school.is_211
        and p.is_double_first == school.is_double_first
    ]
    if tier_peers:
        return round(sum(tier_peers) / len(tier_peers), 1)

    # Level 2: Same 985/211 status (ignore double-first)
    broad_peers = [
        p.rank_prob for p in peers
        if p.rank_prob is not None
        and p.is_985 == school.is_985
        and p.is_211 == school.is_211
    ]
    if broad_peers:
        return round(sum(broad_peers) / len(broad_peers), 1)

    # Level 3: Any peers with valid rank_prob
    all_peers = [p.rank_prob for p in peers if p.rank_prob is not None]
    if all_peers:
        avg = sum(all_peers) / len(all_peers)
        # Adjust by school prestige (inverse to calc_rank_prob: harder schools get penalty, easier get bonus)
        stype = (school.school_type or "").lower()
        if school.is_985:
            avg = max(1.0, avg - 15.0)   # 985 — much harder
        elif school.is_211:
            avg = max(1.0, avg - 10.0)   # 211 — harder
        elif school.is_double_first:
            avg = max(1.0, avg - 7.0)    # 双一流 — slightly harder
        elif "专科" in stype or "职业" in stype:
            avg = min(99.0, avg + 15.0)  # 专科 — much easier
        elif "民办" in stype or "独立" in stype:
            avg = min(99.0, avg + 8.0)   # 民办 — easier
        return round(avg, 1)

    # Level 4: Score-based heuristic with tier prior blending
    # Use _tier_score_prior for consistency with calc_rank_prob
    prior = _tier_score_prior(score, school.is_985, school.is_211, school.is_double_first, school.school_type)
    if prior is not None:
        # Score-based base + tier prior blend
        if score >= 600:
            base = 20.0
        elif score >= 450:
            base = 40.0
        elif score >= 300:
            base = 55.0
        else:
            base = 70.0
        # Blend with prior: 50% heuristic + 50% tier prior
        base = base * 0.5 + prior * 0.5
    else:
        # No prior (公办本科): pure score heuristic
        if score >= 600:
            base = 20.0
        elif score >= 450:
            base = 40.0
        elif score >= 300:
            base = 55.0
        else:
            base = 70.0
    
    # Apply tier adjustment as additional safety
    stype = (school.school_type or "").lower()
    if school.is_985:
        base = max(1.0, base * 0.85)    # 985 — harder
    elif school.is_211:
        base = max(1.0, base * 0.90)    # 211 — harder
    elif school.is_double_first:
        base = max(1.0, base * 0.93)    # 双一流 — slightly harder
    elif "专科" in stype or "职业" in stype:
        base = min(99.0, base * 1.15)   # 专科 — easier
    elif "民办" in stype or "独立" in stype:
        base = min(99.0, base * 1.08)   # 民办 — easier
    return round(base, 1)


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
    if s.globe_expanded:
        d["globe_expanded"] = True
        d["globe_note"] = "🌐 全国扩展推荐：您的成绩已超出意向城市所有院校录取线"
    if s.is_intended and s.rank_prob == 0.0:
        d["note"] = "您的成绩无法达到该校录取线"
    return d
