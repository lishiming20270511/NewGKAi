#!/bin/bash
# ============================================================
# 在新服务器上创建 .env 文件
# 用法（在新服务器上执行）：bash create_env.sh
# ============================================================
APP_DIR="/root/gaokao-ai"

# 从旧服务器 .env 读取敏感配置（如果你有旧 .env 的备份，直接 scp 过来更快）
# 这里提供交互式创建方式

echo "=== 创建 .env 文件 ==="
echo "按 Enter 使用括号内的默认值"
echo ""

read -p "JWT_SECRET (留空自动生成): " JWT_SECRET
[ -z "$JWT_SECRET" ] && JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")

read -p "INTERNAL_JWT_SECRET (留空自动生成): " INT_JWT
[ -z "$INT_JWT" ] && INT_JWT=$(python3 -c "import secrets; print(secrets.token_hex(32))")

read -p "ADMIN_PASSWORD: " ADMIN_PASS
read -p "LLM_API_KEY (DeepSeek): " LLM_KEY
read -p "LLM_BASE_URL [https://api.deepseek.com/v1]: " LLM_URL
[ -z "$LLM_URL" ] && LLM_URL="https://api.deepseek.com/v1"

cat > "${APP_DIR}/.env" <<EOF
# Database
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=gaokao_ai
DB_USER=gaokao_user
DB_PASSWORD=<YOUR_DB_PASSWORD>
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30

# Redis
REDIS_URL=redis://127.0.0.1:6379/0

# JWT
JWT_SECRET=${JWT_SECRET}
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24
INTERNAL_JWT_SECRET=${INT_JWT}

# Admin
ADMIN_USERNAME=admin
ADMIN_PASSWORD=${ADMIN_PASS}

# LLM (pateway.ai proxy, Anthropic-native format)
LLM_PROVIDER=anthropic
LLM_API_KEY=${LLM_KEY}
LLM_BASE_URL=${LLM_URL}
LLM_MODEL=claude-sonnet-4-6
EOF

chmod 600 "${APP_DIR}/.env"
echo ""
echo "✅ .env 已创建：${APP_DIR}/.env"
echo "   请确保 DB_PASSWORD 与 setup_server.sh 中一致"
