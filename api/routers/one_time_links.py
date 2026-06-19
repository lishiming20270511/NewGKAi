"""
一次性链接系统 — PRD v5.4

管理员：生成批次 / 查询批次 / 作废整批
学生端：校验令牌 / 消费令牌 / 一键推荐+消费（无需 JWT）
"""
import hashlib
import hmac
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..deps import get_current_admin
from ..services.recommendation import RecommendRequest as SvcReq, generate_recommendation

router = APIRouter(tags=["one-time-links"])


# ─── 令牌生成工具 ────────────────────────────────────────────────────────────

def _make_token() -> str:
    """生成 UUID4.HMAC(12位) 格式的防伪令牌。"""
    uid = str(uuid.uuid4())
    sig = hmac.new(
        settings.jwt_secret.encode(),
        uid.encode(),
        hashlib.sha256,
    ).hexdigest()[:12]
    return f"{uid}.{sig}"


def _verify_token_signature(token: str) -> bool:
    """校验令牌 HMAC 签名。"""
    try:
        uid_part, sig_part = token.rsplit(".", 1)
        expected = hmac.new(
            settings.jwt_secret.encode(),
            uid_part.encode(),
            hashlib.sha256,
        ).hexdigest()[:12]
        return hmac.compare_digest(sig_part, expected)
    except Exception:
        return False


# ─── Admin: 生成批次 ─────────────────────────────────────────────────────────

class GenerateLinksRequest(BaseModel):
    note: Optional[str] = Field(None, max_length=50, description="批次备注")
    count: int = Field(..., ge=1, le=100, description="生成数量")


@router.post("/admin/one-time-links/generate")
async def generate_links(
    body: GenerateLinksRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    # 创建批次
    result = await db.execute(
        text("""
            INSERT INTO one_time_link_batches (note, total_count, created_by)
            VALUES (:note, :count, :admin_id)
        """),
        {"note": body.note, "count": body.count, "admin_id": admin["id"]},
    )
    batch_id = result.lastrowid

    # 批量生成令牌
    tokens = [_make_token() for _ in range(body.count)]
    for token in tokens:
        await db.execute(
            text("""
                INSERT INTO one_time_links (token, batch_id, batch_note, status)
                VALUES (:token, :batch_id, :batch_note, 'active')
            """),
            {"token": token, "batch_id": batch_id, "batch_note": body.note},
        )

    await db.commit()

    base_url = "http://121.41.69.234"
    links = [f"{base_url}/s?t={t}" for t in tokens]
    return {"batch_id": batch_id, "links": links}


# ─── Admin: 查询批次列表 ─────────────────────────────────────────────────────

@router.get("/admin/one-time-links")
async def list_link_batches(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page

    rows = await db.execute(
        text("""
            SELECT
                b.id, b.note, b.total_count, b.created_at,
                SUM(CASE WHEN l.status = 'used'    THEN 1 ELSE 0 END) AS used_count,
                SUM(CASE WHEN l.status = 'active'  THEN 1 ELSE 0 END) AS active_count,
                SUM(CASE WHEN l.status = 'revoked' THEN 1 ELSE 0 END) AS revoked_count
            FROM one_time_link_batches b
            LEFT JOIN one_time_links l ON l.batch_id = b.id
            GROUP BY b.id
            ORDER BY b.id DESC
            LIMIT :limit OFFSET :offset
        """),
        {"limit": per_page, "offset": offset},
    )

    total_row = await db.execute(
        text("SELECT COUNT(*) FROM one_time_link_batches")
    )
    total = total_row.scalar() or 0

    batches = [dict(r) for r in rows.mappings()]
    for b in batches:
        if isinstance(b.get("created_at"), datetime):
            b["created_at"] = b["created_at"].isoformat()

    return {"total": total, "page": page, "batches": batches}


# ─── Admin: 查看批次详情 ─────────────────────────────────────────────────────

@router.get("/admin/one-time-links/{batch_id}/detail")
async def get_batch_detail(
    batch_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(
        text("""
            SELECT id, LEFT(token, 8) AS token_prefix, status, used_at, used_ip
            FROM one_time_links
            WHERE batch_id = :bid
            ORDER BY id
        """),
        {"bid": batch_id},
    )
    links = []
    for r in rows.mappings():
        item = dict(r)
        if isinstance(item.get("used_at"), datetime):
            item["used_at"] = item["used_at"].isoformat()
        links.append(item)
    return {"batch_id": batch_id, "links": links}


# ─── Admin: 作废整批 ─────────────────────────────────────────────────────────

class RevokeBatchRequest(BaseModel):
    batch_id: int


@router.post("/admin/one-time-links/revoke-batch")
async def revoke_batch(
    body: RevokeBatchRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("""
            UPDATE one_time_links
            SET status = 'revoked'
            WHERE batch_id = :bid AND status = 'active'
        """),
        {"bid": body.batch_id},
    )
    await db.commit()
    return {"batch_id": body.batch_id, "revoked_count": result.rowcount}


# ─── 学生端: 校验令牌 ────────────────────────────────────────────────────────

@router.get("/s/validate")
async def validate_token(
    t: str = Query(..., description="一次性令牌"),
    db: AsyncSession = Depends(get_db),
):
    if not _verify_token_signature(t):
        return {"status": "invalid"}

    row = await db.execute(
        text("SELECT status FROM one_time_links WHERE token = :token"),
        {"token": t},
    )
    rec = row.mappings().first()
    if not rec:
        return {"status": "invalid"}
    return {"status": rec["status"]}


# ─── 学生端: 消费令牌（推荐生成成功后调用）──────────────────────────────────

class ConsumeTokenRequest(BaseModel):
    token: str


@router.post("/s/consume")
async def consume_token(
    body: ConsumeTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if not _verify_token_signature(body.token):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "无效令牌")

    client_ip = request.headers.get("X-Real-IP", request.client.host if request.client else "unknown")

    # 行锁保证并发安全
    row = await db.execute(
        text("SELECT id, status FROM one_time_links WHERE token = :token FOR UPDATE"),
        {"token": body.token},
    )
    rec = row.mappings().first()

    if not rec:
        await db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "令牌不存在")

    if rec["status"] != "active":
        await db.rollback()
        msg = "链接已被使用" if rec["status"] == "used" else "链接已作废"
        raise HTTPException(status.HTTP_409_CONFLICT, msg)

    await db.execute(
        text("""
            UPDATE one_time_links
            SET status = 'used', used_at = NOW(), used_ip = :ip
            WHERE id = :id
        """),
        {"ip": client_ip, "id": rec["id"]},
    )
    await db.commit()
    return {"success": True}


# ─── 学生端: 推荐生成 + 消费（原子操作）───────────────────────────────────────

_SCORE_MAX: dict[str, int] = {"上海": 660}
_DEFAULT_SCORE_MAX = 750


class StudentRecommendRequest(BaseModel):
    token: str
    province: str = Field(..., min_length=2, max_length=32)
    score: int = Field(..., ge=0, le=900)
    subject_category: str = Field(..., min_length=2, max_length=16)
    rank: Optional[int] = Field(None, ge=1)
    city_preference: List[str] = Field(default_factory=list)
    intended_schools: List[str] = Field(default_factory=list)
    major_preference: List[str] = Field(default_factory=list)
    personality: List[str] = Field(default_factory=list)
    economic_level: str = Field("一般", max_length=16)

    @field_validator("score")
    @classmethod
    def cap_score(cls, v, info):
        province = info.data.get("province", "")
        return min(v, _SCORE_MAX.get(province, _DEFAULT_SCORE_MAX))


@router.post("/s/recommend")
async def student_recommend(
    body: StudentRecommendRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if not _verify_token_signature(body.token):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "无效令牌")

    client_ip = request.headers.get("X-Real-IP", request.client.host if request.client else "unknown")

    # 行锁：校验 + 消费原子操作
    row = await db.execute(
        text("SELECT id, status FROM one_time_links WHERE token = :token FOR UPDATE"),
        {"token": body.token},
    )
    rec = row.mappings().first()

    if not rec:
        await db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "令牌不存在")

    if rec["status"] != "active":
        await db.rollback()
        msg = "链接已被使用" if rec["status"] == "used" else "链接已作废"
        raise HTTPException(status.HTTP_409_CONFLICT, msg)

    # 生成推荐
    req = SvcReq(
        province=body.province,
        score=body.score,
        subject_category=body.subject_category,
        rank=body.rank,
        city_preference=body.city_preference,
        intended_schools=body.intended_schools,
        major_preference=body.major_preference,
        personality=body.personality,
        economic_level=body.economic_level,
    )
    result = await generate_recommendation(req, db)

    # 标记已使用
    await db.execute(
        text("""
            UPDATE one_time_links
            SET status = 'used', used_at = NOW(), used_ip = :ip
            WHERE id = :id
        """),
        {"ip": client_ip, "id": rec["id"]},
    )
    await db.commit()
    return result
