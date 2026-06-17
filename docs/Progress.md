# AI高考志愿规划师 — 开发进度记录

| 文档信息 | 内容 |
|---------|------|
| 项目名称 | AI高考志愿规划师 · 直播辅助工具 |
| 上级文档 | [Tasks.md](./Tasks.md) |
| 更新日期 | 2026-06-17 (Bug修复：admin config列名 + crawl_tasks列名) |

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
| **T5.1** 前后端联调（主流程） | ⏳ 待开始 | — | 依赖 Phase 2+3 ✅ |
| **T5.2** 边界场景测试 | ⏳ 待开始 | — | 依赖 T5.1 |
| **T5.3** 性能测试 | ⏳ 待开始 | — | 依赖 T5.1 |
| **T5.4** 爬虫网关集成测试 | ⏳ 待开始 | — | 依赖 T1.3 |
| **T5.5** Nginx配置 + SSL验证 | ⏳ 待开始 | — | 依赖 T5.1 |
| **T5.6** 生产部署 + 冒烟测试 | ⏳ 待开始 | — | 依赖 T5.1~T5.5 |

---

## Phase 6：上线加固 进度

| 任务 | 状态 | 完成日期 | 备注 |
|------|------|----------|------|
| **T6.1** 监控告警部署 | ⏳ 待开始 | — | 依赖 T5.6 |
| **T6.2** 数据备份方案验证 | ⏳ 待开始 | — | 依赖 T5.6 |
| **T6.3** Redis持久化 + 降级验证 | ⏳ 待开始 | — | 依赖 T5.6 |
| **T6.4** 文档更新 + 部署手册 | ⏳ 待开始 | — | 依赖 T5.6 |

---

## Bug修复记录

### BugFix-1：admin.py config API 列名错误（2026-06-17）

- **问题**：`GET /admin/config` 和 `PUT /admin/config` 使用了 `config_key`/`config_value` 列名，但实际 `system_config` 表列名为 `key_`/`value_`（T1.2 创建时的实际建表列名）
- **修复**：`api/routers/admin.py` 中将所有 `config_key`→`key_`，`config_value`→`value_`
- **影响范围**：仅 `GET/PUT /admin/config` 两个端点

### BugFix-2：recommendation.py _create_crawl_tasks 列名错误（2026-06-17）

- **问题**：`_create_crawl_tasks()` 向 `school_admission_crawl_tasks` 插入时使用 `school_id`/`province` 列，但实际表结构为 `school_name`/`school_code`/`year`/`status`（Architecture.md §爬虫任务表描述）
- **修复**：增加从 `schools` 表按 `school_id` 查询 `name` 的步骤，改用 `school_name`/`school_code` 列插入
- **影响范围**：仅数据缺口检测的爬虫任务写入，不影响推荐结果（已有 try/except 兜底）

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
- 查询 `yifenyidang`，`subject_group` 列，按 2025→2024→2023 年份回退
- L2 Redis 缓存：`recommend:rank:{province}:{year}:{category}:{score}` TTL 3600s

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
- 调用 DeepSeek API（`deepseek-chat`），超时 10s
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

## Phase 5-6：待开始

Phase 5 (集成测试) · Phase 6 (上线加固)

详见 [Tasks.md](./Tasks.md)。

下一步：T5.1 前后端联调（在生产服务器上走通完整主流程）。

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
