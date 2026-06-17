#!/usr/bin/env python3
"""
crawler_staging → admission_history 校验迁移脚本
crontab: */5 * * * * /root/gaokao-ai/.venv/bin/python /root/gaokao-ai/scripts/check_staging.py
"""

import sys
import os
import logging
from datetime import datetime

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aiomysql
import asyncio
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/tmp/check_staging.log"),
    ],
)
log = logging.getLogger(__name__)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "gaokao_user"),
    "password": os.getenv("DB_PASSWORD", ""),
    "db": os.getenv("DB_NAME", "gaokao_ai"),
    "charset": "utf8mb4",
    "autocommit": False,
}

BATCH_SIZE = 200


def validate_record(row: dict) -> str | None:
    """Return error description or None if valid."""
    if not row["school_id"] or not row["province"] or not row["year"]:
        return "missing_field: school_id/province/year required"
    if row["min_rank"] is not None and row["min_rank"] <= 0:
        return f"invalid_value: min_rank={row['min_rank']} must be > 0"
    if row["min_score"] is not None and not (0 <= row["min_score"] <= 800):
        return f"invalid_value: min_score={row['min_score']} out of range [0,800]"
    if row["year"] < 2000 or row["year"] > 2030:
        return f"invalid_value: year={row['year']} out of range"
    return None


async def process_batch(conn):
    async with conn.cursor(aiomysql.DictCursor) as cur:
        # Fetch pending batch
        await cur.execute(
            """SELECT id, school_id, major_name, year, province, category,
                      batch, min_score, min_rank, source_ip, crawled_at
               FROM crawler_staging
               WHERE status = 'pending'
               ORDER BY id
               LIMIT %s
               FOR UPDATE""",
            (BATCH_SIZE,),
        )
        rows = await cur.fetchall()

    if not rows:
        return 0, 0

    validated = rejected = 0
    now = datetime.utcnow()
    ids_ok, ids_err = [], []

    for row in rows:
        err = validate_record(row)
        if err:
            async with conn.cursor() as cur:
                await cur.execute(
                    """INSERT INTO crawler_error_log
                           (school_id, province, year, category, raw_data,
                            error_type, error_msg, source_ip)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        row["school_id"],
                        row["province"],
                        row["year"],
                        row["category"],
                        str(row),
                        "validation_error",
                        err,
                        row["source_ip"],
                    ),
                )
            ids_err.append(row["id"])
            rejected += 1
            continue

        # Upsert into admission_history (ON DUPLICATE KEY handles dedup via uk_admission)
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO admission_history
                       (school_id, major_name, year, province, category,
                        batch, min_score, min_rank)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE
                       min_score  = VALUES(min_score),
                       min_rank   = VALUES(min_rank),
                       batch      = VALUES(batch)""",
                (
                    row["school_id"],
                    row["major_name"],
                    row["year"],
                    row["province"],
                    row["category"],
                    row["batch"],
                    row["min_score"],
                    row["min_rank"],
                ),
            )
        ids_ok.append(row["id"])
        validated += 1

    # Mark validated
    if ids_ok:
        placeholders = ",".join(["%s"] * len(ids_ok))
        async with conn.cursor() as cur:
            await cur.execute(
                f"""UPDATE crawler_staging
                    SET status='processed', validated_at=%s
                    WHERE id IN ({placeholders})""",
                [now] + ids_ok,
            )

    # Mark rejected
    if ids_err:
        placeholders = ",".join(["%s"] * len(ids_err))
        async with conn.cursor() as cur:
            await cur.execute(
                f"""UPDATE crawler_staging
                    SET status='rejected', validated_at=%s,
                        error_msg='validation_failed'
                    WHERE id IN ({placeholders})""",
                [now] + ids_err,
            )

    await conn.commit()
    return validated, rejected


async def main():
    pool = await aiomysql.create_pool(**DB_CONFIG)
    total_ok = total_err = 0

    async with pool.acquire() as conn:
        while True:
            ok, err = await process_batch(conn)
            total_ok += ok
            total_err += err
            if ok + err < BATCH_SIZE:
                break

    pool.close()
    await pool.wait_closed()

    if total_ok or total_err:
        log.info(f"check_staging done: validated={total_ok}, rejected={total_err}")
    else:
        log.debug("check_staging: no pending records")


if __name__ == "__main__":
    asyncio.run(main())
