"""
重置管理员密码

用法:
  python scripts/reset_admin_password.py                  # 重置 admin，生成随机密码
  python scripts/reset_admin_password.py admin 新密码      # 指定用户名和密码
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


async def reset(username: str, password: str) -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        r = await session.execute(
            text("SELECT id, status FROM admin_accounts WHERE username = :u"),
            {"u": username},
        )
        row = r.mappings().first()
        if not row:
            print(f"[错误] 找不到用户 '{username}'")
            print("现有账号：")
            all_rows = await session.execute(text("SELECT username, role, status FROM admin_accounts"))
            for a in all_rows.mappings():
                print(f"  - {a['username']} ({a['role']}, {a['status']})")
            return

        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()
        await session.execute(
            text("""
                UPDATE admin_accounts
                SET password_hash = :h, status = 'active'
                WHERE username = :u
            """),
            {"h": pw_hash, "u": username},
        )
        await session.commit()
        print(f"✅ 密码重置成功")
        print(f"   用户名: {username}")
        print(f"   新密码: {password}")
        print(f"   状态:   已激活 (active)")

    await engine.dispose()


if __name__ == "__main__":
    uname = sys.argv[1] if len(sys.argv) > 1 else "admin"
    pwd = sys.argv[2] if len(sys.argv) > 2 else None
    if not pwd:
        chars = string.ascii_letters + string.digits + "!@#$"
        pwd = "".join(random.choices(chars, k=12))
        print(f"[生成随机密码]: {pwd}")
    asyncio.run(reset(uname, pwd))
