"""
报告快照路由
- POST /api/reports/snapshot  — 主播端保存快照（Streamer JWT）
- GET  /admin/report-snapshots — 管理员按 order_id 查询快照（Admin JWT）
- GET  /admin/report-snapshots/{snapshot_id} — 管理员按 id 读全量数据（Admin JWT）
"""
import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_admin, get_current_streamer

router = APIRouter(tags=["report-snapshots"])


# ──────────────────────────────────────────────────────────────────────────────
# 主播端保存快照
# ──────────────────────────────────────────────────────────────────────────────

class SaveSnapshotRequest(BaseModel):
    order_id: str
    student_input: dict
    recommendation_result: dict


@router.post("/api/reports/snapshot")
async def save_snapshot(
    body: SaveSnapshotRequest,
    streamer=Depends(get_current_streamer),
    db: AsyncSession = Depends(get_db),
):
    # 同一 order_id 若已存在则跳过（幂等）
    exists = await db.execute(
        text("SELECT id FROM report_snapshots WHERE order_id = :oid LIMIT 1"),
        {"oid": body.order_id},
    )
    if exists.mappings().first():
        return {"snapshot_id": None, "already_exists": True}

    si = body.student_input
    row = await db.execute(
        text("""
            INSERT INTO report_snapshots
                (order_id, streamer_id, student_nickname, student_province,
                 student_score, student_input, recommendation_result)
            VALUES
                (:oid, :sid, :nick, :prov, :score, :inp, :res)
        """),
        {
            "oid":  body.order_id,
            "sid":  streamer["id"],
            "nick": si.get("nickname") or si.get("student_nickname") or "",
            "prov": si.get("province") or si.get("student_province") or "",
            "score": si.get("score") or si.get("student_score") or 0,
            "inp":  json.dumps(body.student_input,         ensure_ascii=False),
            "res":  json.dumps(body.recommendation_result, ensure_ascii=False),
        },
    )
    await db.commit()
    return {"snapshot_id": row.lastrowid}


# ──────────────────────────────────────────────────────────────────────────────
# 管理员查询快照
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/admin/report-snapshots")
async def get_snapshot_by_order(
    order_id: str = Query(...),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        text("""
            SELECT id, order_id, link_token, streamer_id,
                   student_nickname, student_province, student_score,
                   student_input, recommendation_result, created_at
            FROM report_snapshots
            WHERE order_id = :oid
            ORDER BY created_at DESC
            LIMIT 1
        """),
        {"oid": order_id},
    )
    rec = row.mappings().first()
    if not rec:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "暂无此订单的报告快照")

    return {
        "snapshot": {
            "id":                    rec["id"],
            "order_id":              rec["order_id"],
            "student_nickname":      rec["student_nickname"],
            "student_province":      rec["student_province"],
            "student_score":         rec["student_score"],
            "student_input":         json.loads(rec["student_input"]),
            "recommendation_result": json.loads(rec["recommendation_result"]),
            "created_at":            str(rec["created_at"]),
        }
    }


@router.get("/admin/report-snapshots/{snapshot_id}")
async def get_snapshot_by_id(
    snapshot_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        text("""
            SELECT id, order_id, link_token, streamer_id,
                   student_nickname, student_province, student_score,
                   student_input, recommendation_result, created_at
            FROM report_snapshots
            WHERE id = :sid
        """),
        {"sid": snapshot_id},
    )
    rec = row.mappings().first()
    if not rec:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "快照不存在")

    return {
        "snapshot": {
            "id":                    rec["id"],
            "order_id":              rec["order_id"],
            "student_nickname":      rec["student_nickname"],
            "student_province":      rec["student_province"],
            "student_score":         rec["student_score"],
            "student_input":         json.loads(rec["student_input"]),
            "recommendation_result": json.loads(rec["recommendation_result"]),
            "created_at":            str(rec["created_at"]),
        }
    }
