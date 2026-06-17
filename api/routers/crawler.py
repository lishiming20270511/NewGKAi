"""
爬虫数据网关 — v4.0
支持6种数据类型: admission / major / tuition / employment / salary / city
"""
from datetime import datetime
from typing import Annotated, Literal, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError, jwt
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db

router = APIRouter(prefix="/internal/crawler", tags=["crawler-internal"])


# ─── Auth ────────────────────────────────────────────────────────────────────

def _verify_internal_token(request: Request) -> None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing internal token")
    try:
        jwt.decode(auth[7:], settings.internal_jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid internal token")


# ─── Record Schemas ──────────────────────────────────────────────────────────

class AdmissionRecord(BaseModel):
    school_id: int = Field(..., gt=0)
    major_name: Optional[str] = None
    year: int = Field(..., ge=2000, le=2030)
    province: str = Field(..., min_length=2, max_length=32)
    category: Optional[str] = Field(None, max_length=16)
    batch: Optional[str] = Field(None, max_length=32)
    min_score: Optional[int] = Field(None, ge=0, le=800)
    min_rank: Optional[int] = Field(None, gt=0)


class MajorRecord(BaseModel):
    school_id: int = Field(..., gt=0)
    major_name: str = Field(..., min_length=1, max_length=128)
    major_level: Optional[str] = Field(None, max_length=32)
    discipline: Optional[str] = Field(None, max_length=64)


class TuitionRecord(BaseModel):
    school_id: int = Field(..., gt=0)
    major_name: str = Field(..., min_length=1, max_length=128)
    tuition_per_year: int = Field(..., ge=0, le=200000)
    duration_years: int = Field(4, ge=2, le=8)
    data_source: Optional[str] = Field(None, max_length=255)
    data_year: Optional[int] = Field(None, ge=2020, le=2030)


class EmploymentRecord(BaseModel):
    school_id: int = Field(..., gt=0)
    employment_rate: Optional[float] = Field(None, ge=0, le=100)
    graduate_rate: Optional[float] = Field(None, ge=0, le=100)
    data_source: Optional[str] = Field(None, max_length=255)
    data_year: Optional[int] = Field(None, ge=2020, le=2030)

    @field_validator("employment_rate", "graduate_rate")
    @classmethod
    def rate_2dp(cls, v):
        if v is not None:
            return round(v, 2)
        return v


class SalaryRecord(BaseModel):
    school_id: int = Field(..., gt=0)
    major_name: Optional[str] = Field(None, max_length=128)
    salary_start_min: Optional[int] = Field(None, ge=0)
    salary_start_max: Optional[int] = Field(None, ge=0)
    salary_3yr_min: Optional[int] = Field(None, ge=0)
    salary_3yr_max: Optional[int] = Field(None, ge=0)
    data_source: Optional[str] = Field(None, max_length=255)
    data_year: Optional[int] = Field(None, ge=2020, le=2030)


class CityRecord(BaseModel):
    city_name: str = Field(..., min_length=2, max_length=32)
    location: str = Field(..., min_length=1)
    advantage: str = Field(..., min_length=1)
    development: str = Field(..., min_length=1)
    main_business: str = Field(..., min_length=1)
    city_level: Optional[str] = Field(None, max_length=16)


# ─── Request / Response ──────────────────────────────────────────────────────

class AdmissionIngest(BaseModel):
    data_type: Literal["admission"]
    records: list[AdmissionRecord] = Field(..., min_length=1, max_length=500)


class MajorIngest(BaseModel):
    data_type: Literal["major"]
    records: list[MajorRecord] = Field(..., min_length=1, max_length=500)


class TuitionIngest(BaseModel):
    data_type: Literal["tuition"]
    records: list[TuitionRecord] = Field(..., min_length=1, max_length=500)


class EmploymentIngest(BaseModel):
    data_type: Literal["employment"]
    records: list[EmploymentRecord] = Field(..., min_length=1, max_length=500)


class SalaryIngest(BaseModel):
    data_type: Literal["salary"]
    records: list[SalaryRecord] = Field(..., min_length=1, max_length=500)


class CityIngest(BaseModel):
    data_type: Literal["city"]
    records: list[CityRecord] = Field(..., min_length=1, max_length=100)


IngestRequest = Annotated[
    Union[AdmissionIngest, MajorIngest, TuitionIngest, EmploymentIngest, SalaryIngest, CityIngest],
    Field(discriminator="data_type"),
]


class IngestResponse(BaseModel):
    data_type: str
    ingested: int
    rejected: int


# ─── Per-type write helpers ──────────────────────────────────────────────────

async def _ingest_admission(records, source_ip: str, db: AsyncSession) -> tuple[int, int]:
    ingested = rejected = 0
    ts = datetime.utcnow()
    for rec in records:
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
                {**rec.model_dump(), "source_ip": source_ip, "crawled_at": ts},
            )
            ingested += 1
        except Exception as exc:
            await db.execute(
                text("""
                    INSERT INTO crawler_error_log
                        (school_id, province, year, category, raw_data,
                         error_type, error_msg, source_ip)
                    VALUES (:school_id, :province, :year, :category, :raw,
                            'insert_error', :msg, :ip)
                """),
                {
                    "school_id": rec.school_id, "province": rec.province,
                    "year": rec.year, "category": rec.category,
                    "raw": rec.model_dump_json(), "msg": str(exc), "ip": source_ip,
                },
            )
            rejected += 1
    return ingested, rejected


async def _ingest_major(records, db: AsyncSession) -> tuple[int, int]:
    ingested = rejected = 0
    for rec in records:
        try:
            await db.execute(
                text("""
                    INSERT INTO school_majors (school_id, major_name, major_level, discipline)
                    VALUES (:school_id, :major_name, :major_level, :discipline)
                    ON DUPLICATE KEY UPDATE
                        major_level = COALESCE(VALUES(major_level), major_level),
                        discipline  = COALESCE(VALUES(discipline),  discipline)
                """),
                rec.model_dump(),
            )
            ingested += 1
        except Exception:
            rejected += 1
    return ingested, rejected


async def _ingest_tuition(records, db: AsyncSession) -> tuple[int, int]:
    ingested = rejected = 0
    for rec in records:
        try:
            await db.execute(
                text("""
                    INSERT INTO school_tuition
                        (school_id, major_name, tuition_per_year, duration_years,
                         data_source, data_year)
                    VALUES
                        (:school_id, :major_name, :tuition_per_year, :duration_years,
                         :data_source, :data_year)
                    ON DUPLICATE KEY UPDATE
                        tuition_per_year = VALUES(tuition_per_year),
                        duration_years   = VALUES(duration_years),
                        data_source      = VALUES(data_source),
                        data_year        = VALUES(data_year),
                        updated_at       = NOW()
                """),
                rec.model_dump(),
            )
            ingested += 1
        except Exception:
            rejected += 1
    return ingested, rejected


async def _ingest_employment(records, db: AsyncSession) -> tuple[int, int]:
    ingested = rejected = 0
    for rec in records:
        try:
            await db.execute(
                text("""
                    INSERT INTO school_employment
                        (school_id, employment_rate, graduate_rate, data_source, data_year)
                    VALUES
                        (:school_id, :employment_rate, :graduate_rate, :data_source, :data_year)
                    ON DUPLICATE KEY UPDATE
                        employment_rate = VALUES(employment_rate),
                        graduate_rate   = VALUES(graduate_rate),
                        data_source     = VALUES(data_source),
                        data_year       = VALUES(data_year),
                        updated_at      = NOW()
                """),
                rec.model_dump(),
            )
            ingested += 1
        except Exception:
            rejected += 1
    return ingested, rejected


async def _ingest_salary(records, db: AsyncSession) -> tuple[int, int]:
    ingested = rejected = 0
    for rec in records:
        try:
            d = rec.model_dump()
            d["major_name"] = d["major_name"] or "__default__"
            await db.execute(
                text("""
                    INSERT INTO school_salary
                        (school_id, major_name, salary_start_min, salary_start_max,
                         salary_3yr_min, salary_3yr_max, data_source, data_year)
                    VALUES
                        (:school_id, :major_name, :salary_start_min, :salary_start_max,
                         :salary_3yr_min, :salary_3yr_max, :data_source, :data_year)
                    ON DUPLICATE KEY UPDATE
                        salary_start_min = VALUES(salary_start_min),
                        salary_start_max = VALUES(salary_start_max),
                        salary_3yr_min   = VALUES(salary_3yr_min),
                        salary_3yr_max   = VALUES(salary_3yr_max),
                        data_source      = VALUES(data_source),
                        data_year        = VALUES(data_year),
                        updated_at       = NOW()
                """),
                d,
            )
            ingested += 1
        except Exception:
            rejected += 1
    return ingested, rejected


async def _ingest_city(records, db: AsyncSession) -> tuple[int, int]:
    ingested = rejected = 0
    for rec in records:
        try:
            await db.execute(
                text("""
                    INSERT INTO city_analysis
                        (city_name, location, advantage, development,
                         main_business, city_level)
                    VALUES
                        (:city_name, :location, :advantage, :development,
                         :main_business, :city_level)
                    ON DUPLICATE KEY UPDATE
                        location     = VALUES(location),
                        advantage    = VALUES(advantage),
                        development  = VALUES(development),
                        main_business= VALUES(main_business),
                        city_level   = VALUES(city_level),
                        updated_at   = NOW()
                """),
                rec.model_dump(),
            )
            ingested += 1
        except Exception:
            rejected += 1
    return ingested, rejected


# ─── Endpoint ────────────────────────────────────────────────────────────────

@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    payload: IngestRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    _verify_internal_token(request)
    source_ip = request.headers.get("X-Real-IP", request.client.host if request.client else "unknown")

    data_type = payload.data_type
    if data_type == "admission":
        ingested, rejected = await _ingest_admission(payload.records, source_ip, db)
    elif data_type == "major":
        ingested, rejected = await _ingest_major(payload.records, db)
    elif data_type == "tuition":
        ingested, rejected = await _ingest_tuition(payload.records, db)
    elif data_type == "employment":
        ingested, rejected = await _ingest_employment(payload.records, db)
    elif data_type == "salary":
        ingested, rejected = await _ingest_salary(payload.records, db)
    else:  # city
        ingested, rejected = await _ingest_city(payload.records, db)

    await db.commit()
    return IngestResponse(data_type=data_type, ingested=ingested, rejected=rejected)
