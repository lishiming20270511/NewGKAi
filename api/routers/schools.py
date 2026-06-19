import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_streamer
from ..redis_client import get_redis

router = APIRouter(prefix="/api/schools", tags=["schools"])

# City extraction patterns — covers most Chinese university names
_CITY_PATTERNS = [
    r"^(北京|上海|天津|重庆)",
    r"^(哈尔滨|长春|沈阳|大连|石家庄|济南|青岛|郑州|南京|杭州|武汉|成都|西安|广州|深圳"
    r"|南昌|合肥|福州|长沙|昆明|贵阳|南宁|海口|太原|呼和浩特|西宁|银川|乌鲁木齐|拉萨"
    r"|兰州|徐州|苏州|无锡|宁波|温州|厦门|汕头)",
]
_CITY_RE = [re.compile(p) for p in _CITY_PATTERNS]


def _extract_city(name: str, province: str | None) -> str:
    for pat in _CITY_RE:
        m = pat.match(name)
        if m:
            return m.group(0)
    # Fallback: use province capital for well-known provinces
    return province or ""


def _build_tags(row) -> list[str]:
    tags = []
    if row["is_985"]:
        tags.append("985")
    if row["is_211"]:
        tags.append("211")
    if row["is_double_first"]:
        tags.append("双一流")
    if not tags:
        tags.append(row["level"] or "本科")
    return tags


# ─── Search ──────────────────────────────────────────────────────────────────

@router.get("/search")
async def search_schools(
    q: str = Query(..., min_length=1, max_length=50),
    limit: int = Query(8, ge=1, le=20),
    current_streamer: dict = Depends(get_current_streamer),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"school:search:{q[:20]}:{limit}"
    try:
        r = get_redis()
        cached = await r.get(cache_key)
        if cached:
            import json
            return json.loads(cached)
    except Exception:
        pass

    # FULLTEXT MATCH AGAINST for natural language search (≥2 chars), fallback LIKE
    if len(q) >= 2:
        rows = await db.execute(
            text("""
                SELECT school_id, name, province, level, school_type,
                       is_985, is_211, is_double_first
                FROM schools
                WHERE MATCH(name) AGAINST (:q IN BOOLEAN MODE)
                ORDER BY is_985 DESC, is_211 DESC, is_double_first DESC
                LIMIT :limit
            """),
            {"q": f"{q}*", "limit": limit},
        )
    else:
        rows = await db.execute(
            text("""
                SELECT school_id, name, province, level, school_type,
                       is_985, is_211, is_double_first
                FROM schools
                WHERE name LIKE :q
                ORDER BY is_985 DESC, is_211 DESC
                LIMIT :limit
            """),
            {"q": f"%{q}%", "limit": limit},
        )

    results = []
    for row in rows.mappings():
        results.append({
            "school_id": row["school_id"],
            "name": row["name"],
            "province": row["province"],
            "city": _extract_city(row["name"], row["province"]),
            "tags": _build_tags(row),
        })

    # If FULLTEXT returned nothing, fall back to LIKE
    if not results and len(q) >= 2:
        rows2 = await db.execute(
            text("""
                SELECT school_id, name, province, level, school_type,
                       is_985, is_211, is_double_first
                FROM schools
                WHERE name LIKE :q
                ORDER BY is_985 DESC, is_211 DESC
                LIMIT :limit
            """),
            {"q": f"%{q}%", "limit": limit},
        )
        for row in rows2.mappings():
            results.append({
                "school_id": row["school_id"],
                "name": row["name"],
                "province": row["province"],
                "city": _extract_city(row["name"], row["province"]),
                "tags": _build_tags(row),
            })

    response = {"results": results}

    try:
        import json
        await r.setex(cache_key, 3600, json.dumps(response, ensure_ascii=False))
    except Exception:
        pass

    return response


# ─── Public Search (for student self-service page, no JWT) ───────────────────

@router.get("/search-public")
async def search_schools_public(
    q: str = Query(..., min_length=1, max_length=50),
    limit: int = Query(8, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    if len(q) >= 2:
        rows = await db.execute(
            text("""
                SELECT school_id, name, province, level, school_type,
                       is_985, is_211, is_double_first
                FROM schools
                WHERE MATCH(name) AGAINST (:q IN BOOLEAN MODE)
                ORDER BY is_985 DESC, is_211 DESC, is_double_first DESC
                LIMIT :limit
            """),
            {"q": f"{q}*", "limit": limit},
        )
    else:
        rows = await db.execute(
            text("""
                SELECT school_id, name, province, level, school_type,
                       is_985, is_211, is_double_first
                FROM schools
                WHERE name LIKE :q
                ORDER BY is_985 DESC, is_211 DESC
                LIMIT :limit
            """),
            {"q": f"%{q}%", "limit": limit},
        )

    results = []
    for row in rows.mappings():
        results.append({
            "school_id": row["school_id"],
            "name": row["name"],
            "province": row["province"],
            "city": _extract_city(row["name"], row["province"]),
            "tags": _build_tags(row),
        })

    if not results and len(q) >= 2:
        rows2 = await db.execute(
            text("""
                SELECT school_id, name, province, level, school_type,
                       is_985, is_211, is_double_first
                FROM schools
                WHERE name LIKE :q
                ORDER BY is_985 DESC, is_211 DESC
                LIMIT :limit
            """),
            {"q": f"%{q}%", "limit": limit},
        )
        for row in rows2.mappings():
            results.append({
                "school_id": row["school_id"],
                "name": row["name"],
                "province": row["province"],
                "city": _extract_city(row["name"], row["province"]),
                "tags": _build_tags(row),
            })

    return {"results": results}


# ─── Detail ──────────────────────────────────────────────────────────────────

@router.get("/{school_id}")
async def get_school(
    school_id: int,
    current_streamer: dict = Depends(get_current_streamer),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        text("""
            SELECT school_id, name, province, level, school_type,
                   is_985, is_211, is_double_first
            FROM schools WHERE school_id = :id
        """),
        {"id": school_id},
    )
    school = row.mappings().first()
    if not school:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "学校不存在")

    # Provinces that have admission data for this school
    prov_rows = await db.execute(
        text("""
            SELECT DISTINCT province
            FROM admission_history
            WHERE school_id = :id
            ORDER BY province
        """),
        {"id": school_id},
    )
    provinces = [r["province"] for r in prov_rows.mappings()]

    return {
        "school_id": school["school_id"],
        "name": school["name"],
        "province": school["province"],
        "city": _extract_city(school["name"], school["province"]),
        "level": school["level"],
        "school_type": school["school_type"],
        "tags": _build_tags(school),
        "admission_provinces": provinces,
    }
