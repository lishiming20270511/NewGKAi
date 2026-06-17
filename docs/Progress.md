# AI高考志愿规划师 — 开发进度记录

| 文档信息 | 内容 |
|---------|------|
| 项目名称 | AI高考志愿规划师 · 直播辅助工具 |
| 上级文档 | [Tasks.md](./Tasks.md) |
| 更新日期 | 2026-06-17 (42/42任务完成：Phase 7 v4.0数据层升级收官) |

---

## Phase 1：基础设施 进度

| 任务 | 状态 | 完成日期 | 备注 |
|------|------|----------|------|
| **T1.1** 生产环境准备与Redis安装 | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T1.2** 数据库Schema创建与索引优化 | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T1.3** 爬虫数据网关 | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T1.4** 项目脚手架与FastAPI基础路由 | ✅ 完成 | 2026-06-17 | 见下方详情 |

---

## Phase 2：核心后端 进度

| 任务 | 状态 | 完成日期 | 备注 |
|------|------|----------|------|
| **T2.1** 认证系统（JWT + Redis黑名单） | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T2.2** 扣费系统（幂等+原子事务） | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T2.3** 学校搜索API | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T2.4** 推荐引擎核心（位次估算+四层候选池） | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T2.5** 推荐引擎概率计算（rankProb+weightedProb） | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T2.6** 推荐引擎16维度数据填充 | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T2.7** 直播答疑API + LLM调用 | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T2.8** 报告记录 + 防倒卖检测 | ✅ 完成 | 2026-06-17 | 见下方详情 |

---

## Phase 3：前端页面 进度

| 任务 | 状态 | 完成日期 | 备注 |
|------|------|----------|------|
| **T3.1** 前端框架搭建（index.html + 路由 + 手机模拟框） | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T3.2** 登录页 + 考生信息页 | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T3.3** 意向偏好页 | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T3.4** 分析中过渡页 + 付款墙 | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T3.5** 完整报告页 + 特别关注区 | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T3.6** PDF生成 + 下一位学生 | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T3.7** 报告样板 + 直播答疑 | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T3.8** 直播模式 | ✅ 完成 | 2026-06-17 | 见下方详情 |

---

## Phase 4：管理与交易 进度

| 任务 | 状态 | 完成日期 | 备注 |
|------|------|----------|------|
| **T4.1** 管理后台框架 + 管理员认证 | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T4.2** 主播管理CRUD | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T4.3** 充值系统 | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T4.4** 订单查看 | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T4.5** 系统配置管理 | ✅ 完成 | 2026-06-17 | ⚠️ Bug修复：列名 key_/value_ |

---

## Phase 5：集成测试与部署 进度

| 任务 | 状态 | 完成日期 | 备注 |
|------|------|----------|------|
| **T5.1** 前后端联调（主流程） | ✅ 完成 | 2026-06-17 | 冒烟测试14/14通过，见详情 |
| **T5.2** 边界场景测试 | ✅ 完成 | 2026-06-17 | 9场景7/9通过，2个为行为差异（TC-07已修复截断） |
| **T5.3** 性能测试 | ✅ 完成 | 2026-06-17 | 首次105ms/缓存5ms/10并发P50=57ms，全部超标 |
| **T5.4** 爬虫网关集成测试 | ✅ 完成 | 2026-06-17 | 4场景全通过，数据流验证完整 |
| **T5.5** Nginx配置 + SSL验证 | ✅ 完成 | 2026-06-17 | 14项全通过，HTTPS自签名，待DNS切换后换Let's Encrypt |
| **T5.6** 生产部署 + 冒烟测试 | ✅ 完成 | 2026-06-17 | 最终验收12/12 PASS，TC-07分数截断修复已上线 |

---

## Phase 6：上线加固 进度

| 任务 | 状态 | 完成日期 | 备注 |
|------|------|----------|------|
| **T6.1** 监控告警部署 | ✅ 完成 | 2026-06-17 | gaokao_monitor.sh + crontab */5，飞书Webhook告警已接入 |
| **T6.2** 数据备份方案验证 | ✅ 完成 | 2026-06-17 | gaokao_backup.sh + crontab 每日3am，首次备份12MB已验证 |
| **T6.3** Redis持久化 + 降级验证 | ✅ 完成 | 2026-06-17 | 停Redis扣费仍成功，5s内自动重连恢复 |
| **T6.4** 文档更新 + 部署手册 | ✅ 完成 | 2026-06-17 | ops_manual.md + streamer_guide.md + admin_guide.md |

---

## Phase 7：v4.0 数据层升级 进度

| 任务 | 状态 | 完成日期 | 备注 |
|------|------|----------|------|
| **T7.1** v4.0数据层SQL迁移文件 | ✅ 完成 | 2026-06-17 | scripts/migrate_v4_data_layer.sql，含7张新表+6张爬虫任务表DDL |
| **T7.2** admin_accounts表 + 管理员认证升级 | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T7.3** 爬虫网关扩展到6种数据类型 | ✅ 完成 | 2026-06-17 | crawler.py支持admission/major/tuition/employment/salary/city |
| **T7.4** 重写aggregate_16_dimensions() | ✅ 完成 | 2026-06-17 | 查询school_majors/major_similarity/school_tuition/school_employment/school_salary/city_analysis |
| **T7.5** major_similarity种子脚本 | ✅ 完成 | 2026-06-17 | scripts/seed_major_similarity.py，26大类×3-5相似专业，约110条 |
| **T7.6** 热门院校学费种子脚本 | ✅ 完成 | 2026-06-17 | scripts/seed_hot_school_tuition.py，100+所985/211院校，~110条记录 |
| **T7.7** 数据缺口检测6类爬虫任务 | ✅ 完成 | 2026-06-17 | detect_data_gaps()扩展，自动触发6类爬虫任务 |

---

## Bug修复记录

### BugFix-1：admin.py config API 列名错误（2026-06-17）

- **问题**：`GET /admin/config` 和 `PUT /admin/config` 使用了 `config_key`/`config_value` 列名，但实际 `system_config` 表列名为 `key_`/`value_`（T1.2 创建时的实际建表列名）
- **修复**：`api/routers/admin.py` 中将所有 `config_key`→`key_`，`config_value`→`value_`
- **影响范围**：仅 `GET/PUT /admin/config` 两个端点

### BugFix-2：recommendation.py _create_crawl_tasks 列名错误（2026-06-17）

- **问题**：`_create_crawl_tasks()` 向 `school_admission_crawl_tasks` 插入时使用 `school_id`/`province` 列，但实际表结构为 `school_name`/`school_code`/`year`/`status`
- **修复**：增加从 `schools` 表按 `school_id` 查询 `name` 的步骤，改用 `school_name`/`school_code` 列插入
- **影响范围**：仅数据缺口检测的爬虫任务写入，不影响推荐结果（已有 try/except 兜底）

### BugFix-3：recommendation.py estimate_rank 列名错误（2026-06-17）

- **问题**：`estimate_rank()` 查询 `yifenyidang` 时用 `subject_group` 列，实际列名为 `category`，导致 500 错误
- **修复**：改为 `category`
- **影响范围**：推荐引擎入口，修复前每次推荐请求均报 500

### BugFix-4：yifenyidang 类别 fallback 缺失（2026-06-17）

- **问题**：数据库 `yifenyidang` 表所有记录均为 `category='综合'`，传入 `理科`/`文科` 查不到任何结果，推荐返回 0 所学校
- **修复**：`estimate_rank()` 加 fallback 链：传入值 → 映射值（理科→物理/文科→历史）→ 综合
- **影响范围**：所有非综合省份的考生推荐

### BugFix-5：employment_data 列名不匹配（2026-06-17）

- **问题**：`aggregate_16_dimensions()` 查询 `employment_data` 时用 `major`/`avg_salary_start`/`avg_salary_3yr`/`core_positions`/`other_positions`/`trend_5yr`，实际表列为 `major_name`/`avg_salary`/`top_industries`
- **修复**：按实际列名重写查询和字段映射，`avg_salary_3yr` 估算为 `avg_salary * 1.3`，`top_industries` JSON 拆分为岗位列表
- **影响范围**：16维度中就业数据维度（无数据时降级为按院校层次估算，主流程不中断）

### BugFix-6：deduct() SQLAlchemy 事务冲突（2026-06-17）

- **问题**：`deduct()` 用 `async with db.begin()` 显式开启事务，但 `get_current_streamer` 依赖注入已通过 autobegin 执行了一条 SELECT，导致 `InvalidRequestError: A transaction is already begun`
- **修复**：移除 `async with db.begin()`，改为直接执行 SQL（autobegin 已开启），在成功路径末尾 `await db.commit()`，异常路径 `await db.rollback()`
- **影响范围**：`POST /auth/deduct`，修复前每次扣费请求均报 500

### BugFix-7：logout/token 接口协议错误（2026-06-17）

- **问题**：`POST /auth/logout/token` 期望请求体 `{"token":"..."}` 传入 JWT，但前端（smoke test）只发 `Authorization: Bearer ...` header，导致 422 Unprocessable Entity
- **修复**：改为从 `HTTPBearer` header 读取 token，返回 `{"success": true}`（原返回 204 No Content）
- **影响范围**：注销流程

### BugFix-8：qa.py LLM 调用格式错误（2026-06-17）

- **问题**：`_call_llm()` 用 OpenAI chat completions 格式（`/v1/chat/completions`，`choices[0].message.content`），但 `api.pateway.ai` 对 Claude 模型使用 Anthropic 原生格式，返回 `"protocol_mismatch"`
- **修复**：改为 Anthropic messages 格式（`/v1/messages`，system 字段独立，响应取 `content[0].text`），header 加 `anthropic-version: 2023-06-01`，超时从 10s 改为 30s
- **影响范围**：`POST /api/qa/ask` LLM 调用路径

---

## T1.1 完成详情（2026-06-17）

### 执行内容

**服务器**：`121.41.69.234`（生产服务器）

#### 1. Redis 7.4.2 配置
- `maxmemory-policy` → `allkeys-lru` ✅
- `save` → `3600 1`（每小时至少1次写入）✅
- `maxmemory` → `512MB`（536870912 bytes）✅
- 配置已持久化到 `/etc/redis/redis.conf`（CONFIG REWRITE）✅

**验证结果**：
```
redis-cli PING → PONG
redis-cli CONFIG GET maxmemory-policy → allkeys-lru
redis-cli CONFIG GET save → 3600 1
```

#### 2. gaokao 系统用户
- 用户创建：`uid=1005(gaokao) gid=1005(gaokao)` ✅
- 命令：`useradd -m -s /bin/bash gaokao`

#### 3. MySQL 连接池配置
- 修改 `/root/gaokao-ai/.env`，新增：
  ```
  DB_POOL_SIZE=20
  DB_MAX_OVERFLOW=30
  REDIS_URL=redis://127.0.0.1:6379/0
  INTERNAL_JWT_SECRET=<generated>
  ```
- 原文件已备份（`.env.bak_YYYYMMDD_HHMMSS`）✅

#### 4. Nginx `/internal/*` 路由
- 新增到 `/etc/nginx/sites-enabled/gaokao`（HTTPS server block）：
  ```nginx
  location /internal/ {
      allow 199.193.126.80;
      deny all;
      proxy_pass http://127.0.0.1:8000;
      ...
  }
  ```
- 同时修复了预存在的 `default_server` 端口冲突问题 ✅
- Nginx 配置测试通过并重载 ✅

### 遗留说明
- `/health` 目前返回 `{"status":"ok"}`（老项目格式），T1.4 完成后将改为标准格式 `{"status":"ok","mysql":"ok","redis":"ok"}`

---

## T1.2 完成详情（2026-06-17）

### 执行内容

**服务器**：`121.41.69.234`（生产服务器，数据库 `gaokao_ai`）

#### 1. 旧表归档（保留历史数据）
- `orders`（2条旧数据，B2C端用户支付订单）→ 重命名为 `orders_legacy` ✅
- `report_tasks`（1条旧数据）→ 重命名为 `report_tasks_legacy` ✅
- 先解除外键约束再归档

#### 2. 新 `orders` 表（主播扣费，新架构）
- 字段：`id(PK)`, `streamer_id`, `student_nickname/province/score/subject`, `intended_schools`, `idempotency_key`, `status`, `created_at`
- 索引：`uk_idempotency(streamer_id, idempotency_key)` UNIQUE ✅
- 外键：`streamer_id → streamer_accounts(id)` ✅

#### 3. 新 `report_tasks` 表（防倒卖检测）
- 字段：`id(PK)`, `order_id`, `streamer_id`, `student_hash`, `score_range`, `province`, `school_hash`, `similarity_flag`, `created_at`
- 外键：`order_id → orders(id)` ✅

#### 4. `crawler_staging` 爬虫暂存表（新建）
- 字段与 `admission_history` 对齐 + `source_ip`, `crawled_at`, `status`, `validated_at`, `error_msg`
- 索引：`idx_status(status, created_at)`, `idx_school_prov_year(school_id, province, year)` ✅

#### 5. `crawler_error_log` 错误日志表（新建）
- 字段：`id`, `school_id`, `province`, `year`, `category`, `raw_data`, `error_type`, `error_msg`, `source_ip`, `created_at` ✅

#### 6. 索引确认
- `admission_history`：已有 `idx_school_query(school_id, province, year, category)` 覆盖批量录取查询需求 ✅
- `yifenyidang`：已有 `uk_record(province, year, category, score)` 覆盖位次估算查询需求 ✅

#### 7. `system_config` 预置数据初始化
| key_ | value_ |
|------|--------|
| `score_max` | `{"上海":660,"其他":750}` |
| `tier_thresholds` | `{"boost":30,"solid":60,"safe":85,"low_score":5}` |
| `price_per_query` | `29.9` |
| `low_score_boundary` | `400` |
| `max_candidates` | `105` |

**注**：`system_config` 现有列名为 `key_`/`value_`（非 Architecture.md 设计的 `config_key`/`config_value`），所有代码均按实际列名读取。

### EXPLAIN 验证结果
```
yifenyidang 位次估算:
  type=range, key=uk_record, Extra=Using index condition ✅

admission_history 批量录取:
  type=range, key=uk_admission, Extra=Using index condition ✅
```

---

## T1.3 完成详情（2026-06-17）

### 执行内容

#### `api/routers/crawler.py` — POST /internal/crawler/ingest
- 认证：解析 Bearer token，用 `INTERNAL_JWT_SECRET` 验证（与主播 JWT 完全独立）
- 无效 token → 401 Unauthorized
- 接收最多 500 条 `AdmissionRecord`，Pydantic 前置校验：`min_score ≤ 800`, `min_rank > 0`
- 写入 `crawler_staging`，带 `source_ip`（来自 `X-Real-IP` header）和 `crawled_at`
- 单条写入失败→写 `crawler_error_log`，不影响其他条目，返回 `{ingested: N, rejected: M}`

#### `scripts/check_staging.py` — 校验迁移 cron 脚本
- `BATCH_SIZE=200` 分批处理 `crawler_staging.status='pending'`
- 校验规则：school_id/province/year 非空；min_rank > 0；min_score ∈ [0, 800]；year ∈ [2000, 2030]
- 通过 → `INSERT INTO admission_history … ON DUPLICATE KEY UPDATE`（基于 `uk_admission` 唯一索引去重）
- 失败 → `INSERT INTO crawler_error_log`，status 改为 `rejected`
- crontab：`*/5 * * * *` 运行，日志写 `/tmp/check_staging.log`

**验证结果**：
```bash
# 模拟爬虫写入 2 条
curl -X POST http://127.0.0.1:8000/internal/crawler/ingest \
  -H "Authorization: Bearer <internal_jwt>" \
  -d '{"records": [{"school_id":31,"province":"北京","year":2025,"category":"综合","min_score":686,"min_rank":419}, ...]}'
# → {"ingested": 2, "rejected": 0} ✅

# 无效 token
# → {"detail": "Invalid internal token"} ✅
```

---

## T1.4 完成详情（2026-06-17）

### 执行内容

#### 项目结构（新架构）
```
main.py              FastAPI 应用入口，包含 /health 端点
api/
  __init__.py
  config.py          pydantic-settings 配置（读取 .env）
  database.py        SQLAlchemy 2.0 async 引擎 + get_db()
  redis_client.py    aioredis 客户端单例
  routers/
    auth.py          已实现（T2.1 + T2.2）
    schools.py       已实现（T2.3）
    recommendation.py 已实现（T2.4~T2.6）
    qa.py            已实现（T2.7）
    report.py        已实现（T2.8）
    admin.py         已实现（T4.1~T4.5）
    crawler.py       已实现（T1.3）
  deps.py            已实现（T2.1）— JWT 认证依赖
  services/
    recommendation.py 已实现（T2.4~T2.6，974行）
  models/__init__.py
scripts/
  check_staging.py   已实现（T1.3）
frontend/
  index.html         已实现（T3.1~T3.8，1842行）
```

#### 关键配置
- `api/config.py`：pydantic-settings，自动读取 `.env`，`database_url` 使用 `quote_plus` 处理密码中的特殊字符
- CORS：`allow_origins=["*"]`（开发阶段，T5.5 生产加固时收紧）
- 全局异常处理：捕获未处理异常返回 `{"error":"服务器内部错误"}`

#### systemd 服务更新
- 文件：`/etc/systemd/system/gaokao-api.service`
- 变更：`User=gaokao`（原 root），`ExecStart` 改为 `.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 4`
- `.venv` 用 Python 3.12.3 创建，安装 requirements.txt 所有依赖

**验证结果**：
```bash
curl http://127.0.0.1:8000/health
# → {"status":"ok","mysql":"ok","redis":"ok"} ✅
systemctl status gaokao-api  # → active (running), 4 workers ✅
```

---

## T2.1 完成详情（2026-06-17）

### 执行内容

#### `api/deps.py` — JWT 认证依赖
- `get_current_streamer()`：解析 Bearer Token，Redis 黑名单检查（jti），查库验证账号状态
- `get_current_admin()`：Admin Token 解析，检查 `role=="admin"` 声明
- Redis 不可用时降级（跳过黑名单检查，不拒绝请求）
- **关键修复**：`python-jose` 要求 `sub` 为字符串 → 编码时 `str(streamer_id)`，解码时 `int(payload["sub"])`

#### `api/routers/auth.py` — POST /auth/login, GET /auth/streamer/profile
- `POST /auth/login`：bcrypt 验证，返回 `{token, streamer{id,name,phone(脱敏),balance}}`
- `POST /auth/logout/token`：解码 JWT → 取 jti + exp → Redis `SETEX jwt:blacklist:{jti} TTL 1`（幂等，始终成功）
- `GET /auth/streamer/profile`：返回主播信息（含 purchased_total / used_total）

**验证结果**：
```bash
POST /auth/login → 200 {"token":"eyJ...","streamer":{"id":4,"phone":"138****8000",...}} ✅
GET /auth/streamer/profile (带 Bearer Token) → 200 {"streamer":{...}} ✅
GET /auth/streamer/profile (无 Token) → 401 ✅
```

---

## T2.2 完成详情（2026-06-17）

### 执行内容

#### `api/routers/auth.py` — POST /auth/deduct
- ① Redis NX 分布式锁（`deduct:lock:{sid}`，ex=5s）—— Redis 不可用时降级跳过
- ② 幂等检查：`SELECT id FROM orders WHERE streamer_id=? AND idempotency_key=?`
  - 已存在 → 直接返回 `{success:true, already_processed:true, order_id:...}`
- ③ `SELECT FOR UPDATE` 查询余额
- ④ 余额不足 → 400
- ⑤ `UPDATE balance -= 1, used_total += 1`
- ⑥ `INSERT INTO orders`（order_id 格式：`GK{YYYYMMDD-HHmm}-{4hex}`）
- ⑦ `INSERT INTO report_tasks`（student_hash + score_range + school_hash）

**验证结果**：
```bash
POST /auth/deduct → 200 {success:true, balance:7, order_id:"GKxxxxxxxx-xxxx-xxxx"} ✅
重复 idempotency_key → 200 {already_processed:true} 余额不减 ✅
余额=0 → 400 {detail:"余额不足"} ✅
```

---

## T2.3 完成详情（2026-06-17）

### 执行内容

#### `api/routers/schools.py` — GET /api/schools/search, GET /api/schools/{school_id}
- **搜索**：MySQL FULLTEXT `MATCH(name) AGAINST(:q* IN BOOLEAN MODE)`，无结果自动回退 LIKE `%q%`
- **缓存**：Redis key `school:search:{q}:{limit}` TTL 3600s
- **城市提取**：`_extract_city()` 正则从校名前缀提取城市（覆盖 30+ 主要城市）
- **标签生成**：`_build_tags()` 将 `is_985/is_211/is_double_first` 转为 `["985","211","双一流"]`
- **学校详情**：返回基本信息 + `admission_provinces`（该学校有录取数据的省份列表）

**验证结果**：
```bash
GET /api/schools/search?q=郑州&limit=5
→ [郑州大学(211,双一流), 郑州升达经贸管理学院, ...] ✅

GET /api/schools/100
→ {name:"四川农业大学", tags:["211","双一流"], admission_provinces:[30省...]} ✅
```

---

## T2.4 + T2.5 + T2.6 完成详情（2026-06-17）

### 执行内容

#### `api/services/recommendation.py`（974行）

**位次估算 `estimate_rank()`**：
- 查询 `yifenyidang`，`category` 列，按 2025→2024→2023 年份回退
- 类别 fallback 顺序：传入值 → 映射值（理科→物理/文科→历史）→ 综合（兜底）
- L2 Redis 缓存：`recommend:rank:{province}:{year}:{category}:{score}` TTL 86400s

**四层候选池 `build_candidate_pool()`**：
- 特别关注区：意向学校（不计入15所配额）
- L1：意向城市学校（60+ 城市→省份映射）
- L2：本省学校
- L3：邻省学校（`CITY_NEIGHBOR_PROVINCES` 映射）
- L4：全国兜底（`PROVINCE_EXPAND` 扩展）
- 每层去重，最多 105 候选

**概率计算**：
- `calc_rank_prob()`：取近3年 min_rank 中位数，位次比较法，趋势修正（逐年收紧→下调5%），钳制到 [1,99]
- `calc_weighted_prob()`：6维度加权（录取35% + 专业20% + 就业15% + 城市10% + 性格10% + 经济10%）

**Tier分层 `assign_tier()`**：0=冲刺(30-60%) / 1=稳妥(60-85%) / 2=保底(≥85%)

**16维度 `aggregate_16_dimensions()`**：employment_data 查询 + 学费估算 + 城市分析

**数据缺口检测 `detect_data_gaps()`**：
- 缺数据时向 `school_admission_crawl_tasks` 写爬虫任务（school_name + school_code）

**全局入口 `generate_recommendation()`**：
- L3 全量结果缓存：`recommend:result:{md5}` TTL 1800s

---

## T2.7 完成详情（2026-06-17）

### 执行内容

#### `api/routers/qa.py` — POST /api/qa/ask
- System prompt：张雪峰风格，口语化，犀利接地气，200字以内
- 调用 Claude（`claude-sonnet-4-6` via `api.pateway.ai/v1/messages`，Anthropic 原生格式），超时 30s
- 失败降级：返回 `"AI暂时无法回答，请稍后重试"`
- 问答日志写入 `qa_history`（try/except 兜底，表不存在不影响主流程）

---

## T2.8 完成详情（2026-06-17）

### 执行内容

#### `api/routers/report.py` — POST /api/report/log
- 相似度检测：查询同主播近10条 `report_tasks`
- 同省份 + 同分数段(±5分) + 同意向学校哈希 → `similarity_flag=1`
- 连续3次 → `similarity_flag=2` → `logging.WARNING` 告警

---

## T3.1 ~ T3.8 完成详情（2026-06-17）

### 执行内容

#### `frontend/index.html`（1842行，单文件SPA）

**页面路由（hash-based）**：
- `#login` → `#student`（7字段表单）→ `#pref`（意向偏好）→ `#analyzing`（分析动画）→ `#paywall`（付款墙）→ `#report`（完整报告）
- `#sample`（无需登录，静态样板）
- `#qa`（直播答疑）

**核心功能**：
- 考生信息页：31省选择 + 动态选科组件（3+3 / 3+1+2）+ 分数钳制（上海660/其他750）
- 意向偏好：26专业标签 + 16城市 + 学校搜索（300ms防抖+API）+ 8性格标签
- 分析动画：1.5s加载→AI分析→自动跳转
- 付款墙：概率数据遮蔽 + 余额显示 + 解锁按钮
- 完整报告：特别关注区（意向学校，含0%标注）+ 饼图（Canvas原生绘制）+ 15张学校卡片（16维度折叠展开）
- PDF导出：html2canvas + jsPDF + 5种水印
- 直播模式：requestFullscreen + 1.2x字体 + 悬浮退出按钮
- 管理后台：内嵌 admin panel（主播CRUD/订单/配置），桌面端布局

---

## T4.1 ~ T4.5 完成详情（2026-06-17）

### 执行内容

#### `api/routers/admin.py`（后端）

- `POST /admin/login`：admin JWT（role="admin"，独立于主播 token）
- `GET/POST /admin/streamers`：列表（分页20条）+ 新增主播（bcrypt密码）
- `PUT /admin/streamers/{id}`：编辑手机号/密码/姓名
- `PATCH /admin/streamers/{id}/status`：启用/禁用 toggle
- `POST /admin/streamers/{id}/recharge`：事务 UPDATE balance + INSERT recharge_log
- `GET /admin/orders`：分页 + 日期/主播筛选
- `GET /admin/config`：读 `system_config`（`key_`/`value_` 列），Redis 缓存 300s
- `PUT /admin/config`：更新配置，清除 Redis 缓存

#### 前端（内嵌 `index.html`）
- 管理员登录流程（独立 localStorage 存储）
- 主播列表表格 + 新增/编辑/禁用弹窗
- 充值对话框（次数+金额联动）
- 订单表格 + 筛选器
- 系统配置表单（概率阈值 + 定价 + 分数上限）

---

## T5.1 完成详情（2026-06-17）

### 执行内容

**服务器**：`121.41.69.234`（生产服务器）

#### 冒烟测试结果：✅ 14/14 全通过

```
T1  /health             ✅ status/mysql/redis 均 ok
T2  /auth/login         ✅ 登录成功
T3  /auth/streamer/profile ✅ profile 返回正常
T4  /api/schools/search ✅ 郑州搜索3所
T5  /api/recommendation/generate（首次） ✅ 15所学校，5-5-5分布，70ms
T6  /api/recommendation/generate（缓存） ✅ 缓存命中 10ms
T7  /auth/deduct         ✅ 扣费成功 + 幂等验证
T8  /api/qa/ask          ✅ LLM 实际回答（张雪峰风格）
T9  /auth/logout         ✅ 注销 + Redis 黑名单生效（401）
```

#### 修复的 Bug（本轮发现）

| Bug | 文件 | 原因 | 修复 |
|-----|------|------|------|
| BugFix-3 | `recommendation.py` `estimate_rank()` | 列名写成 `subject_group`，实际为 `category` | 改为 `category` |
| BugFix-4 | `recommendation.py` `estimate_rank()` | 数据库只有 `综合` 类别，传入 `理科`/`文科` 无结果 | 加 fallback：理科→物理→综合 |
| BugFix-5 | `recommendation.py` `aggregate_16_dimensions()` | `employment_data` 列名不匹配（`major`→`major_name`，`avg_salary_start`→`avg_salary` 等） | 按实际列名修复 |
| BugFix-6 | `auth.py` `deduct()` | `async with db.begin()` 与 SQLAlchemy 2.0 autobegin 冲突（get_current_streamer 已起事务） | 移除 begin()，改用手动 commit/rollback |
| BugFix-7 | `auth.py` `logout_with_token()` | 期望 body 传 token，实际前端只发 Bearer header | 改为从 Authorization header 读取 |
| BugFix-8 | `qa.py` `_call_llm()` | pateway.ai 用 Anthropic 原生格式（`/v1/messages`），非 OpenAI format | 改为 Anthropic messages 格式 |

---

---

## T7.2 完成详情（2026-06-17）

### 执行内容

#### `api/deps.py` — get_current_admin() 升级
- 旧版：仅验证 JWT role 声明，无 DB 查询
- 新版：解码 JWT → 查询 `admin_accounts` 表验证账号存在且 `status='active'`
- 返回完整 admin 记录（含 `id`, `username`, `role`）

#### `api/routers/admin.py` — admin_login() 升级
- 旧版：对比 `settings.admin_username` / `settings.admin_password`（明文配置）
- 新版：查询 `admin_accounts` 表 → bcrypt 验证 → UPDATE `last_login_at`
- JWT sub 改为 admin ID（int），不再是用户名字符串

#### 新端点
- `POST /admin/change-password`：验证旧密码 → bcrypt 新密码 → UPDATE
- `POST /admin/streamers/{id}/reset-password`：生成随机8位密码 → bcrypt → UPDATE → 返回明文密码供管理员告知主播

#### 辅助脚本
- `scripts/seed_admin.py`：初始化超级管理员账号（首次部署时执行）

---

## T7.3 完成详情（2026-06-17）

### 执行内容

#### `api/routers/crawler.py` — v4.0 6种数据类型
- 新增 `data_type` 鉴别字段（discriminated union），支持 `admission/major/tuition/employment/salary/city`
- `admission`：写入 `crawler_staging`（原有逻辑）
- `major`：UPSERT `school_majors`（ON DUPLICATE KEY UPDATE by `uk_school_major`）
- `tuition`：UPSERT `school_tuition`（ON DUPLICATE KEY UPDATE by `uk_school_major`）
- `employment`：UPSERT `school_employment`（ON DUPLICATE KEY UPDATE by `uk_school`）
- `salary`：UPSERT `school_salary`（ON DUPLICATE KEY UPDATE by `uk_school_major`；NULL major_name → `__default__`）
- `city`：UPSERT `city_analysis`（ON DUPLICATE KEY UPDATE by `city_name`）

---

## T7.4 完成详情（2026-06-17）

### 执行内容

#### `api/services/recommendation.py` — aggregate_16_dimensions() v4.0

| 维度 | 旧实现 | 新实现 |
|------|--------|--------|
| 维度7 推荐专业 | 直接取 `req.major_preference[0]` | 查 `school_majors` 精确匹配 → `major_similarity` 相似匹配 → fallback |
| 维度8 学费 | 按院校类型硬编码估算 | 查 `school_tuition`（精确/默认）→ fallback估算 |
| 维度11 就业率 | 查旧 `employment_data` 表（列名不匹配）| 查 `school_employment`，标注来源+年份 |
| 维度12 薪资 | 按院校层次估算 | 查 `school_salary`（精确/默认）→ fallback估算 |
| 维度15 城市分析 | Python 硬编码字典12城市 | 查 `city_analysis` 5维度结构化数据 → fallback |

#### `detect_data_gaps()` v4.0
- 扩展为6类缺口检测
- 录取缺口：创建 `school_admission_crawl_tasks`
- 专业缺口（`school_majors` 无记录）：创建 `school_major_crawl_tasks`
- 学费缺口：创建 `school_tuition_crawl_tasks`
- 就业缺口：创建 `school_employment_crawl_tasks`
- 薪资缺口：创建 `school_salary_crawl_tasks`
- 城市数据无需爬虫任务（爬取触发方式不同）

---

## T7.5 完成详情（2026-06-17）

### 执行内容

**`scripts/seed_major_similarity.py`**（约110条映射）

覆盖专业大类：
- 计算机/信息类（计算机→软件/人工智能/数据科学/信息安全）
- 电子/通信类（电子信息→通信/电子科学/微电子）
- 土木/建筑类
- 机械/制造类（机械→自动化/电气工程）
- 化工/材料类
- 经济/金融类（经济→金融/国贸；金融→金融工程）
- 管理类（工商管理→营销/人力/财务；会计→财管/审计）
- 法律/医学/师范/外语/农林/艺术类

---

## T7.6 完成详情（2026-06-17）

### 执行内容

**`scripts/seed_hot_school_tuition.py`**（约110条记录）

覆盖院校：39所985院校（含医学专业差异化）+ 约60所211院校  
学费范围：3800元/年（西部省属院校）~ 8000元/年（医学5年制）  
数据来源：各院校2024年官网公告  
差异化处理：部分院校医学/建筑学/软件工程单独记录（与通用学费不同）

---

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-06-17 | 初始创建，记录 T1.1 完成 |
| v1.1 | 2026-06-17 | 记录 T1.2 完成：DDL迁移、crawler_staging/error_log创建、system_config初始化 |
| v1.2 | 2026-06-17 | 记录 T1.3 完成：爬虫网关 /internal/crawler/ingest + check_staging.py cron脚本 |
| v1.3 | 2026-06-17 | 记录 T1.4 完成：FastAPI脚手架、config/database/redis模块、/health端点、systemd服务迁移 |
| v1.4 | 2026-06-17 | 记录 T2.1 完成：JWT认证、bcrypt登录、Redis黑名单注销、主播profile接口 |
| v1.5 | 2026-06-17 | 记录 T2.3 完成：学校搜索（FULLTEXT+LIKE回退+Redis缓存）、学校详情 |
| v2.0 | 2026-06-17 | 大更新：补录 T2.2/T2.4~T2.8/T3.1~T3.8/T4.1~T4.5 完成状态；修复 BugFix-1(admin config列名) + BugFix-2(crawl_tasks列名) |
| v2.1 | 2026-06-17 | T5.1完成：冒烟测试14/14全通过；修复 BugFix-3~8（列名/事务/LLM格式） |
| v3.0 | 2026-06-17 | Phase 5+6全部完成：边界测试/性能测试/爬虫测试/Nginx加固/监控/备份/Redis降级/文档；TC-07分数截断修复；**35/35任务全部完成** |
| v4.0 | 2026-06-17 | Phase 7全部完成：v4.0数据层升级；T7.1~T7.7；admin_accounts独立认证；6类爬虫网关；aggregate_16_dimensions()查真实数据；**42/42任务全部完成** |
