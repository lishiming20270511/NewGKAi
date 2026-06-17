#!/bin/bash
# ============================================================
# 数据库迁移脚本
# 用法：在【旧服务器 114.55.65.71】上执行
#   bash migrate_db.sh <新服务器IP> <新服务器root密码>
#
# 作用：dump 旧库 → scp 到新服务器 → 自动导入
# ============================================================
set -e

NEW_IP="${1:-<NEW_SERVER_IP>}"
NEW_PASS="${2:-<NEW_SERVER_ROOT_PASSWORD>}"
OLD_DB="gaokao_ai"
DUMP_FILE="/tmp/gaokao_ai_$(date +%Y%m%d_%H%M%S).sql.gz"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅ $1${NC}"; }
info() { echo -e "${YELLOW}▶  $1${NC}"; }

# 读取旧服务器 MySQL 密码（从 .env）
OLD_DB_PASS=$(grep -E "^DB_PASSWORD" /root/gaokao-ai/.env 2>/dev/null | cut -d= -f2 | tr -d ' ' || echo "")
OLD_DB_USER=$(grep -E "^DB_USER" /root/gaokao-ai/.env 2>/dev/null | cut -d= -f2 | tr -d ' ' || echo "gaokao_user")

if [ -z "$OLD_DB_PASS" ]; then
    read -s -p "旧服务器 MySQL 密码 (${OLD_DB_USER}): " OLD_DB_PASS
    echo ""
fi

# ── 1. 导出旧数据库 ───────────────────────────────────────
info "1/3 导出旧数据库 ${OLD_DB}（可能需要几分钟）..."
mysqldump -u"${OLD_DB_USER}" -p"${OLD_DB_PASS}" \
    --single-transaction \
    --quick \
    --set-gtid-purged=OFF \
    "${OLD_DB}" | gzip > "${DUMP_FILE}"

DUMP_SIZE=$(du -sh "$DUMP_FILE" | cut -f1)
ok "导出完成：${DUMP_FILE}（${DUMP_SIZE}）"

# ── 2. 传输到新服务器 ─────────────────────────────────────
info "2/3 传输到新服务器 ${NEW_IP}..."
sshpass -p "${NEW_PASS}" scp -o StrictHostKeyChecking=no \
    "${DUMP_FILE}" "root@${NEW_IP}:/tmp/"
ok "传输完成"

# ── 3. 在新服务器上导入 ───────────────────────────────────
info "3/3 在新服务器上导入数据库..."
REMOTE_FILE="/tmp/$(basename $DUMP_FILE)"

sshpass -p "${NEW_PASS}" ssh -o StrictHostKeyChecking=no "root@${NEW_IP}" <<REMOTE
set -e
echo "解压并导入..."
gunzip -c ${REMOTE_FILE} | mysql -u gaokao_user -pGKai@2026#Prod gaokao_ai
echo "验证行数..."
mysql -u gaokao_user -pGKai@2026#Prod gaokao_ai -e "
    SELECT table_name, table_rows
    FROM information_schema.tables
    WHERE table_schema='gaokao_ai'
    ORDER BY table_rows DESC
    LIMIT 10;
"
rm -f ${REMOTE_FILE}
REMOTE

ok "数据库导入完成！"
echo ""
echo "旧服务器备份文件保留在：${DUMP_FILE}"
