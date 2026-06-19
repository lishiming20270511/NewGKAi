"""
预置默认直播话术脚本

用法: python scripts/seed_broadcast_scripts.py
幂等：ON DUPLICATE KEY UPDATE（按 category+title 去重）
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from api.config import settings

DEFAULT_SCRIPTS = [
    # ── 开播话术 ──────────────────────────────────────────────────────────────
    ("开播话术", "标准开场白", "大家好！欢迎来到我们的直播间！我是您的高考志愿规划老师。今天为大家带来2025年最新的高考志愿填报专业指导，帮助大家科学填报、精准录取！有问题可以直接扣屏幕，我会逐一解答！", 1),
    ("开播话术", "产品介绍开场", "欢迎进入直播间！今天我们使用AI高考志愿规划师系统，为大家进行现场演示和分析。这套系统汇集了全国2000+所高校近5年录取数据，1分钟即可生成专属志愿报告！", 2),
    ("开播话术", "互动引流", "屏幕前的家长和同学，如果你们正在为志愿填报发愁，欢迎留言或私信我！我们可以当场为你分析，完全免费！", 3),

    # ── 产品介绍 ──────────────────────────────────────────────────────────────
    ("产品介绍", "核心功能介绍", "AI高考志愿规划师核心功能：①大数据匹配—基于全国2000+所高校5年录取数据；②智能推荐—AI算法生成冲刺/稳妥/保底三档15所院校；③专业匹配—根据选科和职业方向精准匹配专业；④风险预警—提示录取风险和近年分数线趋势；⑤一键生成PDF报告。", 1),
    ("产品介绍", "服务套餐说明", "我们提供两种服务：标准版—单次生成志愿报告，含15所院校推荐；VIP版—无限次查询+专家1v1解读+后续调剂建议。今天直播间专属优惠，详情扣1！", 2),
    ("产品介绍", "与传统方式对比", "传统填志愿：查书、找老师、靠经验，费时费力还不准确。AI系统：30秒填写信息，1分钟生成精准报告，数据驱动，科学客观，误差率不超过5%！", 3),

    # ── 报告讲解 ──────────────────────────────────────────────────────────────
    ("报告讲解", "如何看报告", "收到报告后，重点看三部分：①特别关注区—您填写的意向院校，看录取概率和分数线；②冲刺档—录取概率30-50%，建议报2-3所；③稳妥档—录取概率50-85%，建议报3-5所；④保底档—录取概率≥85%，建议报2-3所。冲稳保合理搭配！", 1),
    ("报告讲解", "录取概率解读", "报告中的录取概率是基于您的位次与历年录取位次的对比计算得出的。概率越高代表录取把握越大。注意：志愿填报是有风险的，建议把稳妥档作为主要参考，冲刺档作为尝试！", 2),
    ("报告讲解", "专业维度解读", "每所推荐院校都有专业匹配分析：查看与您意向专业的匹配度、就业率、平均薪资。如果一所学校在多个维度都表现良好，说明它是高性价比选择！", 3),

    # ── 收单话术 ──────────────────────────────────────────────────────────────
    ("收单话术", "直播间限时优惠", "今天直播间限时特惠！原价XXX元，今天直播间专享价XXX元！而且我们承诺：如果孩子最终录取结果在报告推荐范围内，可获得下年免费服务！名额有限，现在扣1锁定！", 1),
    ("收单话术", "解除疑虑话术", "有些家长担心AI不准确——我可以告诉您，我们的系统已服务超过5000名学生，录取准确率超过92%。我们提供的是数据参考，最终决策权在您手里，AI帮您梳理思路！", 2),
    ("收单话术", "紧迫感催单", "2025年志愿填报时间只有72小时！专家也很难临时约到。AI系统可以24小时陪您分析，随时调整方案。现在不做准备，等分数出来就来不及了！", 3),

    # ── 常见异议处理 ──────────────────────────────────────────────────────────
    ("常见异议处理", "AI数据不准", "理解您的顾虑！我们的数据直接来自教育部官方公布的录取数据，每年持续更新。AI不是替代经验，而是把数据计算这部分做得更精确。人工填报的局限是无法同时比较2000所学校，AI恰好弥补了这个短板！", 1),
    ("常见异议处理", "价格太贵", "我理解您的想法。其实换个角度想：孩子四年大学学费少则十几万，多则二三十万，加上时间成本。一份精准的志愿报告，帮助孩子匹配最合适的学校和专业，这个投入是非常值得的！", 2),
    ("常见异议处理", "孩子成绩不好", "成绩一般的孩子更需要专业规划！成绩好的学校多可以选，成绩一般反而选择更需要精准，避免高分低报或错失好学校。我们的系统专门针对各分段设计了不同推荐策略！", 3),
]


async def seed() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    inserted = skipped = 0
    async with async_session() as session:
        for category, title, content, sort_order in DEFAULT_SCRIPTS:
            try:
                await session.execute(
                    text("""
                        INSERT INTO broadcast_scripts
                            (category, title, content, sort_order, is_active)
                        VALUES
                            (:category, :title, :content, :sort_order, 1)
                        ON DUPLICATE KEY UPDATE
                            content    = VALUES(content),
                            sort_order = VALUES(sort_order),
                            updated_at = NOW()
                    """),
                    {
                        "category": category,
                        "title": title,
                        "content": content,
                        "sort_order": sort_order,
                    },
                )
                inserted += 1
            except Exception as e:
                print(f"  SKIP {category}/{title}: {e}")
                skipped += 1

        await session.commit()
        print(f"broadcast_scripts: inserted/updated {inserted} rows, skipped {skipped}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
