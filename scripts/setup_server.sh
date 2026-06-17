#!/bin/bash
# ============================================================
# 新服务器初始化脚本（Ubuntu 22.04 裸机）
# 在新服务器上执行：bash setup_server.sh
# ============================================================
set -e

DB_NAME="gaokao_ai"
DB_USER="gaokao_user"
DB_PASS="GKai@2026#Prod"    # 可改，记得同步到 .env
APP_DIR="/root/gaokao-ai"
PY_VER="3.12"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅ $1${NC}"; }
info() { echo -e "${YELLOW}▶  $1${NC}"; }
err()  { echo -e "${RED}❌ $1${NC}"; exit 1; }

# ── 1. 系统更新 ────────────────────────────────────────────
info "1/9 系统更新..."
apt-get update -qq && apt-get upgrade -y -qq
ok "系统更新完成"

# ── 2. 安装基础软件包 ─────────────────────────────────────
info "2/9 安装依赖包..."
apt-get install -y -qq \
    git curl wget unzip ufw \
    python${PY_VER} python${PY_VER}-venv python${PY_VER}-dev python3-pip \
    nginx \
    redis-server \
    mysql-server \
    libmysqlclient-dev \
    build-essential
ok "依赖包安装完成"

# ── 3. 创建系统用户 ───────────────────────────────────────
info "3/9 创建 gaokao 用户..."
id gaokao &>/dev/null || useradd -m -s /bin/bash gaokao
ok "gaokao 用户已就绪"

# ── 4. MySQL 配置 ─────────────────────────────────────────
info "4/9 配置 MySQL..."
systemctl start mysql
systemctl enable mysql --quiet

mysql -u root <<SQL
CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
SQL
ok "MySQL 数据库 ${DB_NAME} + 用户 ${DB_USER} 创建完成"

# ── 5. Redis 配置 ─────────────────────────────────────────
info "5/9 配置 Redis..."
systemctl start redis-server
systemctl enable redis-server --quiet

redis-cli CONFIG SET maxmemory 512mb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
redis-cli CONFIG SET save "3600 1"
redis-cli CONFIG REWRITE
ok "Redis 配置完成（512MB / allkeys-lru）"

# ── 6. 项目目录 & Python 虚拟环境 ─────────────────────────
info "6/9 创建项目目录..."
mkdir -p ${APP_DIR}
cd ${APP_DIR}

if [ ! -d ".venv" ]; then
    python${PY_VER} -m venv .venv
    ok "virtualenv 创建完成"
fi

# 如果代码已经 scp 过来，直接 install；否则提示
if [ -f "requirements.txt" ]; then
    .venv/bin/pip install -q --upgrade pip
    .venv/bin/pip install -q -r requirements.txt
    ok "Python 依赖安装完成"
else
    echo "  ⚠️  requirements.txt 不存在，稍后 scp 代码后再手动运行："
    echo "       cd ${APP_DIR} && .venv/bin/pip install -r requirements.txt"
fi

# ── 7. systemd 服务 ───────────────────────────────────────
info "7/9 配置 systemd 服务..."
cat > /etc/systemd/system/gaokao-api.service <<EOF
[Unit]
Description=GaokaoAI FastAPI Service
After=network.target mysql.service redis-server.service

[Service]
Type=simple
User=root
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable gaokao-api --quiet
ok "systemd 服务注册完成（gaokao-api）"

# ── 8. Nginx 配置 ─────────────────────────────────────────
info "8/9 配置 Nginx..."

# 删除默认站点
rm -f /etc/nginx/sites-enabled/default

cat > /etc/nginx/sites-available/gaokao <<'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    server_name _;

    client_max_body_size 10m;
    proxy_read_timeout 60s;

    # 静态前端
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # 爬虫内网接口（仅允许爬虫服务器 IP）
    location /internal/ {
        allow 199.193.126.80;
        deny all;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

ln -sf /etc/nginx/sites-available/gaokao /etc/nginx/sites-enabled/gaokao
nginx -t && systemctl restart nginx && systemctl enable nginx --quiet
ok "Nginx 配置完成"

# ── 9. 防火墙 ─────────────────────────────────────────────
info "9/9 配置防火墙..."
ufw --force enable
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ok "防火墙配置完成（22/80/443）"

# ── 完成 ──────────────────────────────────────────────────
echo ""
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo -e "${GREEN}  服务器初始化完成！${NC}"
echo -e "${GREEN}══════════════════════════════════════════${NC}"
echo ""
echo "下一步："
echo "  1. scp 代码到服务器（在本地 Windows 运行）："
echo "       scp -r /d/dev/NewGKAi/* root@172.16.190.16:${APP_DIR}/"
echo "  2. 上传数据库备份并导入（见 migrate_db.sh）"
echo "  3. 创建 .env 文件（参考 .env.example）"
echo "  4. 启动服务：systemctl start gaokao-api"
echo "  5. 验证：curl http://127.0.0.1:8000/health"
