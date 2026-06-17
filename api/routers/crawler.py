from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError, jwt
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db

router = APIRouter(prefix="/internal/crawler", tags=["crawler-internal"])


# ─── Auth ───────────────────────────────────────────────────────────────────

def _verify_internal_token(request: Request) -> None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing internal token")
    token = auth[7:]
    try:
        jwt.decode(token, settings.internal_jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid internal token")


# ─── Schemas ─────────────────────────────────────────────────────────────────

class AdmissionRecord(BaseModel):
    school_id: int = Field(..., gt=0)
    major_name: Optional[str] = None
    year: int = Field(..., ge=2000, le=2030)
    province: str = Field(..., min_length=2, max_length=32)
    category: Optional[str] = Field(None, max_length=16)
    batch: Optional[str] = Field(None, max_length=32)
    min_score: Optional[int] = Field(None, ge=0, le=900)
    min_rank: Optional[int] = Field(None, ge=0)

    @field_validator("min_score")
    @classmethod
    def score_reasonable(cls, v):
        if v is not None and v > 800:
            raise ValueError("min_score exceeds 800")
        return v

    @field_validator("min_rank")
    @classmethod
    def rank_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("min_rank must be > 0")
        return v


class IngestRequest(BaseModel):
    records: list[AdmissionRecord] = Field(..., min_length=1, max_length=500)


class IngestResponse(BaseModel):
    ingested: int
    rejected: int


# ─── Endpoint ────────────────────────────────────────────────────────────────

@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    payload: IngestRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    _verify_internal_token(request)

    source_ip = request.headers.get("X-Real-IP", request.client.host if request.client else "unknown")
    crawled_at = datetime.utcnow()
    ingested = 0
    rejected = 0

    for rec in payload.records:
        try:
            await db.execute(
                text("""
                    INSERT INTO crawler_staging
                        (school_id, major_name, year, province, category,
                         batch, min_score, min_rank, source_ip, crawled_at, status)
                    VALUES
                        (:school_id, :major_name, :year, :province, :category,
                         :batch, :min_score, :min_rank, :source_ip, :crawled_at, 'pending')
                """),
                {
                    "school_id": rec.school_id,
                    "major_name": rec.major_name,
                    "year": rec.year,
                    "province": rec.province,
                    "category": rec.category,
                    "batch": rec.batch,
                    "min_score": rec.min_score,
                    "min_rank": rec.min_rank,
                    "source_ip": source_ip,
                    "crawled_at": crawled_at,
                },
            )
            ingested += 1
        except Exception as exc:
            await db.execute(
                text("""
                    INSERT INTO crawler_error_log
                        (school_id, province, year, category, raw_data,
                         error_type, error_msg, source_ip)
                    VALUES
                        (:school_id, :province, :year, :category, :raw_data,
                         'insert_error', :error_msg, :source_ip)
                """),
                {
                    "school_id": rec.school_id,
                    "province": rec.province,
                    "year": rec.year,
                    "category": rec.category,
                    "raw_data": rec.model_dump_json(),
                    "error_msg": str(exc),
                    "source_ip": source_ip,
                },
            )
            rejected += 1

    await db.commit()
    return IngestResponse(ingested=ingested, rejected=rejected)
