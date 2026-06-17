"""
热门院校学费种子数据（985/211/双一流，约100所）

数据来源: 各学校官网公开学费公告（2024年数据）
用法: python scripts/seed_hot_school_tuition.py

注意: school_id 需与 schools 表一致。
      脚本会先按学校名查询 school_id，找不到则跳过。
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from api.config import settings

# (school_name, major_name, tuition_per_year, duration_years, data_source, data_year)
# major_name="__default__" 表示该校校级通用学费
RAW_DATA: list[tuple[str, str, int, int, str, int]] = [
    # ── 985 综合类 ──────────────────────────────────────────────────────────
    ("北京大学",     "__default__",       5500,  4, "北大官网", 2024),
    ("北京大学",     "医学",              8000,  5, "北大官网", 2024),
    ("清华大学",     "__default__",       5500,  4, "清华官网", 2024),
    ("复旦大学",     "__default__",       5500,  4, "复旦官网", 2024),
    ("上海交通大学", "__default__",       5500,  4, "交大官网", 2024),
    ("上海交通大学", "医学",              8000,  5, "交大官网", 2024),
    ("浙江大学",     "__default__",       5500,  4, "浙大官网", 2024),
    ("南京大学",     "__default__",       5200,  4, "南大官网", 2024),
    ("中国人民大学", "__default__",       5500,  4, "人大官网", 2024),
    ("北京师范大学", "__default__",       4800,  4, "北师大官网", 2024),
    ("武汉大学",     "__default__",       4800,  4, "武大官网", 2024),
    ("华中科技大学", "__default__",       4800,  4, "华科官网", 2024),
    ("中山大学",     "__default__",       5200,  4, "中大官网", 2024),
    ("中南大学",     "__default__",       4700,  4, "中南官网", 2024),
    ("四川大学",     "__default__",       4800,  4, "川大官网", 2024),
    ("四川大学",     "医学",              7000,  5, "川大官网", 2024),
    ("吉林大学",     "__default__",       4700,  4, "吉大官网", 2024),
    ("山东大学",     "__default__",       4600,  4, "山大官网", 2024),
    ("厦门大学",     "__default__",       5300,  4, "厦大官网", 2024),
    ("同济大学",     "__default__",       5500,  4, "同济官网", 2024),
    ("东南大学",     "__default__",       5400,  4, "东南官网", 2024),
    ("哈尔滨工业大学", "__default__",     4800,  4, "哈工大官网", 2024),
    ("西安交通大学", "__default__",       5000,  4, "西交大官网", 2024),
    ("重庆大学",     "__default__",       4600,  4, "重大官网", 2024),
    ("大连理工大学", "__default__",       4900,  4, "大工官网", 2024),
    ("华南理工大学", "__default__",       5000,  4, "华工官网", 2024),
    ("湖南大学",     "__default__",       4600,  4, "湖大官网", 2024),
    ("兰州大学",     "__default__",       4400,  4, "兰大官网", 2024),
    ("云南大学",     "__default__",       4200,  4, "云大官网", 2024),
    ("郑州大学",     "__default__",       4400,  4, "郑大官网", 2024),
    ("中国海洋大学", "__default__",       5000,  4, "中海大官网", 2024),
    ("新疆大学",     "__default__",       3800,  4, "新疆大学官网", 2024),

    # ── 985 理工类 ──────────────────────────────────────────────────────────
    ("北京理工大学", "__default__",       5200,  4, "北理工官网", 2024),
    ("北京航空航天大学", "__default__",   5300,  4, "北航官网", 2024),
    ("中国科学技术大学", "__default__",   4600,  4, "中科大官网", 2024),
    ("西北工业大学", "__default__",       4800,  4, "西工大官网", 2024),
    ("电子科技大学", "__default__",       4800,  4, "电子科大官网", 2024),
    ("天津大学",     "__default__",       5000,  4, "天大官网", 2024),
    ("华东师范大学", "__default__",       5200,  4, "华东师大官网", 2024),
    ("中国农业大学", "__default__",       4600,  4, "中农大官网", 2024),
    ("中央民族大学", "__default__",       4200,  4, "民大官网", 2024),

    # ── 211 综合/文科类 ────────────────────────────────────────────────────
    ("南开大学",     "__default__",       5000,  4, "南开官网", 2024),
    ("苏州大学",     "__default__",       5800,  4, "苏大官网", 2024),
    ("暨南大学",     "__default__",       5400,  4, "暨南官网", 2024),
    ("中国政法大学", "__default__",       5200,  4, "政法官网", 2024),
    ("对外经济贸易大学", "__default__",   5300,  4, "对外经贸官网", 2024),
    ("中央财经大学", "__default__",       5300,  4, "中财大官网", 2024),
    ("西南财经大学", "__default__",       5000,  4, "西财官网", 2024),
    ("上海财经大学", "__default__",       5800,  4, "上财官网", 2024),
    ("西南大学",     "__default__",       4400,  4, "西南大学官网", 2024),
    ("东北大学",     "__default__",       4700,  4, "东大官网", 2024),
    ("辽宁大学",     "__default__",       4300,  4, "辽大官网", 2024),
    ("福州大学",     "__default__",       4500,  4, "福大官网", 2024),
    ("合肥工业大学", "__default__",       4700,  4, "合工大官网", 2024),
    ("安徽大学",     "__default__",       4300,  4, "安大官网", 2024),
    ("南昌大学",     "__default__",       4400,  4, "南大官网", 2024),
    ("华中农业大学", "__default__",       4400,  4, "华农官网", 2024),
    ("中国地质大学(武汉)", "__default__", 4600,  4, "地大官网", 2024),
    ("武汉理工大学", "__default__",       4800,  4, "武理工官网", 2024),
    ("长安大学",     "__default__",       4600,  4, "长安官网", 2024),
    ("西北农林科技大学", "__default__",   4200,  4, "西农官网", 2024),
    ("石河子大学",   "__default__",       3800,  4, "石大官网", 2024),
    ("内蒙古大学",   "__default__",       3900,  4, "内大官网", 2024),
    ("广西大学",     "__default__",       4200,  4, "广大官网", 2024),
    ("贵州大学",     "__default__",       4000,  4, "贵大官网", 2024),

    # ── 211 理工类 ────────────────────────────────────────────────────────
    ("北京邮电大学", "__default__",       5500,  4, "北邮官网", 2024),
    ("北京交通大学", "__default__",       5200,  4, "北交大官网", 2024),
    ("北京化工大学", "__default__",       5200,  4, "北化工官网", 2024),
    ("北京科技大学", "__default__",       5000,  4, "北科大官网", 2024),
    ("中国矿业大学", "__default__",       4500,  4, "矿大官网", 2024),
    ("西安电子科技大学", "__default__",   4600,  4, "西电官网", 2024),
    ("江南大学",     "__default__",       5200,  4, "江南官网", 2024),
    ("扬州大学",     "__default__",       5000,  4, "扬大官网", 2024),
    ("宁波大学",     "__default__",       5600,  4, "宁大官网", 2024),
    ("华中师范大学", "__default__",       4700,  4, "华师官网", 2024),
    ("河海大学",     "__default__",       5000,  4, "河海官网", 2024),
    ("太原理工大学", "__default__",       4300,  4, "太理工官网", 2024),
    ("山西大学",     "__default__",       3900,  4, "山西大学官网", 2024),
    ("燕山大学",     "__default__",       4500,  4, "燕大官网", 2024),
    ("东北师范大学", "__default__",       4500,  4, "东师官网", 2024),
    ("华东理工大学", "__default__",       5400,  4, "华理工官网", 2024),
    ("上海大学",     "__default__",       5600,  4, "上大官网", 2024),

    # ── 热门专业学费差异化（部分院校）──────────────────────────────────────
    ("北京大学",     "法学",              5500,  4, "北大官网", 2024),
    ("清华大学",     "建筑学",            5500,  5, "清华官网", 2024),
    ("浙江大学",     "软件工程",          5500,  4, "浙大官网", 2024),
    ("复旦大学",     "临床医学",          8000,  5, "复旦官网", 2024),
    ("华中科技大学", "软件工程",          4800,  4, "华科官网", 2024),
    ("西安交通大学", "临床医学",          7500,  5, "西交大官网", 2024),
    ("中山大学",     "临床医学",          7000,  5, "中大官网", 2024),
    ("武汉大学",     "测绘工程",          4800,  4, "武大官网", 2024),
    ("山东大学",     "临床医学",          6500,  5, "山大官网", 2024),
    ("吉林大学",     "临床医学",          6000,  5, "吉大官网", 2024),
    ("中南大学",     "临床医学",          6500,  5, "中南官网", 2024),
    ("四川大学",     "建筑学",            4800,  5, "川大官网", 2024),
]


async def seed():
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Build name → id map for schools we have data for
        names = list({row[0] for row in RAW_DATA})
        placeholders = ", ".join(f":n{i}" for i in range(len(names)))
        r = await session.execute(
            text(f"SELECT id, name FROM schools WHERE name IN ({placeholders})"),
            {f"n{i}": name for i, name in enumerate(names)},
        )
        name_to_id: dict[str, int] = {row["name"]: row["id"] for row in r.mappings()}

        inserted = skipped = 0
        for school_name, major_name, tuition, duration, source, year in RAW_DATA:
            school_id = name_to_id.get(school_name)
            if not school_id:
                print(f"  SKIP (no school_id): {school_name}")
                skipped += 1
                continue
            try:
                await session.execute(
                    text("""
                        INSERT INTO school_tuition
                            (school_id, major_name, tuition_per_year, duration_years,
                             data_source, data_year)
                        VALUES (:sid, :major, :tuition, :dur, :src, :yr)
                        ON DUPLICATE KEY UPDATE
                            tuition_per_year = VALUES(tuition_per_year),
                            duration_years   = VALUES(duration_years),
                            data_source      = VALUES(data_source),
                            data_year        = VALUES(data_year),
                            updated_at       = NOW()
                    """),
                    {
                        "sid": school_id, "major": major_name,
                        "tuition": tuition, "dur": duration,
                        "src": source, "yr": year,
                    },
                )
                inserted += 1
            except Exception as e:
                print(f"  ERR {school_name} / {major_name}: {e}")
                skipped += 1

        await session.commit()
        print(f"school_tuition: {inserted} upserted, {skipped} skipped")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
