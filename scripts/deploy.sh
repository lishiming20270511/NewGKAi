#!/bin/bash
# 生产部署脚本（在 114.55.65.71 上以 root 执行）
# 用法: bash scripts/deploy.sh
set -e

DEPLOY_DIR="/root/gaokao-ai"
REPO="https://github.com/lishiming20270511/NewGKAi.git"
SERVICE="gaokao-api"
DB_NAME="gaokao_ai"

echo "=== [1/6] 备份当前 .env ==="
if [ -f "$DEPLOY_DIR/.env" ]; then
    cp "$DEPLOY_DIR/.env" "$DEPLOY_DIR/.env.bak_$(date +%Y%m%d_%H%M%S)"
    echo "已备份 .env"
fi

echo "=== [2/6] 拉取最新代码 ==="
if [ -d "$DEPLOY_DIR/.git" ]; then
    cd "$DEPLOY_DIR"
    git -c http.proxy="" pull origin main
else
    # 首次部署：将旧目录重命名，克隆新项目
    if [ -d "$DEPLOY_DIR" ]; then
        mv "$DEPLOY_DIR" "${DEPLOY_DIR}_legacy_$(date +%Y%m%d)"
    fi
    git -c http.proxy="" clone "$REPO" "$DEPLOY_DIR"
    cd "$DEPLOY_DIR"
fi

echo "=== [3/6] 恢复 .env ==="
BAK=$(ls -t "${DEPLOY_DIR}.env.bak_"* 2>/dev/null | head -1 || true)
if [ -n "$BAK" ] && [ ! -f "$DEPLOY_DIR/.env" ]; then
    cp "$BAK" "$DEPLOY_DIR/.env"
    echo "从备份恢复 .env"
elif [ ! -f "$DEPLOY_DIR/.env" ]; then
    echo "警告：.env 文件不存在，请手动创建后重新运行！"
    echo "参考模板：cat .env.example"
    exit 1
fi

echo "=== [4/6] 安装/更新 Python 依赖 ==="
cd "$DEPLOY_DIR"
if [ ! -d ".venv" ]; then
    python3.12 -m venv .venv
fi
.venv/bin/pip install -q -r requirements.txt

echo "=== [5/6] 执行数据库迁移 ==="
# 读取数据库密码（从 .env）
DB_PASS=$(grep DB_PASSWORD .env | cut -d= -f2 | tr -d ' ')
DB_USER=$(grep DB_USER .env | cut -d= -f2 | tr -d ' ' || echo "gaokao_user")
DB_HOST=$(grep DB_HOST .env | cut -d= -f2 | tr -d ' ' || echo "127.0.0.1")

mysql -h"$DB_HOST" -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" \
    < scripts/migrate_qa_history.sql && echo "qa_history 表 OK" || echo "qa_history 迁移跳过（可能已存在）"

echo "=== [6/6] 重启服务 ==="
systemctl restart "$SERVICE"
sleep 2
systemctl is-active "$SERVICE" && echo "服务运行正常 ✅" || (echo "服务启动失败，查看日志：journalctl -u $SERVICE -n 50" && exit 1)

echo ""
echo "=== 部署完成，验证健康检查 ==="
curl -s http://127.0.0.1:8000/health | python3 -m json.tool
