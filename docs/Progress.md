# AI高考志愿规划师 — 开发进度记录

| 文档信息 | 内容 |
|---------|------|
| 项目名称 | AI高考志愿规划师 · 直播辅助工具 |
| 上级文档 | [Tasks.md](./Tasks.md) |
| 更新日期 | 2026-06-17 (T1.4) |

---

## Phase 1：基础设施 进度

| 任务 | 状态 | 完成日期 | 备注 |
|------|------|----------|------|
| **T1.1** 生产环境准备与Redis安装 | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T1.2** 数据库Schema创建与索引优化 | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T1.3** 爬虫数据网关 | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T1.4** 项目脚手架与FastAPI基础路由 | ✅ 完成 | 2026-06-17 | 见下方详情 |

---

## T1.1 完成详情（2026-06-17）

### 执行内容

**服务器**：`114.55.65.71`（生产服务器）

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

**服务器**：`114.55.65.71`（生产服务器，数据库 `gaokao_ai`）

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

**注**：`system_config` 现有列名为 `key_`/`value_`（非 Architecture.md 设计的 `config_key`/`config_value`），T1.4/T2 代码将按实际列名读取。

### EXPLAIN 验证结果
```
yifenyidang 位次估算:
  type=range, key=uk_record, Extra=Using index condition ✅

admission_history 批量录取:
  type=range, key=uk_admission, Extra=Using index condition ✅
```

---

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
    auth.py          空路由（T2.1 实现）
    schools.py       空路由（T2.3 实现）
    recommendation.py 空路由（T2.4 实现）
    qa.py            空路由（T2.7 实现）
    report.py        空路由（T2.8 实现）
    admin.py         空路由（T4.1 实现）
    crawler.py       已实现（T1.3）
  services/__init__.py
  models/__init__.py
scripts/
  check_staging.py   已实现（T1.3）
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

## Phase 2-6：待开始

Phase 2 (核心后端) · Phase 3 (前端) · Phase 4 (管理与交易) · Phase 5 (集成部署) · Phase 6 (上线加固)

详见 [Tasks.md](./Tasks.md)。

---

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-06-17 | 初始创建，记录 T1.1 完成 |
| v1.1 | 2026-06-17 | 记录 T1.2 完成：DDL迁移、crawler_staging/error_log创建、system_config初始化 |
| v1.2 | 2026-06-17 | 记录 T1.3 完成：爬虫网关 /internal/crawler/ingest + check_staging.py cron脚本 |
| v1.3 | 2026-06-17 | 记录 T1.4 完成：FastAPI脚手架、config/database/redis模块、/health端点、systemd服务迁移 |
