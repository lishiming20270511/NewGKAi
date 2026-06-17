#!/bin/bash
# T5.1 冒烟测试脚本（在 114.55.65.71 上执行，或本地通过 -H 指定 Host）
# 用法: bash scripts/smoke_test.sh [BASE_URL] [PHONE] [PASSWORD]
#   默认: BASE_URL=http://127.0.0.1:8000, PHONE=13800138000, PASSWORD=test123
set -e

BASE="${1:-http://127.0.0.1:8000}"
PHONE="${2:-13800138000}"
PASS="${3:-test123}"
IDEM_KEY="smoke-$(date +%s)"
PASS_COUNT=0
FAIL_COUNT=0

ok()   { echo "  ✅ $1"; PASS_COUNT=$((PASS_COUNT+1)); }
fail() { echo "  ❌ $1"; FAIL_COUNT=$((FAIL_COUNT+1)); }
sep()  { echo ""; echo "─── $1 ───"; }

# ── helper: extract JSON field ──────────────────────────────────────────────
jget() { echo "$1" | python3 -c "import sys,json; d=json.load(sys.stdin); print($2)" 2>/dev/null; }

sep "T1 /health"
HEALTH=$(curl -sf "$BASE/health")
STATUS=$(jget "$HEALTH" "d['status']")
MYSQL=$(jget  "$HEALTH" "d['mysql']")
REDIS=$(jget  "$HEALTH" "d['redis']")
[ "$STATUS" = "ok" ] && ok "status=ok" || fail "status=$STATUS"
[ "$MYSQL"  = "ok" ] && ok "mysql=ok"  || fail "mysql=$MYSQL"
[ "$REDIS"  = "ok" ] && ok "redis=ok"  || fail "redis=$REDIS"

sep "T2 /auth/login"
LOGIN=$(curl -sf -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"phone\":\"$PHONE\",\"password\":\"$PASS\"}")
TOKEN=$(jget "$LOGIN" "d['token']")
BAL=$(jget   "$LOGIN" "d['streamer']['balance']")
if [ -n "$TOKEN" ] && [ "$TOKEN" != "None" ]; then
    ok "登录成功，balance=$BAL"
else
    fail "登录失败: $LOGIN"
    echo "请确认主播账号存在（phone=$PHONE，password=$PASS）"
    exit 1
fi

HDR="Authorization: Bearer $TOKEN"

sep "T3 /auth/streamer/profile"
PROF=$(curl -sf "$BASE/auth/streamer/profile" -H "$HDR")
NAME=$(jget "$PROF" "d['streamer']['name']")
[ -n "$NAME" ] && ok "profile OK，name=$NAME" || fail "profile 失败: $PROF"

sep "T4 /api/schools/search"
SCH=$(curl -sf "$BASE/api/schools/search?q=%E9%83%91%E5%B7%9E&limit=3" -H "$HDR")
CNT=$(jget "$SCH" "len(d['results'])")
[ "${CNT:-0}" -ge 1 ] && ok "搜索郑州，结果=${CNT}所" || fail "搜索失败: $SCH"

sep "T5 /api/recommendation/generate（首次，无缓存）"
T_START=$(date +%s%3N)
REC=$(curl -sf -X POST "$BASE/api/recommendation/generate" \
  -H "Content-Type: application/json" \
  -H "$HDR" \
  -d '{
    "province":"河南",
    "score":580,
    "subject_category":"理科",
    "city_preference":["郑州","武汉"],
    "intended_schools":[],
    "major_preference":["计算机","电子信息"],
    "personality":["外向","创新"],
    "economic_level":"一般"
  }')
T_END=$(date +%s%3N)
T_MS=$((T_END - T_START))

SCHOOL_CNT=$(jget "$REC" "len(d.get('schools',[]))")
TIER0=$(jget "$REC" "len([s for s in d.get('schools',[]) if s.get('tier')==0])")
TIER1=$(jget "$REC" "len([s for s in d.get('schools',[]) if s.get('tier')==1])")
TIER2=$(jget "$REC" "len([s for s in d.get('schools',[]) if s.get('tier')==2])")

[ "${SCHOOL_CNT:-0}" -ge 1 ] && ok "推荐学校数=${SCHOOL_CNT}" || fail "推荐失败: $(echo $REC | head -c 300)"
echo "  Tier分布：冲刺=${TIER0} 稳妥=${TIER1} 保底=${TIER2}"
[ "$T_MS" -lt 2000 ] && ok "响应时间=${T_MS}ms（目标<2000ms）" || fail "响应时间=${T_MS}ms（超时）"

sep "T6 /api/recommendation/generate（第二次，缓存命中）"
T2_START=$(date +%s%3N)
curl -sf -X POST "$BASE/api/recommendation/generate" \
  -H "Content-Type: application/json" \
  -H "$HDR" \
  -d '{
    "province":"河南",
    "score":580,
    "subject_category":"理科",
    "city_preference":["郑州","武汉"],
    "intended_schools":[],
    "major_preference":["计算机","电子信息"],
    "personality":["外向","创新"],
    "economic_level":"一般"
  }' > /dev/null
T2_END=$(date +%s%3N)
T2_MS=$((T2_END - T2_START))
[ "$T2_MS" -lt 500 ] && ok "缓存命中，响应时间=${T2_MS}ms（目标<500ms）" || echo "  ⚠️  缓存时间=${T2_MS}ms（可能未命中）"

sep "T7 /auth/deduct（扣费）"
if [ "${BAL:-0}" -gt 0 ]; then
    DED=$(curl -sf -X POST "$BASE/auth/deduct" \
      -H "Content-Type: application/json" \
      -H "$HDR" \
      -d "{\"idempotency_key\":\"$IDEM_KEY\",\"student_nickname\":\"测试学生\",\"student_province\":\"河南\",\"student_score\":580,\"student_subject\":\"理科\",\"intended_schools\":[]}")
    NEW_BAL=$(jget "$DED" "d.get('balance')")
    ORDER_ID=$(jget "$DED" "d.get('order_id','')")
    [ -n "$ORDER_ID" ] && ok "扣费成功，order_id=$ORDER_ID，新余额=$NEW_BAL" || fail "扣费失败: $DED"

    # 幂等测试：同 key 再扣一次
    DED2=$(curl -sf -X POST "$BASE/auth/deduct" \
      -H "Content-Type: application/json" \
      -H "$HDR" \
      -d "{\"idempotency_key\":\"$IDEM_KEY\",\"student_nickname\":\"测试学生\",\"student_province\":\"河南\",\"student_score\":580,\"student_subject\":\"理科\",\"intended_schools\":[]}")
    ALREADY=$(jget "$DED2" "d.get('already_processed',False)")
    BAL2=$(jget "$DED2" "d.get('balance')")
    [ "$ALREADY" = "True" ] && ok "幂等验证通过，重复请求余额未变(=$BAL2)" || fail "幂等失败: $DED2"
else
    echo "  ⚠️  余额=0，跳过扣费测试（需先在管理后台充值）"
fi

sep "T8 /api/qa/ask"
QA=$(curl -sf -X POST "$BASE/api/qa/ask" \
  -H "Content-Type: application/json" \
  -H "$HDR" \
  -d '{"question":"计算机专业就业前景怎么样？"}')
ANS=$(jget "$QA" "d.get('answer','')[:30]")
[ -n "$ANS" ] && ok "QA回答：${ANS}..." || fail "QA失败: $QA"

sep "T9 /auth/logout"
LOGOUT=$(curl -sf -X POST "$BASE/auth/logout/token" -H "$HDR")
[ "$(jget "$LOGOUT" "d.get('success',False)")" = "True" ] && ok "注销成功" || echo "  ⚠️  注销响应: $LOGOUT"

# 验证 token 已失效
PROF2=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/auth/streamer/profile" -H "$HDR")
[ "$PROF2" = "401" ] && ok "Token 黑名单生效（401）" || echo "  ⚠️  注销后状态码: $PROF2（Redis黑名单可能未生效）"

echo ""
echo "══════════════════════════════════════"
echo "测试结果：✅ ${PASS_COUNT} 通过  ❌ ${FAIL_COUNT} 失败"
echo "══════════════════════════════════════"
[ "$FAIL_COUNT" -eq 0 ] && exit 0 || exit 1
