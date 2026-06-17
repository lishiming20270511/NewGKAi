from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import get_db
from .redis_client import get_redis

_bearer = HTTPBearer(auto_error=True)


async def get_current_streamer(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "未登录或Token已过期")

    streamer_id: int = int(payload.get("sub"))
    jti: str = payload.get("jti", "")

    # Check JWT blacklist in Redis (degrade gracefully if Redis unavailable)
    try:
        r = get_redis()
        if await r.exists(f"jwt:blacklist:{jti}"):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token已注销，请重新登录")
    except HTTPException:
        raise
    except Exception:
        pass  # Redis unavailable — skip blacklist check, log in production

    row = await db.execute(
        text("SELECT id, phone, name, balance, purchased_total, used_total, status FROM streamer_accounts WHERE id = :id"),
        {"id": streamer_id},
    )
    streamer = row.mappings().first()
    if not streamer:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账号不存在")
    if streamer["status"] == "disabled":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "账号已被禁用，请联系管理员")

    return dict(streamer)


_admin_bearer = HTTPBearer(auto_error=True)
ADMIN_JWT_SECRET = settings.jwt_secret  # same secret, different role claim


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(_admin_bearer),
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, ADMIN_JWT_SECRET, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "未登录或Token已过期")

    if payload.get("role") != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "无管理员权限")

    return payload
