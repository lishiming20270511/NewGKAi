"""
直播话术脚本 — PRD v5.4

主播端：只读接口（按分类返回所有启用话术）
管理员：CRUD + 分类管理 + 排序
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_admin, get_current_streamer

router = APIRouter(tags=["broadcast-scripts"])


# ─── 主播只读：获取所有启用话术 ─────────────────────────────────────────────

@router.get("/api/scripts")
async def get_scripts(
    streamer=Depends(get_current_streamer),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(
        text("""
            SELECT id, category, title, content, sort_order
            FROM broadcast_scripts
            WHERE is_active = 1
            ORDER BY category, sort_order, id
        """)
    )
    categories: list[str] = []
    scripts: dict[str, list] = {}
    for r in rows.mappings():
        cat = r["category"]
        if cat not in scripts:
            scripts[cat] = []
            categories.append(cat)
        scripts[cat].append({
            "id": r["id"],
            "title": r["title"],
            "content": r["content"],
            "sort_order": r["sort_order"],
        })
    return {"categories": categories, "scripts": scripts}


# ─── 管理员 CRUD ─────────────────────────────────────────────────────────────

class ScriptCreate(BaseModel):
    category: str = Field(..., min_length=1, max_length=64)
    title: str = Field(..., min_length=1, max_length=128)
    content: str = Field(..., min_length=1, max_length=2000)
    sort_order: int = Field(0, ge=0)


class ScriptUpdate(BaseModel):
    category: Optional[str] = Field(None, min_length=1, max_length=64)
    title: Optional[str] = Field(None, min_length=1, max_length=128)
    content: Optional[str] = Field(None, min_length=1, max_length=2000)
    sort_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[int] = Field(None, ge=0, le=1)


@router.get("/admin/scripts")
async def list_scripts(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(
        text("""
            SELECT id, category, title, content, sort_order, is_active
            FROM broadcast_scripts
            ORDER BY category, sort_order, id
        """)
    )
    categories: list[str] = []
    scripts: dict[str, list] = {}
    for r in rows.mappings():
        cat = r["category"]
        if cat not in scripts:
            scripts[cat] = []
            categories.append(cat)
        scripts[cat].append(dict(r))
    return {"categories": categories, "scripts": scripts}


@router.post("/admin/scripts", status_code=status.HTTP_201_CREATED)
async def create_script(
    body: ScriptCreate,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("""
            INSERT INTO broadcast_scripts (category, title, content, sort_order, is_active)
            VALUES (:category, :title, :content, :sort_order, 1)
        """),
        body.model_dump(),
    )
    await db.commit()
    return {"id": result.lastrowid, "success": True}


@router.put("/admin/scripts/{script_id}")
async def update_script(
    script_id: int,
    body: ScriptUpdate,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        text("SELECT id FROM broadcast_scripts WHERE id = :id"),
        {"id": script_id},
    )
    if not row.mappings().first():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "话术不存在")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return {"success": True}

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = script_id
    await db.execute(
        text(f"UPDATE broadcast_scripts SET {set_clause}, updated_at = NOW() WHERE id = :id"),
        updates,
    )
    await db.commit()
    return {"success": True}


@router.delete("/admin/scripts/{script_id}")
async def delete_script(
    script_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        text("SELECT id FROM broadcast_scripts WHERE id = :id"),
        {"id": script_id},
    )
    if not row.mappings().first():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "话术不存在")

    await db.execute(
        text("DELETE FROM broadcast_scripts WHERE id = :id"),
        {"id": script_id},
    )
    await db.commit()
    return {"success": True}


# ─── 管理员：排序更新 ────────────────────────────────────────────────────────

class SortUpdateRequest(BaseModel):
    sort_order: int = Field(..., ge=0)


@router.put("/admin/scripts/{script_id}/sort")
async def update_script_sort(
    script_id: int,
    body: SortUpdateRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        text("UPDATE broadcast_scripts SET sort_order = :s, updated_at = NOW() WHERE id = :id"),
        {"s": body.sort_order, "id": script_id},
    )
    await db.commit()
    return {"success": True}


# ─── 管理员：分类管理 ────────────────────────────────────────────────────────

@router.get("/admin/script-categories")
async def list_categories(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(
        text("SELECT DISTINCT category FROM broadcast_scripts ORDER BY category")
    )
    return {"categories": [r[0] for r in rows.fetchall()]}


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)


@router.post("/admin/script-categories")
async def create_category(
    body: CategoryCreate,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    # 分类通过插入占位话术来"创建"，实际通过话术记录存在
    # 这里仅返回成功，实际分类在新增话术时自动创建
    return {"success": True, "name": body.name}


@router.delete("/admin/script-categories/{category_name}")
async def delete_category(
    category_name: str,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("DELETE FROM broadcast_scripts WHERE category = :cat"),
        {"cat": category_name},
    )
    await db.commit()
    return {"success": True, "deleted_count": result.rowcount}
