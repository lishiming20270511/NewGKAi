# AI高考志愿规划师 — 开发任务拆分

| 文档信息 | 内容 |
|---------|------|
| 产品名称 | AI高考志愿规划师 · 直播辅助工具 |
| 上级文档 | [PRD.md](./PRD.md) v3.1 · [Architecture.md](./Architecture.md) v1.2 · [ARR.md](./ARR.md) |
| 创建日期 | 2026-06-17 |
| 总预估工时 | **~120h（约15人天）** |

---

## 任务总览

```
Phase 1: 基础设施 (T1.1 ~ T1.4)    ─── 4个任务，12h
Phase 2: 核心后端 (T2.1 ~ T2.8)    ─── 8个任务，28h
Phase 3: 前端页面 (T3.1 ~ T3.8)    ─── 8个任务，32h
Phase 4: 管理与交易 (T4.1 ~ T4.5)   ─── 5个任务，18h
Phase 5: 集成部署 (T5.1 ~ T5.6)    ─── 6个任务，20h
Phase 6: 上线加固 (T6.1 ~ T6.4)    ─── 4个任务，12h
                                    ─────────────────
                                    35个任务，~122h
```

---

## Phase 1：基础设施搭建

### T1.1 · 生产环境准备与Redis安装
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | 无 |
| **负责人** | 后端 / 运维 |

**任务清单**：
- [ ] 在 121.41.69.234 安装 Redis 7.x（`apt install redis-server`）
- [ ] 配置 Redis：`maxmemory-policy allkeys-lru`，`save 3600 1`（RDB每1小时至少1次写入），`maxmemory 512mb`
- [ ] 创建 `gaokao` 系统用户：`useradd -m -s /bin/bash gaokao`
- [ ] 配置 MySQL 连接池：`pool_size=20, max_overflow=30`（修改 `/root/gaokao-ai/.env`）
- [ ] 配置 Nginx 新增 `/internal/*` 路由代理（仅允许 199.193.126.80 来源IP）
- [ ] 验证：`redis-cli PING` → PONG，`systemctl status redis` → active

**验收标准**：
```bash
redis-cli CONFIG GET maxmemory-policy  # → allkeys-lru
redis-cli CONFIG GET save              # → 3600 1
curl -s http://127.0.0.1:8000/health   # → {"status":"ok","mysql":"ok","redis":"ok"}
id gaokao                               # → uid exists
```

---

### T1.2 · 数据库Schema创建与索引优化
| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | T1.1 |
| **负责人** | 后端 |

**任务清单**：
- [ ] 创建 `crawler_staging` 临时表（字段与 `admission_history` 对齐 + `validated_at` / `error_msg`）
- [ ] 创建 `crawler_error_log` 错误日志表
- [ ] 为 `orders` 表加 `idempotency_key VARCHAR(36)` + `UNIQUE INDEX uk_idempotency (streamer_id, idempotency_key)`
- [ ] 确认 `admission_history` 索引：`idx_school_prov_year(school_id, province, year)` 是否存在（如字段为 `school_id`）
- [ ] 确认 `yifenyidang` 索引：`uk_prov_year_sub_score(province, year, category, score)` 
- [ ] 初始化 `system_config` 表预置数据（省份满分/概率阈值/定价）
- [ ] 运行 EXPLAIN 验证关键查询是否走索引：
  ```sql
  EXPLAIN SELECT * FROM yifenyidang 
  WHERE province='河南' AND year=2025 AND category='理科' AND score<=580 
  ORDER BY score DESC LIMIT 1;  -- 预期: Using index
  ```

**验收标准**：
- 所有表 DDL 与 Architecture.md §4 一致
- `crawler_staging` 表存在且结构正确
- `orders` 表新增 `uk_idempotency` 唯一索引
- 关键查询 EXPLAIN 显示走索引

---

### T1.3 · 爬虫数据网关（修复 ARR R2）
| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | T1.2 |
| **负责人** | 后端 |

**任务清单**：
- [ ] 创建 FastAPI Router：`api/routers/crawler.py`
- [ ] 实现 `POST /internal/crawler/ingest`
  - 认证：内部 JWT（与主播 JWT 不同，单一静态 secret）
  - 写入 `crawler_staging` 临时表（每条记录带 `source_ip` / `crawled_at`）
  - 返回 `{ingested: N, rejected: M}`
- [ ] 实现 `crawler_staging` 校验脚本 `scripts/check_staging.py`（crontab 每 5 分钟）：
  - 字段完整性：`school_id` / `province` / `year` NOT NULL
  - 值域合理性：`min_rank > 0`，`min_score BETWEEN 0 AND 750`
  - 去重：`school_id + province + year + category` 唯一
  - 通过 → `INSERT INTO admission_history ... ON DUPLICATE KEY UPDATE`
  - 失败 → `INSERT INTO crawler_error_log`
- [ ] 在 Nginx 配置中限制 `/internal/*` 仅允许爬虫服务器 IP
- [ ] **爬虫端改造**：（需在 199.193.126.80 上执行）
  - 将 `fetch_school_facts.py` 的 `MySQL INSERT` 改为 `POST /internal/crawler/ingest`
  - 增加失败重试（exponential backoff, max 3次）

**验收标准**：
```bash
# 模拟爬虫写入
curl -X POST https://gaokao.lumenaistudio.co/internal/crawler/ingest \
  -H "Authorization: Bearer <internal_jwt>" \
  -d '{"records":[{"school_id":31,"province":"北京","year":2025,"category":"综合","min_score":686,"min_rank":419}]}'
# → {"ingested": 1, "rejected": 0}

# 等待5分钟后验证数据流入
mysql -e "SELECT COUNT(*) FROM admission_history WHERE school_id=31 AND year=2025 AND province='北京'"
# → 1
```

---

### T1.4 · 项目脚手架与FastAPI基础路由
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T1.1 |
| **负责人** | 后端 |

**任务清单**：
- [ ] 创建项目目录结构（按 Architecture.md 附录B 文件清单）
- [ ] 配置 `.env`（DB连接串、JWT_SECRET、INTERNAL_JWT_SECRET、REDIS_URL、LLM_API_KEY）
- [ ] 创建 `api/routers/` 下所有空路由文件：`auth.py`, `schools.py`, `recommendation.py`, `qa.py`, `report.py`, `admin.py`, `crawler.py`
- [ ] 实现 `/health` 深度检查端点（检查 MySQL 连接 + Redis 连接）：
  ```python
  @router.get("/health")
  async def health():
      mysql_ok = await check_mysql()
      redis_ok = await check_redis()
      return {"status": "ok" if (mysql_ok and redis_ok) else "degraded",
              "mysql": "ok" if mysql_ok else "error",
              "redis": "ok" if redis_ok else "error"}
  ```
- [ ] 配置 CORS、全局异常处理中间件
- [ ] 验证：`uvicorn main:app --port 8000` 启动成功，`/health` 返回200

**验收标准**：
- `curl http://127.0.0.1:8000/health` → `{"status":"ok","mysql":"ok","redis":"ok"}`
- 项目目录结构符合 Architecture.md 附录B

---

## Phase 2：核心后端

### T2.1 · 认证系统（登录/注销/JWT/中间件）
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T1.4 |
| **负责人** | 后端 |

**任务清单**：
- [ ] 实现 `POST /auth/login`：手机号+密码 → bcrypt验证 → 签发JWT(24h)
  - 返回 `{token, streamer: {id, name, phone(脱敏), balance}}`
  - 异常：401 密码错误、403 账号禁用
- [ ] 实现 `POST /auth/logout`：JWT jti 加入 Redis 黑名单
  - Redis 不可用时不检查黑名单（降级，日志告警）
- [ ] 实现 `GET /auth/streamer/profile`：返回当前主播信息+剩余次数
- [ ] 实现 JWT 验证中间件 `get_current_streamer()`：
  - 解码 JWT → 检查黑名单(Redis) → 检查账号状态(MySQL) → 返回 streamer 对象
- [ ] 实现 Admin JWT 中间件（管理员专用，与主播 token 不同）

**验收标准**：
```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -d '{"phone":"13800138000","password":"test123"}'
# → 200 {token, streamer: {...}}

curl http://127.0.0.1:8000/auth/streamer/profile \
  -H "Authorization: Bearer <token>"
# → 200 {streamer: {id, name, balance, ...}}
```

---

### T2.2 · 扣费系统（幂等+原子事务，修复 ARR R1）
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T2.1, T1.2（uk_idempotency已建） |
| **负责人** | 后端 |

**任务清单**：
- [ ] 实现 `POST /auth/deduct`（Request: `{idempotency_key}`）：
  ```python
  # ① Redis 分布式锁（可选，不可用时降级为仅DB锁）
  try: await redis.set(f"deduct:lock:{sid}", "1", nx=True, ex=5)
  except: pass
  # ② 幂等检查
  existing = await db.fetch_one("SELECT id FROM orders WHERE streamer_id=? AND idempotency_key=?", ...)
  if existing: return {"success": True, "already_processed": True, "order_id": existing.id}
  # ③ SELECT FOR UPDATE + 扣费
  # ④ INSERT orders + INSERT report_tasks
  ```
- [ ] 返回标准格式：`{success: true, balance: N, used_total: N, order_id: "GK..."}`
- [ ] 异常处理：400（余额不足）、409（已处理，幂等返回）
- [ ] 写入 `orders` 表：订单号生成规则 `GK` + 时间戳 `YYYYMMDD-HHmm` + `-` + 4位随机hex

**验收标准**：
```bash
# 正常扣费
curl -X POST /auth/deduct -H "Authorization: Bearer <token>" \
  -d '{"idempotency_key":"test-uuid-001"}'
# → 200 {success: true, balance: 7, order_id: "GK..."}

# 幂等重试（同一 key）
curl ... -d '{"idempotency_key":"test-uuid-001"}'
# → 200 {success: true, already_processed: true, order_id: "GK..."}  # 余额不减少！
```

---

### T2.3 · 学校搜索API
| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | T1.4 |
| **负责人** | 后端 |

**任务清单**：
- [ ] 实现 `GET /api/schools/search?q=郑州&limit=8`
  - MySQL FULLTEXT 搜索 `schools.name`
  - 返回字段：`school_id, name, province, city, tags(is_985/is_211/is_double_first)`
  - city 为空时用 `getCityFromSchoolName()` 从校名提取
- [ ] 实现 `GET /api/schools/{school_id}`
  - 返回完整学校信息 + 该校有录取数据的省份列表
- [ ] 前端 `school_data.js` 如不使用则移除（搜索统一走后端API）

**验收标准**：
```bash
curl "http://127.0.0.1:8000/api/schools/search?q=郑州&limit=5"
# → {results: [{school_id:123, name:"郑州大学", city:"郑州", ...}, ...]}
```

---

### T2.4 · 推荐引擎核心（位次估算 + 四层填充）
| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | T2.3 |
| **负责人** | 后端 ★ 核心任务 |

**任务清单**：
- [ ] 实现 `api/services/recommendation.py`
- [ ] 实现 `estimate_rank(province, score, category)`：
  - 查询 `yifenyidang` → 如无2025数据则用最新年份回退
  - L2 Redis 缓存：`recommend:rank:{province}:{year}:{category}:{score}`
- [ ] 实现 `build_candidate_pool_four_tiers(req)`：
  - ① 提取特别关注区（意向学校，不计入15所）
  - ② L1 意向城市（城市→省份映射，60+城市）
  - ③ L2 本省学校
  - ④ L3 意向城市周边（邻省映射表）
  - ⑤ L4 全国兜底（邻省→沿海→全国）
  - 每层去重，最多105候选
- [ ] 实现城市→省份映射表（60+城市）和城市→邻省映射表

**验收标准**：
```python
# 单元测试
pool = build_candidate_pool_four_tiers(
    province="河南", city_preference=["郑州","武汉"], intended_schools=["北京大学"]
)
assert len(pool) <= 105
assert "北京大学" in [s.name for s in pool.special_attention]
```

---

### T2.5 · 推荐引擎概率计算（rankProb + weightedProb）
| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | T2.4 |
| **负责人** | 后端 ★ 核心任务 |

**任务清单**：
- [ ] 实现 `batch_query_admission(school_ids, province)`：
  - 批量查询 `admission_history WHERE school_id IN (...) AND province=?`
  - L1 Redis 缓存：`recommend:admission:{province}:{school_id}`
- [ ] 实现 `calc_rank_prob(student_rank, multi_year_history)`：
  - 取最近3年 min_rank 的中位数
  - 位次比较法公式（见 Architecture §推荐引擎）
  - 趋势修正（录取位次逐年收紧→下调5%）
  - 钳制到 [1, 99]
- [ ] 实现 `calc_weighted_prob(req, rank_prob, data)`：
  - 六维度加权：录取概率(35%) + 专业匹配(20%) + 就业(15%) + 城市(10%) + 性格(10%) + 经济(10%)
  - 性格匹配：外向→文科/综合类+10%、内向→理工科+10% 等
  - 经济偏好：困难+师范→师范类+10%、困难+无师→≤5000元年费公办+10%
  - 专业匹配：国家一流20%/省级一流15%/有专业10%/无专业0%
- [ ] 实现 Tier 分层 + 排序（含性格tiebreaker: rankProb差距≤5%→性格决胜）
- [ ] 实现 `detect_data_gaps()` → 缺数据写入 `school_admission_crawl_tasks`

**验收标准**：
```bash
curl -X POST /api/recommendation/generate \
  -H "Authorization: Bearer <token>" \
  -d '{"province":"河南","score":580,"subject_category":"理科","city_preference":["郑州"]}'
# → 200 {special_attention:[{name:"北京大学",rank_prob:0,...}], schools:[15所], ...}
# 验证：每所学校有 rankProb + weightedProb，tier 分布尽量5+5+5
```

---

### T2.6 · 推荐引擎16维度数据填充
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T2.5 |
| **负责人** | 后端 |

**任务清单**：
- [ ] 实现 16 维度数据聚合函数 `aggregate_school_dimensions(school_id, province, student)`：
  - 维度1-6：学校标签/概率/城市/分数线/位次匹配/趋势（来自 admission_history）
  - 维度7：推荐专业（匹配 student.major_preference）
  - 维度8：学费（如无数据，按学校类型估算：公办4500-6000/民办15000-30000）
  - 维度9：录取趋势（逐年分数变化+趋势方向）
  - 维度10：专业地位（查询 major_ranks 表）
  - 维度11-13：就业率/薪资/岗位（查询 employment_data 表，无数据时按专业类型估算）
  - 维度14：5年趋势（从 employment_data.trend_5yr 读取）
  - 维度15：城市分析（城市定位+产业优势+起薪+消费+留存率）
  - 维度16：AI点评（返回 null，异步生成）
- [ ] 16维度数据降级策略：有数据用数据，无数据用估算并标记 `data_source: "estimated"`
- [ ] 返回数据结构标记每个维度的 `data_source`：`"database"` | `"estimated"` | `"ai_generated"`

**验收标准**：
- 每所学校返回完整的 16 个维度对象
- 缺数据维度有合理估算值（非 null/空字符串）

---

### T2.7 · 直播答疑API + LLM调用
| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | T2.1 |
| **负责人** | 后端 |

**任务清单**：
- [ ] 实现 `POST /api/qa/ask`（Request: `{question}`）
  - System prompt：张雪峰风格口语化，犀利接地气，有数据支撑，200字以内
  - 调用 DeepSeek API（或配置的 LLM 接口）
  - 超时设置 10s，失败返回降级回答"AI暂时无法回答，请稍后重试"
  - 将问答记录写入 `qa_history` 日志表（可选，用于质量分析）
- [ ] LLM 客户端配置：支持 DeepSeek/Claude/GPT 三选一（环境变量切换）

**验收标准**：
```bash
curl -X POST /api/qa/ask \
  -H "Authorization: Bearer <token>" \
  -d '{"question":"计算机专业好就业吗？"}'
# → 200 {answer: "计算机这专业吧，不能说闭着眼都能找到工作..."}
```

---

### T2.8 · 报告记录 + 防倒卖检测
| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | T2.2 |
| **负责人** | 后端 |

**任务清单**：
- [ ] 实现 `POST /api/report/log`：记录每次报告生成
  - 写 `report_tasks` 表（student_hash, score_range, province, school_hash）
- [ ] 实现相似度检测（扣费时触发）：
  - 查询同主播近10条 report_tasks
  - 相同省份 + 相同分数段(±5分) + 相同意向学校哈希 → 标记 `similarity_flag=1`
  - 连续3次 `similarity_flag=1` → 标记 `similarity_flag=2` → 企业微信/钉钉告警
- [ ] MVP 阶段告警仅打印日志 + 前端提示（不做自动封禁）

**验收标准**：
- 连续3次提交高度相似报告 → `similarity_flag=2` → 日志输出 `[ALERT]`

---

## Phase 3：前端页面

### T3.1 · 前端框架搭建（index.html + 路由 + 手机模拟框）
| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | 无（可与后端并行）|
| **负责人** | 前端 |

**任务清单**：
- [ ] 创建 `index.html` 基础框架：
  - `.phone-frame` 手机模拟框（375×800px 固定）
  - `.status-bar`（28px）+ `.nav-bar`（flex-shrink:0）+ `.page-container`（flex:1, overflow-y:auto）+ `.home-bar`（24px）
  - CSS 变量体系（--color-danger/info/success/985/211 等，对齐 UI_Spec §1.2）
- [ ] 实现 hash-based 页面路由：
  - `#login` → `#student` → `#pref` → `#analyzing` → `#paywall` → `#report`
  - `#sample`（无需登录可访问）
  - `#qa`
  - 未登录时除 `#login` 和 `#sample` 外全部拦截回 `#login`
- [ ] 实现全局 Toast 通知组件（4种类型：成功/错误/警告/信息，顶部居中）
- [ ] 实现导航栏（9个按钮，当前页高亮，auth 控制可见性）
- [ ] 实现登录态管理：`localStorage` JWT 存取，过期检测，`fetch` 拦截器自动带 Bearer header

**验收标准**：
- 浏览器打开 `index.html` → 显示手机框 → 自动跳转 `#login`
- 导航栏点击切换页面（hash 变化）
- 配色/字体与 UI_Spec §1.2/§1.3 一致

---

### T3.2 · 登录页 + 考生信息页（STEP 1）
| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | T3.1 |
| **负责人** | 前端 |

**任务清单**：
- [ ] 登录页（`#login`）：
  - 品牌区（Logo + slogan + 数据背书：2200万+/6年/98.3%）
  - 手机号输入（type=tel, maxlength=11）+ 密码输入（带👁切换）+ 登录按钮（红色全宽）
  - 状态：idle/loading/error-credentials/error-disabled/success
  - 成功后存储 JWT + balance → 跳转 `#student`
- [ ] 考生信息页（`#student`）7字段表单：
  - 抖音昵称（text，必填）
  - 省份（select，31省）+ 选中后动态切换选科组件
  - 高考分数（number，上海/660 其余/750 动态显示，超限自动钳制）
  - 省内位次（number，选填，占位"可留空自动估算"）
  - 选科（动态组件：3+3=6科标签任选3，3+1+2=首选Radio+再选4选2；浙江+技术）
  - 服从调剂（双选标签）、家庭经济（select）
- [ ] 表单校验：必填标红+抖动，校验通过→跳转`#pref`

**验收标准**：
- 选择"上海"→满分显示/660；选择"河南"→选科组件切换为3+1+2
- 填入580分→选浙江→不能超过750自动钳制
- 必填为空点"下一步"→标红抖动

---

### T3.3 · 意向偏好页（STEP 2）
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T3.2 |
| **负责人** | 前端 |

**任务清单**：
- [ ] 专业方向：26个标签多选，4列网格排列
- [ ] 意向城市：16个预设城市标签 + 自定义输入框
- [ ] 意向院校搜索（最多3所）：
  - 输入≥2字符 → 300ms防抖 → `GET /api/schools/search?q=...`
  - 下拉列表最多8条（学校名+城市）
  - 选中→显示Tag可删除；选满3所→禁用搜索框
  - 搜索无结果→"未找到该学校"
- [ ] 性格/倾向：8个标签多选，2列网格
- [ ] 底部按钮：「← 返回」→ `#student`，「🚀 开始AI分析」→ `#analyzing`
- [ ] 点击「开始AI分析」→ 调用 `POST /api/recommendation/generate` → 进入分析中页面

**验收标准**：
- 搜索"郑州"→显示郑州大学等结果→点击选中→显示Tag+✕
- 选满3所后搜索框禁用
- 所有非必填字段可以不填直接点分析

---

### T3.4 · 分析中过渡页 + 付款墙
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T3.3, T2.5（推荐API可用） |
| **负责人** | 前端 |

**任务清单**：
- [ ] 分析中页面（`#analyzing`，浅色科技风，对齐UI_Spec浅色主题规范）：
  - 背景：`#F5F7FA→#EEF2FF→#F5F7FA`渐变 + 数据网点 + 扫描线
  - 中心脑图标🧠（56px）+ 标题"⚡ AI 深度分析中"（渐变色）
  - 三引擎徽章（Claude蓝点/DeepSeek紫点/GPT青点）
  - 2步动画：加载数据(~800ms)→AI分析(~700ms)，完成自动→`#paywall`
- [ ] 付款墙（`#paywall`）：
  - 调用推荐API返回数据 → 学校名称可见，概率+详情全部"——"遮蔽
  - 4个AI洞察区加密遮蔽
  - 剩余次数显示 + CTA"🔓 一键解锁完整报告"按钮
  - 状态切换：idle（可解锁）/loading（解锁中...）/insufficient（余额不足）

**验收标准**：
- 从`#pref`点击"开始AI分析"→分析动画~1.5s→自动跳转付款墙
- 付款墙显示15所学校名称，概率显示"——"
- 剩余次数=0时解锁按钮禁用+提示充值

---

### T3.5 · 完整报告页 + 特别关注区
| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前端** |  |
| **前置** | T3.4, T2.6 |
| **负责人** | 前端 ★ 核心任务 |

**任务清单**：
- [ ] 报告头部：报告编号 + 防伪标识 + 考生摘要行
- [ ] **📌 特别关注区**（意向学校，不计入15所）：
  - 展示条件：仅当考生填了意向学校时
  - 每所学校显示：名称 + rankProb（如实标注，含0%）+ 简要状态
  - 0%概率加特殊标注"您的成绩无法达到该校录取线"
- [ ] **饼图概览**：冲/稳/保分布（原生Canvas绘制环形图）
- [ ] **学校卡片（15所，16维度）**：
  - Tier 颜色区分（红=冲刺/蓝=稳妥/绿=保底）
  - 折叠/展开交互（默认展开冲刺，稳妥/保底可折叠）
  - 录取概率进度条 + 颜色编码
  - 16维度完整展示，缺数据维度显示"数据收集中..."
- [ ] 底部三个操作按钮：📥下载PDF / 👤下一位学生 / 🤖直播答疑

**验收标准**：
- 报告渲染后页面显示特别关注区(如有意向学校)+饼图+15张卡片
- 冲刺/稳妥/保底颜色正确
- 意向学校0%概率的卡片显示特殊标注

---

### T3.6 · PDF生成 + 下一位学生
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T3.5 |
| **负责人** | 前端 |

**任务清单**：
- [ ] PDF生成（html2canvas + jsPDF）：
  - 点击"📥 下载PDF"→ 按钮变"生成中…" → html2canvas截图 → jsPDF合成
  - 5种水印：报告编号页眉 + 防伪声明(红色) + 斜纹全页水印(主播手机后4位,45°,8-12%透明) + 考生信息摘要 + 封面二维码
  - 命名：`志愿报告_[网名]_[报告编号].pdf`
- [ ] "👤 下一位学生"按钮：
  - ① 清空 `student` 全局对象所有字段
  - ② 清空报告 DOM
  - ③ 跳转 `#student`
  - ④ 所有输入框/选择器恢复默认值
  - ⑤ 不清除 JWT / balance
- [ ] 浮动"回到顶部"按钮（滚动>800px显示）

**验收标准**：
- 点击下载PDF → 浏览器弹出文件下载 → 打开PDF包含5种水印
- 点击下一位学生 → 页面跳转到`#student` → 表单全部清空
- 余额保持解锁后的值

---

### T3.7 · 报告样板 + 直播答疑
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T3.5 |
| **负责人** | 前端 |

**任务清单**：
- [ ] 报告样板（`#sample`，无需登录）：
  - 顶部黄色横幅"★ 样板展示 · 仅供展示，非真实报告"
  - 硬编码预设数据：抖音用户_小明·河南·560分·物理+化学+政治
  - 包含完整15所学校卡片（静态HTML，不可交互）
- [ ] 直播答疑（`#qa`）：
  - 10个预设问题按钮（2列网格，点击填入输入框）
  - 自由输入文本框（限100字，实时计数）
  - 发送按钮 → `POST /api/qa/ask` → 答案气泡展示
  - 对话历史（本会话，刷新即清）
  - 清空输入/清空历史按钮

**验收标准**：
- 未登录可访问 `#sample`，展示完整样板报告
- qa页面输入问题→发送→返回回答→对话气泡展示

---

### T3.8 · 直播模式
| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | T3.5 |
| **负责人** | 前端 |

**任务清单**：
- [ ] 导航栏右侧"🔴 直播模式"按钮（脉冲动画，`@keyframes pulse`）
- [ ] 点击进入：
  - `requestFullscreen()` 全屏
  - 隐藏 `.nav-bar`
  - 隐藏 `.phone-frame` 边框
  - 根元素字号 ×1.2
  - 显示悬浮"退出直播"按钮
- [ ] 退出：Esc 或 点击退出按钮 → 恢复所有样式
- [ ] 浏览器不支持全屏时：模拟全屏样式（无导航+大字体）+ Toast"请手动全屏(F11)"

**验收标准**：
- 点击"🔴 直播模式"→ 全屏+无导航+大字体
- 按Esc → 恢复正常

---

## Phase 4：管理后台与交易

### T4.1 · 管理后台页面框架 + 管理员认证
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T2.1（auth中间件） |
| **负责人** | 后端+前端 |

**任务清单**：
- [ ] 创建 `admin.html`（独立页面，桌面端布局，非375px手机框）
  - 顶部标题栏 + 侧边导航（主播管理/订单查看/系统配置）+ 主内容区
- [ ] 管理员密码登录（独立JWT，与主播token不同）
- [ ] 后端：实现 Admin JWT 中间件，验证 `admin` role
- [ ] 前端：认证流程同主播端（localStorage存取 + 过期检测）

**验收标准**：
- `admin.html` 打开 → 显示管理后台登录
- 错误密码→红色提示；正确密码→进入主播管理页

---

### T4.2 · 主播管理CRUD
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前端+后端** |  |
| **前置** | T4.1 |
| **负责人** | 后端+前端 |

**任务清单**：
- [ ] 后端实现 `GET/POST /admin/streamers`：
  - 列表：分页（每页20条），7列（手机号/姓名/剩余次数/累计购买/已使用/状态/注册时间）
  - 新增：手机号+初始密码+主播姓名，`balance=0`
- [ ] 后端实现 `PUT /admin/streamers/{id}`：编辑手机号/密码/姓名
- [ ] 后端实现 `PATCH /admin/streamers/{id}/status`：启用/禁用（toggle）
- [ ] 前端：表格渲染 + 分页 + 新增弹窗 + 编辑弹窗 + 启用/禁用确认

**验收标准**：
- 列表正确显示所有主播 + 分页
- 新增主播→列表刷新→新主播出现，balance=0
- 禁用主播→主播无法登录（403禁止）

---

### T4.3 · 充值系统
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T4.2 |
| **负责人** | 后端+前端 |

**任务清单**：
- [ ] 后端实现 `POST /admin/streamers/{id}/recharge`（事务）：
  ```python
  BEGIN TRANSACTION
    UPDATE streamer_accounts SET balance = balance + count, purchased_total = purchased_total + count
    INSERT INTO streamer_recharge_logs (streamer_id, amount, count, operator, remark)
  COMMIT
  ```
- [ ] 前端：充值对话框
  - 显示当前剩余次数
  - 输入充值次数+金额（联动计算：10次=299元）
  - 确认→调用API→显示新余额
- [ ] 充值日志表记录：`streamer_id` / `amount` / `count` / `operator` / `remark`

**验收标准**：
- 充10次→主播 balance 增加10，purchased_total 增加10
- 充值记录出现在 `streamer_recharge_logs` 表
- 前端刷新后主播剩余次数显示正确

---

### T4.4 · 订单查看
| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | T4.2 |
| **负责人** | 后端+前端 |

**任务清单**：
- [ ] 后端实现 `GET /admin/orders`：
  - 列表：订单号/主播/考生/省份/分数/时间/状态
  - 支持日期范围筛选、按主播筛选
  - 按时间倒序，分页
- [ ] 前端：订单表格 + 筛选器 + 分页

**验收标准**：
- 订单列表正确显示所有解锁订单
- 日期筛选生效

---

### T4.5 · 系统配置管理
| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | T4.1 |
| **负责人** | 后端+前端 |

**任务清单**：
- [ ] 后端实现 `GET /admin/config`：读取 `system_config` 表所有配置
- [ ] 后端实现 `PUT /admin/config`：更新配置项
- [ ] 前端：配置表单
  - 省份满分表（31省可编辑）
  - 概率阈值：冲刺/稳妥/保底三段滑块
  - 低分阈值（<400分）
  - 定价（299元=10次）
- [ ] 配置缓存：读取时优先Redis，无则查MySQL（TTL 300s）

**验收标准**：
- 修改概率阈值→保存→下次推荐使用新阈值
- 配置更新后无需重启服务即可生效

---

## Phase 5：集成测试与部署

### T5.1 · 前后端联调（主流程）
| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | Phase 2 + Phase 3 全部 |
| **负责人** | 全员 |

**任务清单**：
- [ ] 端到端走通主流程：登录→填考生信息→填意向偏好→API推荐→付款墙→解锁→完整报告
- [ ] 验证：特别关注区正确显示意向学校（含0%概率标注）
- [ ] 验证：tier分布尽量5+5+5
- [ ] 验证：不同考生产生不同推荐结果（换省份/分数/意向确认差异化）
- [ ] 验证：扣费幂等（同一idempotency_key重试不重复扣费）
- [ ] 验证：下一位学生→表单清空→余额不变

**验收标准**：
- 全流程无报错，10分钟内完成一个完整考生推荐
- 幂等测试：同key扣2次→余额只减1次

---

### T5.2 · 边界场景测试
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T5.1 |
| **负责人** | 后端+前端 |

**任务清单**：
- [ ] 低分场景（<400分）：验证阈值降至5%，推荐学校数量不变
- [ ] 意向学校0%概率：验证报告顶部特别关注区展示 + "无法达到录取线"
- [ ] 意向城市无数据：验证降级到本省→周边→全国兜底
- [ ] 余额不足：验证付款墙按钮禁用 + 提示信息
- [ ] Token过期：验证自动跳转登录页 + Toast提示
- [ ] 账号禁用：验证登录返回403 + 提示
- [ ] 分数钳制：输入800分（非上海）→自动钳制到750
- [ ] Redis宕机模拟：停止Redis→验证扣费仍可用（降级为DB锁）
- [ ] 爬虫网关校验：提交`min_score=999`→验证写入`crawler_error_log`而非`admission_history`

**验收标准**：
- 所有边界场景不抛出500错误
- 低分考生仍能获得15所学校推荐（部分标记estimated）

---

### T5.3 · 性能测试
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T5.1 |
| **负责人** | 后端 |

**任务清单**：
- [ ] 推荐API响应时间（首次，无缓存）：目标<1s
- [ ] 推荐API响应时间（二次，L1/L2缓存命中）：目标<300ms
- [ ] 扣费API响应时间：目标<200ms
- [ ] 并发测试：10个并发请求 `/api/recommendation/generate`（相同参数）→ 验证无死锁/无超时
- [ ] 使用 `EXPLAIN` 确认关键查询走索引
- [ ] MySQL 慢查询日志检查（设置 `long_query_time=0.5`）

**验收标准**：
```bash
# 简单压测
for i in {1..10}; do
  curl -s -o /dev/null -w "%{time_total}\n" -X POST /api/recommendation/generate -H "..." -d '{...}' &
done
wait
# → P50 < 500ms, P99 < 1s
```

---

### T5.4 · 爬虫网关集成测试
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T1.3 |
| **负责人** | 后端 |

**任务清单**：
- [ ] 模拟爬虫服务器通过 HTTPS 推送数据（curl 模拟）
- [ ] 验证 `crawler_staging` 数据 → 校验通过 → 流入 `admission_history`
- [ ] 验证坏数据被拒绝并记录到 `crawler_error_log`
- [ ] 验证去重逻辑：同 school_id+province+year 不重复插入
- [ ] 验证数据质量导致推荐结果变化（爬虫补全前 vs 补全后对比）
- [ ] 验证 `data_quality` 标记变化：partial → full

**验收标准**：
- 新数据流入后，推荐引擎使用新数据计算概率
- `crawler_error_log` 中有坏数据的记录

---

### T5.5 · Nginx配置 + SSL验证
| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | T1.1, T5.1 |
| **负责人** | 运维 |

**任务清单**：
- [ ] 确认 Nginx 所有 location 正确代理：
  - `/auth/*`, `/api/*`, `/admin/*`, `/internal/*`, `/health`
- [ ] `/internal/*` 限制来源 IP 为爬虫服务器
- [ ] SSL 证书检查：`openssl x509 -checkend 604800`
- [ ] `nginx -t` 语法检查
- [ ] 配置缓存头：`school_data.js` 设置 `Cache-Control: public, max-age=3600`
- [ ] 配置 `/api/recommendation/generate` 响应不缓存：`Cache-Control: no-store`

**验收标准**：
```bash
curl -sk 'https://127.0.0.1/' -H 'Host: gaokao.lumenaistudio.co' | head -1
# → HTTP 200, content: index.html
nginx -t  # → syntax is ok / test is successful
```

---

### T5.6 · 生产部署 + 冒烟测试
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T5.1 ~ T5.5 全部 |
| **负责人** | 全员 |

**任务清单**：
- [ ] 后端：scp 代码到 `/root/gaokao-ai/` → `pkill -HUP -f 'uvicorn.*main:app'`
- [ ] 前端：scp `index.html` / `admin.html` / `school_data.js` 到 `/www/wwwroot/gaokao.lumenaistudio.co/`
- [ ] 数据库：如有 DDL 变更，执行 migrate
- [ ] 冒烟测试（生产环境）：
  ```bash
  curl -s https://gaokao.lumenaistudio.co/health  # → 200 ok
  # 登录 → 获取token → 搜索学校 → 生成推荐 → 扣费 → 查看报告
  ```
- [ ] 监控告警配置：企业微信/钉钉 webhook

**验收标准**：
- `/health` 返回200
- 全流程在浏览器中走通（需 Ctrl+F5 强制刷新）
- nginx 日志无异常

---

## Phase 6：上线加固

### T6.1 · 监控告警部署
| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | T5.6 |
| **负责人** | 运维 |

**任务清单**：
- [ ] 部署 crontab 健康检查脚本（每5分钟）：
  ```bash
  #!/bin/bash
  HEALTH=$(curl -s http://127.0.0.1:8000/health)
  if echo "$HEALTH" | grep -q '"status":"ok"'; then exit 0; fi
  # else: 发送企业微信/钉钉 webhook 告警
  ```
- [ ] 磁盘监控：`df -h | awk '$5>80'` → 告警
- [ ] 异常扣费监控：`SELECT COUNT(*) FROM streamer_accounts WHERE balance < 0` → >0 告警
- [ ] Redis 内存监控：`redis-cli INFO memory | grep used_memory_human`
- [ ] SSL 证书过期监控：`openssl x509 -checkend 604800`
- [ ] MySQL 慢查询日志告警

**验收标准**：
- 模拟磁盘不足 → 企业微信收到告警消息
- 健康检查脚本可手动执行并返回正确状态

---

### T6.2 · 数据备份方案验证
| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | T5.6 |
| **负责人** | 运维 |

**任务清单**：
- [ ] 配置 MySQL 每日自动备份到 OSS：
  ```bash
  mysqldump gaokao_ai | gzip | ossutil cp - oss://bucket/backup/gaokao_ai_$(date +%Y%m%d).sql.gz
  ```
- [ ] 备份保留策略：30天（OSS 生命周期规则）
- [ ] 验证备份恢复：从 OSS 下载最新备份 → 恢复到测试库 → 验证表数量+关键表行数

**验收标准**：
- OSS bucket 中存在最近2天的备份文件
- 测试库恢复后表数量与原库一致

---

### T6.3 · Redis 持久化 + 降级验证
| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | T5.6 |
| **负责人** | 运维+后端 |

**任务清单**：
- [ ] 确认 Redis RDB 配置生效：`redis-cli CONFIG GET save` → `3600 1`
- [ ] 确认 maxmemory-policy：`allkeys-lru`
- [ ] 模拟 Redis 宕机 → 验证扣费仍可用（DB锁降级）→ 验证搜索可用（直接查MySQL）
- [ ] Redis 恢复后验证缓存重新预热

**验收标准**：
- 停止 Redis → 扣费成功（仅DB锁）→ 搜索正常（退化为MySQL LIKE）
- 启动 Redis → 缓存逐步重建

---

### T6.4 · 文档更新 + 部署手册
| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | T5.6 |
| **负责人** | 全员 |

**任务清单**：
- [ ] 更新 Architecture.md 变更记录（v1.3）
- [ ] 更新 Tasks.md 完成状态
- [ ] 编写运维手册（启动/停止/重启/日志查看/备份恢复）
- [ ] 编写主播使用指南（截图版，1页PDF）
- [ ] 编写管理员操作指南（充值/新增主播/查看订单）

**验收标准**：
- 新人按运维手册可独立重启服务
- 主播按使用指南可独立完成一次志愿推荐

---

## 任务依赖图

```
Phase 1 (基础设施)
  T1.1 ──┬── T1.2 ── T1.3
         │
         └── T1.4
               │
Phase 2 (核心后端)         Phase 3 (前端)
  T2.1 ← T1.4              T3.1 (独立，可并行)
   ├── T2.2 ← T2.1+T1.2     ├── T3.2
   ├── T2.3 ← T1.4           │    ├── T3.3
   ├── T2.4 ← T2.3           │    │    ├── T3.4 ← T3.3+[T2.5]
   │    └── T2.5              │    │    │    └── T3.5 ← T3.4+[T2.6]
   │         └── T2.6         │    │    │         ├── T3.6
   ├── T2.7 ← T2.1           │    │    │         ├── T3.7
   └── T2.8 ← T2.2           │    │    │         └── T3.8
                              │    │    │
Phase 4 (管理与交易)          │    │    │
  T4.1 ← T2.1                │    │    │
   └── T4.2                  │    │    │
        ├── T4.3             │    │    │
        ├── T4.4             │    │    │
        └── T4.5             │    │    │
                              │    │    │
Phase 5 (集成部署)            │    │    │
  T5.1 ← Phase 2+3 ──────────┘────┘────┘
   ├── T5.2
   ├── T5.3
   ├── T5.4
   ├── T5.5
   └── T5.6
        │
Phase 6 (上线加固)
  T6.1 ← T5.6
  T6.2 ← T5.6
  T6.3 ← T5.6
  T6.4 ← T5.6  (可与T6.1-6.3并行)
```

## 关键路径（最短交付时间）

```
T1.1 → T1.4 → T2.1 → T2.3 → T2.4 → T2.5 → T2.6 (后端核心)
T3.1 → T3.2 → T3.3 → T3.4 → T3.5 → T3.6 (前端核心)
                                    ↓
                              T5.1 → T5.6 (联调+部署)
                                    ↓
                              T6.1 → T6.3 (上线加固)

关键路径总工时: ~72h (约9人天，单人开发)
前后端并行开发: ~60h (约7.5人天，双人开发)
```

---

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-06-17 | 初始版本：35个任务，6个Phase，~122h总工时 |
