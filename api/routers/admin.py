import json
import random
import string
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from jose import jwt
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..deps import get_current_admin
from ..redis_client import get_redis

router = APIRouter(prefix="/admin", tags=["admin"])

_PAGE_SIZE = 20


# ──────────────────────────────────────────────────────────────────────────────
# Admin auth — v4.0: queries admin_accounts table
# ──────────────────────────────────────────────────────────────────────────────

class AdminLoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def admin_login(body: AdminLoginRequest, db: AsyncSession = Depends(get_db)):
    row = await db.execute(
        text("SELECT id, username, password_hash, role, status FROM admin_accounts WHERE username = :u"),
        {"u": body.username},
    )
    admin = row.mappings().first()
    if not admin:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误")
    if admin["status"] == "disabled":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "账号已被禁用")
    if not bcrypt.checkpw(body.password.encode(), admin["password_hash"].encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误")

    await db.execute(
        text("UPDATE admin_accounts SET last_login_at = NOW() WHERE id = :id"),
        {"id": admin["id"]},
    )
    await db.commit()

    exp = datetime.now(timezone.utc) + timedelta(hours=24)
    token = jwt.encode(
        {"sub": str(admin["id"]), "role": "admin", "jti": str(uuid.uuid4()), "exp": exp},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return {"token": token, "username": admin["username"], "role": admin["role"]}


# ──────────────────────────────────────────────────────────────────────────────
# v4.0: 密码管理
# ──────────────────────────────────────────────────────────────────────────────

class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=6, max_length=64)
    new_password: str = Field(..., min_length=6, max_length=64)


@router.post("/change-password")
async def change_admin_password(
    body: ChangePasswordRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        text("SELECT password_hash FROM admin_accounts WHERE id = :id"),
        {"id": admin["id"]},
    )
    record = row.mappings().first()
    if not record:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "账号不存在")
    if not bcrypt.checkpw(body.old_password.encode(), record["password_hash"].encode()):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "旧密码错误")

    new_hash = bcrypt.hashpw(body.new_password.encode(), bcrypt.gensalt(rounds=12)).decode()
    await db.execute(
        text("UPDATE admin_accounts SET password_hash = :h WHERE id = :id"),
        {"h": new_hash, "id": admin["id"]},
    )
    await db.commit()
    return {"success": True, "message": "密码修改成功"}


# ──────────────────────────────────────────────────────────────────────────────
# T4.2 主播管理 CRUD
# ──────────────────────────────────────────────────────────────────────────────

class StreamerCreateRequest(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11)
    password: str = Field(..., min_length=6, max_length=64)
    name: str = Field(..., min_length=1, max_length=64)


class StreamerUpdateRequest(BaseModel):
    phone: Optional[str] = Field(None, min_length=11, max_length=11)
    password: Optional[str] = Field(None, min_length=6, max_length=64)
    name: Optional[str] = Field(None, min_length=1, max_length=64)


@router.get("/streamers")
async def list_streamers(
    page: int = Query(1, ge=1),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * _PAGE_SIZE
    rows = await db.execute(
        text("""
            SELECT id, phone, name, balance, purchased_total, used_total,
                   status, created_at
            FROM streamer_accounts
            ORDER BY created_at DESC
            LIMIT :lim OFFSET :off
        """),
        {"lim": _PAGE_SIZE, "off": offset},
    )
    total_row = await db.execute(text("SELECT COUNT(*) AS cnt FROM streamer_accounts"))
    total = total_row.mappings().first()["cnt"]

    streamers = []
    for r in rows.mappings():
        streamers.append({
            "id": r["id"],
            "phone": r["phone"][:3] + "****" + r["phone"][-4:],
            "name": r["name"],
            "balance": r["balance"],
            "purchased_total": r["purchased_total"],
            "used_total": r["used_total"],
            "status": r["status"],
            "created_at": str(r["created_at"]),
        })
    return {"streamers": streamers, "total": total, "page": page, "page_size": _PAGE_SIZE}


@router.post("/streamers", status_code=status.HTTP_201_CREATED)
async def create_streamer(
    body: StreamerCreateRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        text("SELECT id FROM streamer_accounts WHERE phone = :phone"),
        {"phone": body.phone},
    )
    if existing.mappings().first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "手机号已存在")

    pw_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt(rounds=12)).decode()
    await db.execute(
        text("""
            INSERT INTO streamer_accounts (phone, password_hash, name, balance)
            VALUES (:phone, :pw, :name, 0)
        """),
        {"phone": body.phone, "pw": pw_hash, "name": body.name},
    )
    await db.commit()
    return {"success": True, "message": f"主播 {body.name} 创建成功"}


@router.put("/streamers/{streamer_id}")
async def update_streamer(
    streamer_id: int,
    body: StreamerUpdateRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    updates = []
    params: dict = {"id": streamer_id}
    if body.name is not None:
        updates.append("name = :name")
        params["name"] = body.name
    if body.phone is not None:
        updates.append("phone = :phone")
        params["phone"] = body.phone
    if body.password is not None:
        pw_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt(rounds=12)).decode()
        updates.append("password_hash = :pw")
        params["pw"] = pw_hash
    if not updates:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "无可更新字段")

    await db.execute(
        text(f"UPDATE streamer_accounts SET {', '.join(updates)} WHERE id = :id"),
        params,
    )
    await db.commit()
    return {"success": True}


@router.post("/streamers/{streamer_id}/reset-password")
async def reset_streamer_password(
    streamer_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        text("SELECT id FROM streamer_accounts WHERE id = :id"),
        {"id": streamer_id},
    )
    if not row.mappings().first():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "主播不存在")

    chars = string.ascii_letters + string.digits
    new_password = "".join(random.choices(chars, k=8))
    pw_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt(rounds=12)).decode()
    await db.execute(
        text("UPDATE streamer_accounts SET password_hash = :h WHERE id = :id"),
        {"h": pw_hash, "id": streamer_id},
    )
    await db.commit()
    return {"success": True, "new_password": new_password}


@router.patch("/streamers/{streamer_id}/status")
async def toggle_streamer_status(
    streamer_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        text("SELECT status FROM streamer_accounts WHERE id = :id"),
        {"id": streamer_id},
    )
    streamer = row.mappings().first()
    if not streamer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "主播不存在")

    new_status = "disabled" if streamer["status"] == "active" else "active"
    await db.execute(
        text("UPDATE streamer_accounts SET status = :s WHERE id = :id"),
        {"s": new_status, "id": streamer_id},
    )
    await db.commit()
    return {"success": True, "status": new_status}


# ──────────────────────────────────────────────────────────────────────────────
# T4.3 充值系统
# ──────────────────────────────────────────────────────────────────────────────

class RechargeRequest(BaseModel):
    count: int = Field(..., ge=1, le=10000)
    amount: float = Field(..., ge=0)
    remark: str = Field("", max_length=255)


@router.post("/streamers/{streamer_id}/recharge")
async def recharge_streamer(
    streamer_id: int,
    body: RechargeRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    async with db.begin():
        row = await db.execute(
            text("SELECT id, balance, purchased_total FROM streamer_accounts WHERE id = :id FOR UPDATE"),
            {"id": streamer_id},
        )
        streamer = row.mappings().first()
        if not streamer:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "主播不存在")

        await db.execute(
            text("""
                UPDATE streamer_accounts
                SET balance = balance + :cnt,
                    purchased_total = purchased_total + :cnt
                WHERE id = :id
            """),
            {"cnt": body.count, "id": streamer_id},
        )
        await db.execute(
            text("""
                INSERT INTO streamer_recharge_logs
                    (streamer_id, amount, count, operator, remark)
                VALUES (:sid, :amt, :cnt, :op, :rmk)
            """),
            {
                "sid": streamer_id,
                "amt": body.amount,
                "cnt": body.count,
                "op": admin.get("sub", "admin"),
                "rmk": body.remark,
            },
        )

    new_balance = streamer["balance"] + body.count
    new_purchased = streamer["purchased_total"] + body.count
    return {
        "success": True,
        "streamer": {
            "id": streamer_id,
            "balance": new_balance,
            "purchased_total": new_purchased,
        },
    }


# ──────────────────────────────────────────────────────────────────────────────
# T4.4 订单查看
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/orders")
async def list_orders(
    page: int = Query(1, ge=1),
    streamer_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * _PAGE_SIZE
    filters = []
    params: dict = {"lim": _PAGE_SIZE, "off": offset}

    if streamer_id is not None:
        filters.append("o.streamer_id = :sid")
        params["sid"] = streamer_id
    if date_from:
        filters.append("o.created_at >= :df")
        params["df"] = date_from
    if date_to:
        filters.append("o.created_at <= :dt")
        params["dt"] = date_to

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

    rows = await db.execute(
        text(f"""
            SELECT o.id, o.streamer_id, sa.name AS streamer_name,
                   o.student_nickname, o.student_province, o.student_score,
                   o.student_subject, o.status, o.created_at
            FROM orders o
            JOIN streamer_accounts sa ON sa.id = o.streamer_id
            {where_clause}
            ORDER BY o.created_at DESC
            LIMIT :lim OFFSET :off
        """),
        params,
    )
    count_row = await db.execute(
        text(f"SELECT COUNT(*) AS cnt FROM orders o {where_clause}"),
        {k: v for k, v in params.items() if k not in ("lim", "off")},
    )
    total = count_row.mappings().first()["cnt"]

    orders = [
        {
            "id": r["id"],
            "streamer_id": r["streamer_id"],
            "streamer_name": r["streamer_name"],
            "student_nickname": r["student_nickname"],
            "student_province": r["student_province"],
            "student_score": r["student_score"],
            "student_subject": r["student_subject"],
            "status": r["status"],
            "created_at": str(r["created_at"]),
        }
        for r in rows.mappings()
    ]
    return {"orders": orders, "total": total, "page": page, "page_size": _PAGE_SIZE}


# ──────────────────────────────────────────────────────────────────────────────
# T4.5 系统配置
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/config")
async def get_config(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        r = get_redis()
        cached = await r.get("sys:config")
        if cached:
            return {"config": json.loads(cached)}
    except Exception:
        pass

    rows = await db.execute(
        text("SELECT key_, value_, description FROM system_config ORDER BY key_")
    )
    config = {r["key_"]: {"value": r["value_"], "description": r["description"]} for r in rows.mappings()}
    try:
        r = get_redis()
        await r.setex("sys:config", 300, json.dumps(config, ensure_ascii=False))
    except Exception:
        pass
    return {"config": config}


@router.put("/config")
async def update_config(
    body: dict,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    for key, value in body.items():
        await db.execute(
            text("""
                INSERT INTO system_config (key_, value_)
                VALUES (:k, :v)
                ON DUPLICATE KEY UPDATE value_ = :v
            """),
            {"k": key, "v": json.dumps(value) if not isinstance(value, str) else value},
        )
    await db.commit()

    try:
        r = get_redis()
        await r.delete("sys:config")
    except Exception:
        pass

    return {"success": True, "updated": list(body.keys())}
