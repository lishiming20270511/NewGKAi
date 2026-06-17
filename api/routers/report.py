import hashlib
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_streamer

router = APIRouter(prefix="/api/report", tags=["report"])
logger = logging.getLogger(__name__)


class ReportLogRequest(BaseModel):
    order_id: str = Field(..., max_length=32)
    student_nickname: str = Field("", max_length=64)
    student_province: str = Field("", max_length=32)
    student_score: int = Field(0, ge=0, le=900)
    intended_schools: list[str] = Field(default_factory=list)


@router.post("/log")
async def log_report(
    body: ReportLogRequest,
    current_streamer: dict = Depends(get_current_streamer),
    db: AsyncSession = Depends(get_db),
):
    sid = current_streamer["id"]
    score = body.student_score
    score_low = (score // 5) * 5
    score_range = f"{score_low}-{score_low + 5}"

    student_hash = hashlib.sha256(
        f"{body.student_nickname}:{body.student_province}:{score}".encode()
    ).hexdigest()[:64]

    import json
    school_hash = hashlib.sha256(
        json.dumps(sorted(body.intended_schools), ensure_ascii=False).encode()
    ).hexdigest()[:64]

    # Check similarity against last 10 reports from this streamer
    rows = await db.execute(
        text("""
            SELECT student_hash, score_range, province, school_hash
            FROM report_tasks
            WHERE streamer_id = :sid
            ORDER BY created_at DESC
            LIMIT 10
        """),
        {"sid": sid},
    )
    recent = rows.mappings().all()

    similar_count = sum(
        1
        for r in recent
        if (
            r["province"] == body.student_province
            and r["school_hash"] == school_hash
            and _score_ranges_overlap(r["score_range"], score_range)
        )
    )

    # Determine similarity flag (T2.8 anti-fraud logic)
    if similar_count >= 2:
        similarity_flag = 2
        logger.warning(
            "[ALERT] Streamer %d suspected resale: province=%s score=%d similar_count=%d",
            sid, body.student_province, score, similar_count,
        )
    elif similar_count >= 1:
        similarity_flag = 1
    else:
        similarity_flag = 0

    await db.execute(
        text("""
            UPDATE report_tasks
            SET similarity_flag = :flag
            WHERE order_id = :oid
        """),
        {"flag": similarity_flag, "oid": body.order_id},
    )
    await db.commit()

    return {"success": True, "similarity_flag": similarity_flag}


def _score_ranges_overlap(range_a: str, range_b: str) -> bool:
    """Two score ranges overlap if they are within ±10 points (2 buckets) of each other."""
    try:
        a_low = int(range_a.split("-")[0])
        b_low = int(range_b.split("-")[0])
        return abs(a_low - b_low) <= 10
    except Exception:
        return False
