import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..deps import get_current_streamer
from ..redis_client import get_redis

router = APIRouter(prefix="/auth", tags=["auth"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    phone: str
    password: str


class StreamerOut(BaseModel):
    id: int
    name: str
    phone: str
    balance: int


class LoginResponse(BaseModel):
    token: str
    streamer: StreamerOut


class DeductRequest(BaseModel):
    idempotency_key: str = Field(..., min_length=1, max_length=36)
    student_nickname: str = Field("", max_length=64)
    student_province: str = Field("", max_length=32)
    student_score: int = Field(0, ge=0, le=900)
    student_subject: str = Field("", max_length=32)
    intended_schools: Optional[list[str]] = None


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _generate_order_id() -> str:
    now = datetime.now(timezone.utc)
    return f"GK{now.strftime('%Y%m%d-%H%M')}-{uuid.uuid4().hex[:4]}"


def _score_range(score: int) -> str:
    low = (score // 5) * 5
    return f"{low}-{low + 5}"


def _make_token(streamer_id: int) -> tuple[str, str]:
    jti = str(uuid.uuid4())
    exp = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    payload = {"sub": str(streamer_id), "jti": jti, "exp": exp}
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, jti


def _mask_phone(phone: str) -> str:
    return phone[:3] + "****" + phone[-4:] if len(phone) == 11 else phone


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    row = await db.execute(
        text("SELECT id, phone, name, password_hash, balance, status FROM streamer_accounts WHERE phone = :phone"),
        {"phone": body.phone},
    )
    streamer = row.mappings().first()

    if not streamer:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账号或密码错误")

    if not bcrypt.checkpw(body.password.encode(), streamer["password_hash"].encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账号或密码错误")

    if streamer["status"] == "disabled":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账号或密码错误")

    token, _ = _make_token(streamer["id"])
    return LoginResponse(
        token=token,
        streamer=StreamerOut(
            id=streamer["id"],
            name=streamer["name"],
            phone=_mask_phone(streamer["phone"]),
            balance=streamer["balance"],
        ),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
):
    """Blacklist the JWT token. Always returns success (idempotent)."""
    if credentials:
        try:
            payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            jti = payload.get("jti", "")
            exp = payload.get("exp", 0)
            ttl = max(int(exp - datetime.now(timezone.utc).timestamp()), 1)
            r = get_redis()
            await r.setex(f"jwt:blacklist:{jti}", ttl, "1")
        except Exception:
            pass
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/logout/token")
async def logout_with_token(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
):
    """Blacklist the JWT via Bearer token header. Always returns success (idempotent)."""
    from jose import JWTError as _JWTError
    if credentials:
        try:
            payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            jti = payload.get("jti", "")
            exp = payload.get("exp", 0)
            ttl = max(int(exp - datetime.now(timezone.utc).timestamp()), 1)
            r = get_redis()
            await r.setex(f"jwt:blacklist:{jti}", ttl, "1")
        except (_JWTError, Exception):
            pass  # Always succeed (idempotent)
    return {"success": True}


@router.get("/streamer/profile")
async def streamer_profile(current_streamer: dict = Depends(get_current_streamer)):
    return {
        "streamer": {
            "id": current_streamer["id"],
            "name": current_streamer["name"],
            "phone": _mask_phone(current_streamer["phone"]),
            "balance": current_streamer["balance"],
            "purchased_total": current_streamer["purchased_total"],
            "used_total": current_streamer["used_total"],
        }
    }




class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=6, max_length=64)
    new_password: str = Field(..., min_length=6, max_length=64)


@router.post("/change-password")
async def change_streamer_password(
    body: ChangePasswordRequest,
    current_streamer: dict = Depends(get_current_streamer),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        text("SELECT password_hash FROM streamer_accounts WHERE id = :id"),
        {"id": current_streamer["id"]},
    )
    account = row.mappings().first()
    if not account or not bcrypt.checkpw(body.old_password.encode(), account["password_hash"].encode()):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "旧密码错误")

    new_hash = bcrypt.hashpw(body.new_password.encode(), bcrypt.gensalt(rounds=12)).decode()
    await db.execute(
        text("UPDATE streamer_accounts SET password_hash = :h, updated_at = NOW() WHERE id = :id"),
        {"h": new_hash, "id": current_streamer["id"]},
    )
    await db.commit()
    return {"success": True, "message": "密码修改成功"}

@router.post("/deduct")
async def deduct(
    body: DeductRequest,
    current_streamer: dict = Depends(get_current_streamer),
    db: AsyncSession = Depends(get_db),
):
    sid = current_streamer["id"]
    lock_key = f"deduct:lock:{sid}"
    redis_client = None

    # ① Redis distributed lock (best-effort; degrade to DB lock if unavailable)
    try:
        redis_client = get_redis()
        locked = await redis_client.set(lock_key, "1", nx=True, ex=5)
        if locked is None:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "操作过于频繁，请稍后重试")
    except HTTPException:
        raise
    except Exception:
        redis_client = None  # Redis unavailable — DB lock only

    try:
        # ② Idempotency check (autobegin already started by get_current_streamer)
        dup = await db.execute(
            text("SELECT id FROM orders WHERE streamer_id=:sid AND idempotency_key=:key"),
            {"sid": sid, "key": body.idempotency_key},
        )
        existing = dup.mappings().first()
        if existing:
            acc_row = await db.execute(
                text("SELECT balance, used_total FROM streamer_accounts WHERE id=:id"),
                {"id": sid},
            )
            acc = acc_row.mappings().first()
            await db.rollback()
            return {
                "success": True,
                "already_processed": True,
                "order_id": existing["id"],
                "balance": acc["balance"],
                "used_total": acc["used_total"],
            }

        # ③ SELECT FOR UPDATE — row-level lock prevents concurrent deducts
        acc_row = await db.execute(
            text("SELECT balance, used_total FROM streamer_accounts WHERE id=:id FOR UPDATE"),
            {"id": sid},
        )
        account = acc_row.mappings().first()
        if account["balance"] < 1:
            await db.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "剩余次数不足")

        # ④ Atomic deduct
        await db.execute(
            text("UPDATE streamer_accounts SET balance=balance-1, used_total=used_total+1 WHERE id=:id"),
            {"id": sid},
        )

        # ⑤ Create order
        order_id = _generate_order_id()
        intended_json = json.dumps(body.intended_schools or [], ensure_ascii=False)
        await db.execute(
            text("""
                INSERT INTO orders
                    (id, streamer_id, student_nickname, student_province,
                     student_score, student_subject, intended_schools, idempotency_key)
                VALUES
                    (:id, :sid, :nick, :prov, :score, :subj, :intended, :ikey)
            """),
            {
                "id": order_id,
                "sid": sid,
                "nick": body.student_nickname,
                "prov": body.student_province,
                "score": body.student_score,
                "subj": body.student_subject,
                "intended": intended_json,
                "ikey": body.idempotency_key,
            },
        )

        # ⑥ Insert report_tasks (anti-fraud similarity check done in T2.8 service)
        student_hash = hashlib.sha256(
            f"{body.student_nickname}:{body.student_province}:{body.student_score}".encode()
        ).hexdigest()[:64]
        school_hash = hashlib.sha256(
            json.dumps(sorted(body.intended_schools or []), ensure_ascii=False).encode()
        ).hexdigest()[:64]
        await db.execute(
            text("""
                INSERT INTO report_tasks
                    (order_id, streamer_id, student_hash, score_range,
                     province, school_hash, similarity_flag)
                VALUES
                    (:oid, :sid, :shash, :srange, :prov, :schash, 0)
            """),
            {
                "oid": order_id,
                "sid": sid,
                "shash": student_hash,
                "srange": _score_range(body.student_score),
                "prov": body.student_province,
                "schash": school_hash,
            },
        )

        await db.commit()
        return {
            "success": True,
            "balance": account["balance"] - 1,
            "used_total": account["used_total"] + 1,
            "order_id": order_id,
        }

    except IntegrityError:
        await db.rollback()
        # Duplicate idempotency_key race condition — treat as already processed
        acc_row = await db.execute(
            text("SELECT id FROM orders WHERE streamer_id=:sid AND idempotency_key=:key"),
            {"sid": sid, "key": body.idempotency_key},
        )
        existing = acc_row.mappings().first()
        if existing:
            acc2 = await db.execute(
                text("SELECT balance, used_total FROM streamer_accounts WHERE id=:id"),
                {"id": sid},
            )
            acc = acc2.mappings().first()
            return {
                "success": True,
                "already_processed": True,
                "order_id": existing["id"],
                "balance": acc["balance"],
                "used_total": acc["used_total"],
            }
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "扣费失败，请重试")
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise

    finally:
        if redis_client is not None:
            try:
                await redis_client.delete(lock_key)
            except Exception:
                pass
