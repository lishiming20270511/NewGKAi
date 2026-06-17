"""
初始化超级管理员账号

用法: python scripts/seed_admin.py [username] [password]
默认: username=admin  password 从环境变量 ADMIN_INIT_PASSWORD 读取，
      否则生成随机16位密码并打印

安全: 运行一次后删除或禁用此脚本
"""
import asyncio
import os
import random
import string
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import bcrypt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from api.config import settings


async def seed(username: str, password: str) -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        r = await session.execute(
            text("SELECT id FROM admin_accounts WHERE username = :u"),
            {"u": username},
        )
        if r.mappings().first():
            print(f"admin_accounts: '{username}' already exists — skipping")
        else:
            pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()
            await session.execute(
                text("""
                    INSERT INTO admin_accounts (username, password_hash, role)
                    VALUES (:u, :h, 'super_admin')
                """),
                {"u": username, "h": pw_hash},
            )
            await session.commit()
            print(f"admin_accounts: created super_admin '{username}'")

    await engine.dispose()


if __name__ == "__main__":
    uname = sys.argv[1] if len(sys.argv) > 1 else "admin"
    pwd = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("ADMIN_INIT_PASSWORD")
    if not pwd:
        pwd = "".join(random.choices(string.ascii_letters + string.digits + "!@#$", k=16))
        print(f"Generated password: {pwd}")
    asyncio.run(seed(uname, pwd))
