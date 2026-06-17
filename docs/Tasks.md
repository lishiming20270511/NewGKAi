# AI高考志愿规划师 — 开发任务拆分

| 文档信息 | 内容 |
|---------|------|
| 产品名称 | AI高考志愿规划师 · 直播辅助工具 |
| 上级文档 | [PRD.md](./PRD.md) v4.0 · [Architecture.md](./Architecture.md) v2.0 |
| 创建日期 | 2026-06-17 |
| 总预估工时 | **~170h（约21人天）** |

---

## 任务总览

```
Phase 1: 基础设施搭建     (T1.1 ~ T1.4) ───  4个任务， 12h
Phase 2: 核心后端         (T2.1 ~ T2.8) ───  8个任务， 24h
Phase 3: 前端页面         (T3.1 ~ T3.8) ───  8个任务， 27h
Phase 4: 管理与交易       (T4.1 ~ T4.5) ───  5个任务， 14h
Phase 5: 集成测试与部署   (T5.1 ~ T5.6) ───  6个任务， 19h
Phase 6: 上线加固         (T6.1 ~ T6.4) ───  4个任务， 10h
Phase 7: v4.0 数据层升级  (T7.1 ~ T7.7) ───  7个任务， 22h  ★ 新增
Phase 8: v4.0 前端与体验  (T8.1 ~ T8.5) ───  5个任务， 18h  ★ 新增
Phase 9: v4.0 集成验证    (T9.1 ~ T9.3) ───  3个任务， 10h  ★ 新增
                                         ─────────────────
                                         50个任务，~156h
```

> **标注说明**：★ 新增 = PRD v4.0 相对旧版任务的新增内容。Phase 1-6 保留原有任务（适配 v2.0 架构），Phase 7-9 为 v4.0 专项升级任务。

---

## Phase 1：基础设施搭建

### T1.1 · 生产环境准备与Redis安装
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | 无 |
| **负责人** | 后端/运维 |

**任务清单**：
- [ ] 在 121.41.69.234 安装 Redis 7.x
- [ ] 配置 Redis：`maxmemory-policy allkeys-lru`，`save 3600 1`，`maxmemory 512mb`
- [ ] 创建 `gaokao` 系统用户（systemd 运行用户）
- [ ] 配置 MySQL 连接池：`pool_size=20, max_overflow=30`
- [ ] 配置 Nginx `/internal/*` 路由（仅允许爬虫IP 199.193.126.80）
- [ ] 验证：`redis-cli PING` → PONG

**验收标准**：
```bash
curl -s http://127.0.0.1:8000/health  # → {"status":"ok","mysql":"ok","redis":"ok"}
```

---

### T1.2 · 数据库Schema创建与索引优化
| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | T1.1 |
| **负责人** | 后端 |

**任务清单**：
- [ ] 创建 `crawler_staging` 临时表 + `crawler_error_log` 错误日志表
- [ ] 为 `orders` 表加 `idempotency_key` + `UNIQUE INDEX uk_idempotency`
- [ ] 确认 `admission_history` 索引：`idx_school_prov_year(school_id, province, year)`
- [ ] 确认 `yifenyidang` 索引：`uk_prov_year_sub_score(province, year, category, score)`
- [ ] 初始化 `system_config` 表预置数据（省份满分/概率阈值/定价）
- [ ] 运行 EXPLAIN 验证关键查询走索引

**验收标准**：关键查询 EXPLAIN 显示 Using index；`uk_idempotency` 存在。

---

### T1.3 · 爬虫数据网关基础（修复 ARR R2）
| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | T1.2 |
| **负责人** | 后端 |

**任务清单**：
- [ ] 创建 `api/routers/crawler.py`
- [ ] 实现 `POST /internal/crawler/ingest`：内部JWT认证 → 写入 `crawler_staging`
- [ ] 实现 `scripts/check_staging.py`（crontab 每5分钟）：校验 → MERGE INTO admission_history | 失败 → crawler_error_log
- [ ] Nginx 限制 `/internal/*` 仅爬虫IP访问
- [ ] 爬虫端改造：`fetch_school_facts.py` 不直连MySQL，改为 POST /internal/crawler/ingest

**验收标准**：模拟爬虫推送→数据经staging校验后流入admission_history；坏数据进入error_log。

---

### T1.4 · 项目脚手架与FastAPI基础路由
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T1.1 |
| **负责人** | 后端 |

**任务清单**：
- [ ] 创建项目目录结构（api/routers/, api/services/, api/models/, config/, scripts/）
- [ ] 配置 `.env`（DB连接串、JWT_SECRET、REDIS_URL、LLM_API_KEY、INTERNAL_JWT_SECRET）
- [ ] 创建空路由文件：auth.py / schools.py / recommendation.py / qa.py / report.py / admin.py / crawler.py
- [ ] 实现 `/health` 深度检查（MySQL + Redis 连通性）
- [ ] 配置 CORS、全局异常处理中间件

**验收标准**：`uvicorn main:app --port 8000` 启动成功；`/health` 返回 `{"status":"ok"}`。

---

## Phase 2：核心后端

### T2.1 · 认证系统（登录/注销/JWT/中间件）
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T1.4 |
| **负责人** | 后端 |

**任务清单**：
- [ ] 实现 `POST /auth/login`：bcrypt验证 → 签发JWT(24h) → 返回 `{token, streamer}`
- [ ] 实现 `POST /auth/logout`：JWT jti 加入 Redis 黑名单
- [ ] 实现 `GET /auth/streamer/profile`：返回主播信息+剩余次数
- [ ] 实现 JWT 验证中间件 `get_current_streamer()`：解码→黑名单检查→账号状态检查
- [ ] 实现 Admin JWT 中间件（管理员专用，独立于主播token体系）

**验收标准**：
```bash
curl -X POST /auth/login -d '{"phone":"13800138000","password":"test123"}'
# → 200 {token, streamer: {id, name, balance}}
```

---

### T2.2 · 扣费系统（幂等+原子事务，修复 ARR R1）
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T2.1, T1.2 |
| **负责人** | 后端 ★ 核心交易 |

**任务清单**：
- [ ] 实现 `POST /auth/deduct`（Request: `{idempotency_key}`）：
  - Redis 分布式锁（可选，失败降级为DB锁）
  - 幂等检查：`SELECT id FROM orders WHERE streamer_id=? AND idempotency_key=?`
  - `SELECT ... FOR UPDATE` + 原子扣减
  - INSERT orders + INSERT report_tasks
- [ ] 订单号生成：`GK` + `YYYYMMDD-HHmm` + `-` + 4位随机hex
- [ ] 异常处理：400（余额不足）、409（已处理）

**验收标准**：同idempotency_key重试2次→余额只减1次；返回 `already_processed: true`。

---

### T2.3 · 学校搜索API
| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | T1.4 |
| **负责人** | 后端 |

**任务清单**：
- [ ] 实现 `GET /api/schools/search?q=郑州&limit=8`：MySQL FULLTEXT 搜索
- [ ] 实现 `GET /api/schools/{school_id}`：完整学校信息
- [ ] city 为空时用 `getCityFromSchoolName()` 从校名提取

**验收标准**：搜索"郑州"→返回郑州大学等；无结果返回空数组。

---

### T2.4 · 推荐引擎核心（位次估算 + 四层填充）
| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | T2.3 |
| **负责人** | 后端 ★ 核心算法 |

**任务清单**：
- [ ] 实现 `api/services/recommendation.py`
- [ ] 实现 `estimate_rank()`：yifenyidang查询 + Redis L2缓存
- [ ] 实现 `build_candidate_pool_four_tiers()`：
  - ① 提取特别关注区（意向学校，不计入15所）
  - ② L1 意向城市 → L2 本省 → L3 周边 → L4 全国兜底
  - 每层去重，最多105候选
- [ ] 城市→省份映射表（60+城市） + 邻省映射表

**验收标准**：候选池≤105所；意向学校单独提取到 special_attention 数组。

---

### T2.5 · 推荐引擎概率计算（rankProb + weightedProb）
| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | T2.4 |
| **负责人** | 后端 ★ 核心算法 |

**任务清单**：
- [ ] 实现 `batch_query_admission()`：批量查询，Redis L1缓存
- [ ] 实现 `calc_rank_prob()`：取最近3年 min_rank 中位数 → 位次比较法 → 趋势修正
- [ ] 实现 `calc_weighted_prob()`：六维度加权（录取35%+专业20%+就业15%+城市10%+性格10%+经济10%）
- [ ] 性格匹配：外向→文科/综合+10%、内向→理工科+10%、动手→工科+10%、艺术→艺术类+10%
- [ ] Tier分层（冲刺30-60%/稳妥60-85%/保底≥85%）+ 排序（含性格tiebreaker）
- [ ] 实现 `detect_data_gaps()` → 缺数据写入爬虫任务表

**验收标准**：不同考生产生不同推荐结果；tier分布尽量5+5+5。

---

### T2.6 · 推荐引擎16维度数据填充（v4.0 核心后端任务）

| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | T2.5, T7.1（新表已建） |
| **负责人** | 后端 ★ v4.0 核心 |

**任务清单**：
- [ ] 实现 `aggregate_school_dimensions(school_id, province, student)` 查询所有新表：
  - 维度7 推荐专业：查询 `school_majors` → 无则 `major_similarity` 相近专业映射
  - 维度8 学费：查询 `school_tuition` → 无则按学校类型估算（公办4500-6000/民办15000-30000）
  - 维度11 就业率：查询 `school_employment` → 无则按专业类型估算
  - 维度12 薪资：查询 `school_salary` → 无则按城市等级估算
  - 维度15 城市分析：查询 `city_analysis` → 无则创建 `school_city_crawl_tasks`
- [ ] 每个维度标记 `data_source`：`"database"` | `"estimated"` | `"pending_crawl"`
- [ ] 数据降级策略：数据库有→直接用; 无→估算+标记; 冷门学校→创建爬虫任务

**验收标准**：
```bash
curl -X POST /api/recommendation/generate \
  -H "Authorization: Bearer *** \
  -d '{"province":"河南","score":580,"subject_category":"物理",...}'
# → 每所学校返回完整16维度dimensions对象
# → 不同学校推荐专业/学费/就业率/薪资差异化
# → data_quality_summary.crawl_tasks_created >= 0
```

---

### T2.7 · 直播答疑API + LLM调用
| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | T2.1 |
| **负责人** | 后端 |

**任务清单**：
- [ ] 实现 `POST /api/qa/ask`：System prompt（口语化直白，200字内，禁用"张雪峰"品牌）
- [ ] 调用 DeepSeek API，超时10s，失败返回降级回答
- [ ] LLM 客户端支持 DeepSeek/Claude/GPT 三选一（环境变量切换）

**验收标准**：输入问题→返回口语化回答；LLM不可用时返回降级提示。

---

### T2.8 · 报告记录 + 防倒卖检测
| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | T2.2 |
| **负责人** | 后端 |

**任务清单**：
- [ ] 扣费时同步写入 `report_tasks`（student_hash, score_range, province, school_hash）
- [ ] 检测同主播近10条：同省+同分±5+同意向哈希 → `similarity_flag=1`
- [ ] 连续3次 → `similarity_flag=2` → 日志告警

**验收标准**：连续3次高度相似→`similarity_flag=2`→日志输出 `[ALERT]`。

---

## Phase 3：前端页面

### T3.1 · 前端框架搭建（index.html + 路由 + 手机模拟框）
| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | 无 |
| **负责人** | 前端 |

**任务清单**：
- [ ] 创建 `index.html`——`.phone-frame`（375×800px固定）+ `.status-bar` + `.nav-bar` + `.page-container` + `.home-bar`
- [ ] CSS 变量体系（--color-danger/info/success/985/211/accent 等，v4.0 预备 Bento Grid 暗色变量但先完成浅色版功能）
- [ ] hash-based 路由：`#login`→`#student`→`#pref`→`#analyzing`→`#paywall`→`#report`
- [ ] Toast 通知组件（成功/错误/警告/信息）
- [ ] 导航栏 + 登录态管理（localStorage JWT + expires检测 + fetch拦截器）

**验收标准**：打开 index.html → 手机框 → 自动跳转 `#login`；导航栏页面切换正常。

---

### T3.2 · 登录页 + 考生信息页（STEP 1）
| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | T3.1 |
| **负责人** | 前端 |

**任务清单**：
- [ ] 登录页：品牌区 + 5行宣传文案 + 手机号+密码+登录 + 状态管理
- [ ] 考生信息页7字段：昵称/省份/分数/位次/选科/调剂/家庭经济
- [ ] 动态选科：3+3（6科标签任选3，浙江+技术） / 3+1+2（首选Radio+再选4选2）
- [ ] 表单校验：必填标红+抖动；分数钳制（上海/660，其余/750）

**验收标准**：选上海→满分/660；输入800→钳制750；必填为空→标红。

---

### T3.3 · 意向偏好页（STEP 2）
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T3.2 |
| **负责人** | 前端 |

**任务清单**：
- [ ] 专业方向26标签多选（4列网格）+ 意向城市16预设+自定义
- [ ] 意向院校搜索：输入≥2字→300ms防抖→API搜索→下拉8条→选Tag可删→最多3所
- [ ] 性格8标签多选（2列网格）
- [ ] 「← 返回」→ `#student`，「🚀 开始AI分析」→ 调用推荐API → `#analyzing`

**验收标准**：搜索"郑州"→显示学校列表→选中→Tag✕；选满3所禁用搜索框。

---

### T3.4 · 分析中过渡页 + 付款墙
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T3.3, T2.5 |
| **负责人** | 前端 |

**任务清单**：
- [ ] 分析中页面（`#analyzing`）：暗色底+网点+扫描线+🧠图标+三引擎徽章+2步动画(~1.5s)
- [ ] 付款墙：学校名称可见，概率详情"——"遮蔽；剩余次数 + 🔓解锁按钮
- [ ] 解锁流程：乐观扣减 balance-1 → POST /auth/deduct → 成功→`#report` / 失败→回滚

**验收标准**：分析动画→付款墙；解锁成功→完整报告；余额=0→按钮禁用。

---

### T3.5 · 完整报告页 + 特别关注区（v4.0 已重构为5大板块）

| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | T3.4, T2.6 |
| **负责人** | 前端 ★ 核心页面 |

**任务清单**：
- [ ] 报告头部：报告编号 + 防伪标识 + 考生摘要行
- [ ] **📌 特别关注区**（独立于15所）：
  - 展示条件：考生填了意向学校时才显示
  - 琥珀色 `#F59E0B` 强调 + ★标记
  - 0%概率显示"您的成绩无法达到该校录取线"
- [ ] **饼图概览**：冲/稳/保环形图（Canvas原生绘制）
- [ ] **学校卡片（15所，16维度）**：Tier三色 + 折叠/展开 + 概率进度条
- [ ] **AI 个性化填报建议书**（6节）：成绩定位/梯度策略/调剂风险/经济适配/性格匹配/四大原则
- [ ] **免责声明**卡片
- [ ] 底部三按钮：📥下载PDF / 👤测下一个 / 🤖直播答疑

**验收标准**：报告渲染后显示特别关注区+饼图+15张卡片；冲刺/稳妥/保底颜色正确。

---

### T3.6 · PDF生成 + 测下一个（v4.0 升级为5种水印）

| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T3.5 |
| **负责人** | 前端 |

**任务清单**：
- [ ] PDF生成（html2canvas scale:3 保证300DPI + jsPDF）：
  - 5种水印：①报告编号页眉 ②防伪声明(红色) ③斜纹全页(主播手机后4位,45°,8-12%) ④考生信息卡片 ⑤封面二维码
  - 封面：浅蓝渐变 `#E6F0FF`，5区块（品牌区→大标题→考生信息卡→数据权威卡→底部免责）
  - 正文页：延续渐变底+水印+16维度卡片+页眉页脚
  - 命名：`志愿报告_[网名]_[报告编号].pdf`
- [ ] 「👤 测下一个」：4步清空（student对象→报告DOM→跳转#student→恢复默认值）

**验收标准**：PDF打开含5种水印；封面5区块完整；测下一个→表单全空。

---

### T3.7 · 报告样板 + 直播答疑
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T3.5 |
| **负责人** | 前端 |

**任务清单**：
- [ ] 报告样板（`#sample`）：顶部琥珀横幅"★ 样板展示"，硬编码预设数据，无需登录
- [ ] 直播答疑（`#qa`）：10预设问题+自由输入(限100字)+AI回答气泡+对话历史

**验收标准**：未登录可查看样板；qa页面发送问题→显示回答。

---

### T3.8 · 直播模式
| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | T3.5 |
| **负责人** | 前端 |

**任务清单**：
- [ ] 导航栏"🔴 直播模式"按钮（脉冲动画）
- [ ] 进入：全屏+隐藏导航+隐藏手机框边框+字号×1.2+悬浮退出按钮
- [ ] 退出：Esc或点击退出按钮→恢复

**验收标准**：点击直播→全屏大字体；Esc→恢复。

---

## Phase 4：管理后台与交易

### T4.1 · 管理后台页面框架 + 管理员认证
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T2.1 |
| **负责人** | 后端+前端 |

**任务清单**：
- [ ] 创建 `admin.html`（桌面端布局：侧边导航+主内容区）
- [ ] 管理员登录（使用 `admin_accounts` 表，独立 JWT）
- [ ] Admin JWT 中间件
- [ ] v4.0 预备：支持 `super_admin` / `admin` 角色

**验收标准**：admin.html 登录 → 进入主播管理页。

---

### T4.2 · 主播管理CRUD
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T4.1 |
| **负责人** | 后端+前端 |

**任务清单**：
- [ ] 后端：`GET/POST/PUT /admin/streamers` + `PATCH /admin/streamers/{id}/status`
- [ ] 前端：表格（7列）+ 分页 + 新增/编辑弹窗 + 启用/禁用确认

**验收标准**：新增主播→列表刷新→balance=0；禁用→主播无法登录。

---

### T4.3 · 充值系统
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T4.2 |
| **负责人** | 后端+前端 |

**任务清单**：
- [ ] 后端：`POST /admin/streamers/{id}/recharge`（事务：balance+purchased_total增加 + 写充值日志）
- [ ] 前端：充值对话框（显示当前次数+输入次数/金额联动+备注）

**验收标准**：充10次→balance+10，日志表有记录。

---

### T4.4 · 订单查看
| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | T4.2 |
| **负责人** | 后端+前端 |

**任务清单**：
- [ ] 后端：`GET /admin/orders`（列表+日期/主播筛选+分页）
- [ ] 前端：订单表格 + 筛选器

**验收标准**：订单列表显示所有解锁记录；筛选生效。

---

### T4.5 · 系统配置管理
| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | T4.1 |
| **负责人** | 后端+前端 |

**任务清单**：
- [ ] 后端：`GET/PUT /admin/config`（system_config KV表 + Redis缓存TTL 300s）
- [ ] 前端：省份满分/概率阈值滑块/低分阈值/定价编辑

**验收标准**：修改阈值→保存→推荐使用新值。

---

## Phase 5：集成测试与部署

### T5.1 · 前后端联调（主流程）
| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | Phase 2+3 全部 |
| **负责人** | 全员 |

**任务清单**：
- [ ] 端到端走通：登录→填表→推荐→付费解锁→报告→下一位
- [ ] 验证特别关注区 + tier分布 + 幂等扣费
- [ ] 验证不同考生差异化结果

**验收标准**：全流程无报错；同key扣2次余额只减1次。

---

### T5.2 · 边界场景测试
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T5.1 |
| **负责人** | 后端+前端 |

**任务清单**：
- [ ] 低分<400：阈值降至5%
- [ ] 意向学校0%概率展示
- [ ] 余额不足/Token过期/账号禁用/分数钳制
- [ ] Redis宕机模拟（扣费降级DB锁）
- [ ] 爬虫网关：坏数据进error_log非admission_history

**验收标准**：所有边界场景不抛500。

---

### T5.3 · 性能测试
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T5.1 |
| **负责人** | 后端 |

**任务清单**：
- [ ] 推荐API：首次<1s，缓存命中<300ms
- [ ] 扣费API：<200ms
- [ ] 10并发→无死锁/无超时
- [ ] MySQL慢查询日志检查

**验收标准**：P50<500ms，P99<1s。

---

### T5.4 · 爬虫网关集成测试
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T1.3 |
| **负责人** | 后端 |

**任务清单**：
- [ ] 模拟爬虫推送→staging→校验→MERGE→数据流入
- [ ] 验证坏数据进error_log + 去重逻辑
- [ ] 数据补全前后推荐结果对比

**验收标准**：新数据流入后推荐使用新数据；error_log有坏数据。

---

### T5.5 · Nginx配置验证（v3.2 — IP直连HTTP）
| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | T1.1, T5.1 |
| **负责人** | 运维 |

**任务清单**：
- [ ] 确认 Nginx HTTP:80 `/etc/nginx/sites-enabled/gaokao-ip` 所有 location 正确
- [ ] `/internal/*` IP白名单限制
- [ ] `/api/recommendation/generate` 响应 `Cache-Control: no-store`
- [ ] `nginx -t` 语法检查

**验收标准**：
```bash
curl -s http://121.41.69.234/health  # → {"status":"ok"}
nginx -t                              # → syntax ok
```

---

### T5.6 · 生产部署 + 冒烟测试
| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T5.1~T5.5 |
| **负责人** | 全员 |

**任务清单**：
- [ ] 后端部署：scp→pkill -HUP uvicorn
- [ ] 前端部署：scp index.html/admin.html
- [ ] 如有DDL变更执行migrate
- [ ] 冒烟测试：登录→推荐→扣费→报告→PDF

**验收标准**：`/health` 200；全流程浏览器走通（Ctrl+F5刷新）。

---

## Phase 6：上线加固

### T6.1 · 监控告警部署
| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | T5.6 |
| **负责人** | 运维 |

**任务清单**：
- [ ] crontab 健康检查（每5分钟 curl /health → 连续3次失败告警）
- [ ] 磁盘>80%告警 + 异常扣费(balance<0)告警
- [ ] Redis 内存监控 + MySQL 慢查询告警

**验收标准**：企业微信收到告警消息。

---

### T6.2 · 数据备份方案验证
| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | T5.6 |
| **负责人** | 运维 |

**任务清单**：
- [ ] MySQL 每日自动备份到 OSS（保留30天）
- [ ] 验证备份恢复流程

**验收标准**：OSS有最近2天备份；恢复后表数量一致。

---

### T6.3 · Redis 持久化 + 降级验证
| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | T5.6 |
| **负责人** | 运维+后端 |

**任务清单**：
- [ ] Redis RDB 配置验证
- [ ] 停Redis→扣费可用(DB锁)→搜索可用(MySQL LIKE)→重启Redis→缓存预热

**验收标准**：Redis宕机不影响核心业务流程。

---

### T6.4 · 文档更新 + 部署手册
| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | T5.6 |
| **负责人** | 全员 |

**任务清单**：
- [ ] 更新 Architecture.md 版本记录
- [ ] 编写运维手册 + 主播使用指南 + 管理员操作指南

**验收标准**：新人可按手册独立操作。

---

## Phase 7：v4.0 数据层升级 ★ 新增

> **此阶段为 PRD v4.0 相对旧版的核心数据层变更。必须在 Phase 1-6 基础上执行。**

### T7.1 · v4.0 新增数据表DDL（5张静态数据表）

| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T1.2（基础DB已就绪） |
| **负责人** | 后端 ★ v4.0 数据奠基 |

**任务清单**：
- [ ] 创建 `school_majors` 表（各校专业列表 + `major_level` 分级）：
  ```sql
  CREATE TABLE school_majors (
      school_id INT, major_name VARCHAR(128), major_level VARCHAR(32),
      discipline VARCHAR(64), UNIQUE KEY uk_school_major (school_id, major_name)
  );
  ```
- [ ] 创建 `major_similarity` 表（专业相似度映射）并预置初始数据：
  ```sql
  CREATE TABLE major_similarity (
      source_major VARCHAR(64), target_major VARCHAR(64),
      similarity DECIMAL(3,2), UNIQUE KEY uk_pair (source_major, target_major)
  );
  -- 预置：26个意向专业 × 每专业3-5个相近专业 ≈ 100条映射
  -- 示例：通信工程↔信息工程(0.95)/电子信息工程(0.90)/电子科学与技术(0.85)
  ```
- [ ] 创建 `school_tuition` 表（学费校×专业）：
  ```sql
  CREATE TABLE school_tuition (
      school_id INT, major_name VARCHAR(128), tuition_per_year INT,
      duration_years TINYINT DEFAULT 4, data_source VARCHAR(255), data_year INT
  );
  ```
- [ ] 创建 `school_employment` 表（就业率+深造率 + 数据来源标注）：
  ```sql
  CREATE TABLE school_employment (
      school_id INT UNIQUE, employment_rate DECIMAL(5,2),
      graduate_rate DECIMAL(5,2), data_source VARCHAR(255), data_year INT
  );
  ```
- [ ] 创建 `school_salary` 表（薪资校×专业）：
  ```sql
  CREATE TABLE school_salary (
      school_id INT, major_name VARCHAR(128),
      salary_start_min INT, salary_start_max INT,
      salary_3yr_min INT, salary_3yr_max INT,
      data_source VARCHAR(255), data_year INT
  );
  ```
- [ ] 创建 `city_analysis` 表（城市5维分析）：
  ```sql
  CREATE TABLE city_analysis (
      city_name VARCHAR(32) UNIQUE, location TEXT, advantage TEXT,
      development TEXT, main_business TEXT, city_level VARCHAR(16)
  );
  ```

**验收标准**：
```sql
SHOW TABLES LIKE '%school_majors%';       -- → school_majors
SHOW TABLES LIKE '%major_similarity%';    -- → major_similarity
SHOW TABLES LIKE '%school_tuition%';      -- → school_tuition
SHOW TABLES LIKE '%school_employment%';   -- → school_employment
SHOW TABLES LIKE '%school_salary%';       -- → school_salary
SHOW TABLES LIKE '%city_analysis%';       -- → city_analysis
SELECT COUNT(*) FROM major_similarity;    -- → >= 80 条预置映射
```

**为什么需要**：PRD v4.0 对16维度提出了数据真实性要求——不同学校必须展示不同的专业/学费/就业率/薪资/城市分析，禁止全校统一模板。这5张表是数据差异化呈现的基础设施。

---

### T7.2 · admin_accounts 独立认证体系 + 密码管理API

| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T4.1（管理后台已有框架） |
| **负责人** | 后端 |

**任务清单**：
- [ ] 创建 `admin_accounts` 表（独立于 streamer_accounts）：
  ```sql
  CREATE TABLE admin_accounts (
      id INT AUTO_INCREMENT PRIMARY KEY,
      username VARCHAR(64) UNIQUE, password_hash VARCHAR(255),
      role ENUM('super_admin','admin') DEFAULT 'admin',
      status ENUM('active','disabled') DEFAULT 'active',
      last_login_at DATETIME
  );
  ```
- [ ] 修改 T4.1 管理员登录逻辑：从查询 `streamer_accounts` → 改为查询 `admin_accounts`
- [ ] 实现 `POST /admin/change-password`（v4.0 新增——主播和管理员通用）：
  - 验证旧密码 → 校验新密码6-20位 → bcrypt更新
  - 根据 token 类型自动判断更新 `streamer_accounts` 还是 `admin_accounts`
- [ ] 实现 `POST /admin/streamers/{id}/reset-password`（v4.0 新增——管理员重置主播密码）：
  - 仅 `super_admin` 可调用
  - 生成随机8位密码 → 返回明文（仅此一次）→ bcrypt存储
- [ ] 修改 T2.1 Auth中间件：`get_current_user()` 同时支持主播JWT和管理员JWT

**验收标准**：
```bash
# 主播自助改密码
curl -X POST /admin/change-password \
  -H "Authorization: Bearer <streamer_token>" \
  -d '{"old_password":"old","new_password":"new123"}'
# → 200 {"success": true}

# 管理员重置主播密码
curl -X POST /admin/streamers/1/reset-password \
  -H "Authorization: Bearer <admin_token>"
# → 200 {"new_password": "aB3xK9mQ"}  # 随机8位

# 旧密码登录失败
curl -X POST /auth/login -d '{"phone":"138...", "password":"old"}'
# → 401
```

**为什么需要**：PRD v4.0 §1.2 明确要求管理员账号独立于主播体系；§1.1 新增主播自助改密码和密码重置功能。

---

### T7.3 · 6类爬虫任务表DDL + 爬虫端改造

| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T1.3（爬虫网关基础已有） |
| **负责人** | 后端 |

**任务清单**：
- [ ] 创建 6 类爬虫任务表（Architecture v2.0 §4.5）：
  ```sql
  -- 模板结构（6张表共用）
  CREATE TABLE school_admission_crawl_tasks (
      school_id INT, province VARCHAR(32), year INT,
      status ENUM('pending','running','done','failed') DEFAULT 'pending',
      retry_count INT DEFAULT 0, error_msg TEXT
  );
  -- 同理创建：school_major_crawl_tasks / school_tuition_crawl_tasks /
  --           school_employment_crawl_tasks / school_salary_crawl_tasks /
  --           school_city_crawl_tasks (city_name 替代 school_id)
  ```
- [ ] 更新 `scripts/check_staging.py`：从仅处理 `admission_history` → 扩展为处理 6 类数据（admission / major / tuition / employment / salary / city）
- [ ] 更新 `POST /internal/crawler/ingest`：Request body 新增 `data_type` 字段 → 路由到对应的 staging 处理逻辑
- [ ] 爬虫端（199.193.126.80）改造：
  - 新增专业爬虫脚本 `fetch_school_majors.py`
  - 新增学费爬虫脚本 `fetch_school_tuition.py`
  - 新增就业/薪资/城市爬虫脚本
  - 所有脚本统一 POST 到 `/internal/crawler/ingest`
- [ ] 爬取优先级调度：`check_staging.py` 按优先级处理 pending 任务（录取>专业>学费>就业>薪资>城市）

**验收标准**：
```sql
SHOW TABLES LIKE '%crawl_tasks';  
-- → school_admission_crawl_tasks, school_major_crawl_tasks, 
--    school_tuition_crawl_tasks, school_employment_crawl_tasks,
--    school_salary_crawl_tasks, school_city_crawl_tasks
-- 共6张

-- 模拟专业数据推送
curl -X POST /internal/crawler/ingest \
  -H "Authorization: Bearer <internal_jwt>" \
  -d '{"data_type":"major","records":[{"school_id":123,"major_name":"计算机科学与技术","major_level":"国家级一流"}]}'
# → {"ingested": 1}
```

**为什么需要**：PRD v4.0 §1.3 定义了6类爬虫任务表以支持16维度数据补全。旧版只有1类（录取数据），v4.0 需扩展为专业/学费/就业/薪资/城市共6类。

---

### T7.4 · 推荐引擎适配新数据表（16维度查询）

| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | T7.1, T7.3, T2.5 |
| **负责人** | 后端 ★ v4.0 核心重构 |

**任务清单**：
- [ ] 重构 `aggregate_school_dimensions()` 函数，从新表查询而非使用估算值：
  ```python
  async def aggregate_school_dimensions(school_id, student, db):
      dims = {}
      
      # 维度7：推荐专业（★ 核心差异化逻辑）
      intended_majors = student.major_preference or []
      school_majors = await db.fetch_all(
          "SELECT major_name, major_level FROM school_majors WHERE school_id=?", (school_id,)
      )
      if school_majors:
          # 精确匹配意向专业
          matched = [m for m in school_majors if m['major_name'] in intended_majors]
          if matched:
              dims['recommended_major'] = matched[0]
          else:
              # 相似度映射
              similar = await db.fetch_all(
                  """SELECT target_major FROM major_similarity 
                     WHERE source_major IN ({}) ORDER BY similarity DESC LIMIT 1"""
                  .format(','.join('?'*len(intended_majors))),
                  intended_majors
              )
              dims['recommended_major'] = similar[0] if similar else school_majors[0]
              dims['major_note'] = '相近专业'  # 标注
      else:
          # 创建爬虫任务 + 标记pending
          await create_crawl_task('major', school_id)
          dims['recommended_major'] = {'major_name': '数据获取中…'}
      
      # 维度8：学费（★ 差异化）
      tuition = await db.fetch_one(
          "SELECT * FROM school_tuition WHERE school_id=? AND major_name=?",
          (school_id, dims['recommended_major']['major_name'])
      )
      if tuition:
          dims['tuition_per_year'] = f"{tuition['tuition_per_year']}元/年"
          dims['tuition_total'] = f"4年约{tuition['tuition_per_year']*4/10000:.1f}万"
      else:
          # 按学校类型估算 + 创建爬虫任务
          dims['tuition_per_year'] = estimate_tuition(school_type)
          await create_crawl_task('tuition', school_id)
      
      # 维度11：就业率（★ 差异化 + 来源标注）
      emp = await db.fetch_one(
          "SELECT * FROM school_employment WHERE school_id=?", (school_id,)
      )
      if emp:
          dims['employment_rate'] = f"{emp['employment_rate']}%"
          dims['employment_source'] = f"数据来源：{emp['data_source']}（{emp['data_year']}年）"
      else:
          # 按专业类型估算 + 创建爬虫任务
          dims['employment_rate'] = estimate_employment(major_category)
          await create_crawl_task('employment', school_id)
      
      # 维度12：薪资（★ 差异化）
      salary = await db.fetch_one(
          "SELECT * FROM school_salary WHERE school_id=?", (school_id,)
      )
      if salary:
          dims['avg_salary'] = f"应届起薪{salary['salary_start_min']}-{salary['salary_start_max']}元/月；3年后{salary['salary_3yr_min']}-{salary['salary_3yr_max']}元/月"
      else:
          dims['avg_salary'] = estimate_salary(city_level, major_category)
          await create_crawl_task('salary', school_id)
      
      # 维度15：城市5维分析（★ 同城前4维缓存复用，第5维微调）
      city_data = await db.fetch_one(
          "SELECT * FROM city_analysis WHERE city_name=?", (school_city,)
      )
      if city_data:
          dims['city_analysis'] = {
              'location': city_data['location'],
              'advantage': city_data['advantage'],
              'development': city_data['development'],
              'main_business': city_data['main_business'],
              'career_impact': generate_career_impact(city_data, school_id, dims['recommended_major'])
          }
      else:
          await create_crawl_task('city', city_name=city_name)
          dims['city_analysis'] = {'location': f'{city_name}（数据获取中…）'}
      
      return dims
  ```
- [ ] 每个维度标记 `data_source`：`"database"` / `"estimated"` / `"pending_crawl"`
- [ ] 更新 `data_quality_summary` 返回格式：按类型统计爬虫任务创建数量
- [ ] 确保不同学校的推荐专业/学费/就业率/薪资/城市分析差异化

**验收标准**：
```bash
# 测试：河南580分，意向计算机
curl -X POST /api/recommendation/generate \
  -H "Authorization: Bearer <token>" \
  -d '{"province":"河南","score":580,"subject_category":"物理","major_preference":["计算机"]}'
# → 返回15所学校
# 验证：不同学校的 dimensions.recommended_major 不同（有计算机的显示计算机，无的显示相近专业+标注）
# 验证：不同学校的 dimensions.tuition_per_year 不同
# 验证：不同学校的 dimensions.avg_salary 不同
# 验证：不同学校的 dimensions.city_analysis 随城市变化
```

**为什么需要**：PRD v4.0 §⑦-⑫ 对推荐专业/学费/就业率/薪资/城市分析提出了严格的"不同学校必须差异化"要求。旧版 T2.6 使用估算值填充，v4.0 需从新增数据表查询真实数据。

---

### T7.5 · 专业相似度映射预置数据（major_similarity seeding）

| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | T7.1 |
| **负责人** | 后端/数据 |

**任务清单**：
- [ ] 编写 `scripts/seed_major_similarity.py`：为 PRD §附录A 的26个意向专业创建相似度映射
- [ ] 每个专业至少3-5个相近专业，按相似度递减排列：
  ```
  计算机科学与技术 → 软件工程(0.95) / 人工智能(0.85) / 数据科学(0.85) / 信息安全(0.80) / 物联网工程(0.75)
  通信工程       → 信息工程(0.95) / 电子信息工程(0.90) / 电子科学与技术(0.85) / 光电信息(0.75)
  临床医学       → 基础医学(0.80) / 医学影像学(0.75) / 麻醉学(0.70) / 预防医学(0.60)
  金融学         → 经济学(0.85) / 国际经济与贸易(0.75) / 保险学(0.70) / 财政学(0.70)
  ...
  ```
- [ ] 26 × 4 = ~104 条映射数据
- [ ] 运行脚本 insert 到 `major_similarity` 表（ON DUPLICATE KEY UPDATE）

**验收标准**：
```sql
SELECT COUNT(*) FROM major_similarity;  -- → >= 100
SELECT * FROM major_similarity WHERE source_major='通信工程';  
-- → 至少3条，包含信息工程/电子信息工程/电子科学与技术
```

---

### T7.6 · 热门院校学费数据初始化

| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T7.1 |
| **负责人** | 后端/数据 |

**任务清单**：
- [ ] 编写 `scripts/seed_hot_school_tuition.py`：
  - 目标：985/211/双一流院校（约150所）的专业学费数据
  - 每条数据格式：`{school_id, major_name, tuition_per_year, duration_years, data_source, data_year}`
- [ ] 按院校×专业维度插入：
  - 公办本科常见专业：4500-6000元/年
  - 计算机/电子信息类：5000-6500元/年
  - 医学类：5000-7000元/年
  - 艺术类：8000-12000元/年
- [ ] 标注数据来源为"各高校2025年招生章程"
- [ ] 冷门院校（非985/211/双一流）不预填，留待首次推荐时异步爬取

**验收标准**：
```sql
SELECT COUNT(DISTINCT school_id) FROM school_tuition;  -- → >= 100所院校
SELECT COUNT(*) FROM school_tuition;                    -- → >= 500条专业学费
```

**为什么需要**：PRD v4.0 §维度8 规定学费采用混合爬取策略——热门院校全量预爬，冷门院校首次推荐时异步爬取。本任务预填热门院校数据避免推荐中出现大量"数据获取中"。

---

### T7.7 · 爬虫数据网关扩展（支持6类数据校验入库）

| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | T7.3, T1.3 |
| **负责人** | 后端 ★ 数据安全 |

**任务清单**：
- [ ] 更新 `POST /internal/crawler/ingest`：根据 `data_type` 路由到对应 staging 处理
- [ ] 为每类数据编写校验规则：
  - admission: min_rank>0, min_score∈[0,750], school_id+province+year去重
  - major: school_id存在, major_name非空, school_id+major_name去重
  - tuition: tuition_per_year>0且<100000, school_id存在
  - employment: employment_rate∈[0,100], graduate_rate∈[0,100]
  - salary: salary_start_max>salary_start_min, salary范围内合理
  - city: city_name非空, location/advantage/development三字段不为纯空格
- [ ] 校验失败→写入 `crawler_error_log`（统一表，增加 `data_type` 字段区分）
- [ ] 校验通过→MERGE INTO 对应目标表（admission_history / school_majors / school_tuition 等）
- [ ] 更新 `check_staging.py` 支持6类数据的批量校验+合并

**验收标准**：
```bash
# 测试各类数据推送
# 合法数据→入库
curl ... -d '{"data_type":"tuition","records":[{...}]}'  # → ingested: 1

# 非法数据→error_log
curl ... -d '{"data_type":"employment","records":[{"employment_rate":150}]}'  
# → ingested: 0, rejected: 1
# 验证 crawler_error_log 中有此条记录
```

**为什么需要**：ARR R2 修复仅覆盖了 admission_history 的数据校验。v4.0 新增5张数据表，每类数据都需要独立的校验规则和入库逻辑。本任务将爬虫网关从单通道扩展为6通道。

---

## Phase 8：v4.0 前端与体验升级 ★ 新增

> **此阶段负责 PRD v4.0 视觉重塑（Bento Grid 暗色主题）和 16 维度卡片渲染。**

### T8.1 · Bento Grid 暗色主题 CSS 系统

| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | T3.1（前端框架已有浅色版） |
| **负责人** | 前端 ★ v4.0 视觉核心 |

**任务清单**：
- [ ] 在 `index.html` `<head>` 中建立完整的暗色 CSS 变量体系（对齐 UI_Spec v4.0 §1.2）：
  ```css
  :root {
    /* 背景 */
    --bg-primary: #0F172A;        /* Slate 900 主背景 */
    --bg-card: #1E293B;           /* Slate 800 卡片 */
    --bg-card-hover: #334155;     /* Slate 700 悬停 */
    --bg-input: #1E293B;          /* 输入框 */
    /* 文字 */
    --text-primary: #F1F5F9;      /* Slate 100 */
    --text-secondary: #94A3B8;    /* Slate 400 */
    --text-muted: #64748B;        /* Slate 500 */
    /* 强调 */
    --color-accent: #818CF8;      /* Indigo 400 — CTA/主按钮 */
    --color-accent-hover: #6366F1;/* Indigo 500 */
    --color-cyan: #22D3EE;        /* Cyan 400 — 数据高亮 */
    /* 标签 */
    --color-985: #F59E0B;         /* Amber 500 */
    --color-211: #818CF8;         /* Indigo 400 */
    --color-double-first: #06B6D4;/* Cyan 600 */
    /* Tier */
    --color-danger: #EF4444;      /* 冲刺 */
    --color-info: #3B82F6;        /* 稳妥 */
    --color-success: #22C55E;     /* 保底 */
    /* UI */
    --border: rgba(148,163,184,0.08);
    --shadow-card: 0 4px 24px rgba(0,0,0,0.3);
    --shadow-glow: 0 2px 8px rgba(129,140,248,0.25);
  }
  ```
- [ ] 全局应用暗色主题到所有页面块：
  - `body` / `.phone-frame` → `background: var(--bg-primary)`
  - `.nav-bar` → `background: rgba(15,23,42,0.92); backdrop-filter: blur(12px)`
  - 所有 `.card` → `background: var(--bg-card); border-radius: 16px; box-shadow: var(--shadow-card)`
  - 所有 `input/select` → `background: var(--bg-input); border: 1px solid var(--border)`
  - CTA 按钮 → `background: var(--color-accent); color: #fff; box-shadow: var(--shadow-glow)`
- [ ] 更新付款墙遮蔽色：从浅色 `#E2E8F0` → 暗色 `#475569`（斜纹对比度增强）
- [ ] 骨架屏 shimmer 动画：`background: linear-gradient(90deg, #334155 0%, #475569 50%, #334155 100%)`
- [ ] 微交互：卡片 hover→上移2px+阴影加深；按钮 hover→缩放1.02+发光增强；标签选中→0.2s过渡

**验收标准**：
- 浏览器打开 index.html → 全局暗色 Slate 900 底色
- 所有卡片 rounded-16px + shadow-card
- CTA 按钮 Indigo 紫 + 发光阴影
- 付款墙遮蔽有足够对比度（直播压缩后仍可辨识）
- 与 UI_Spec v4.0 §1.2 配色完全一致

**为什么需要**：PRD v4.0 全面采用 Bento Grid 暗色设计系统。旧版浅色主题需完整的 CSS 变量替换。适配直播投屏时暗色对眼睛更友好，卡片悬浮感和"精密仪器"秩序感需要圆角+阴影+微交互支撑。

---

### T8.2 · 16维度学校卡片渲染（新维度字段展示）

| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | T8.1, T3.5, T7.4 |
| **负责人** | 前端 ★ v4.0 核心页面 |

**任务清单**：
- [ ] 更新 T3.5 学校卡片渲染逻辑，适配 API 返回的 16 维度新字段：
  - 维度7 **推荐专业**：显示 `recommended_major` + 如有 `major_note:"相近专业"` 显示灰色小字标注
  - 维度8 **学费**：`tuition_per_year` + `tuition_total` + `tuition_fit`（经济友好 💚 标记学费≤5000）
  - 维度11 **就业率**：显示百分比 + 下方小字标注 `employment_source`（数据来源+年份）
  - 维度12 **薪资**：应届起薪 + 3年后薪资，两行显示
  - 维度15 **城市分析**：折叠面板展开显示5个子维度（location/advantage/development/main_business/career_impact）
- [ ] 缺数据维度降级展示：
  - `data_source="pending_crawl"` → 骨架屏占位 + "数据获取中…"文字
  - `data_source="estimated"` → 正常显示但附加灰色 `(估算)` 标记
  - `data_source="database"` → 正常显示
- [ ] 确保不同学校卡片的专业/学费/就业率/薪资/城市分析字段值**确实不同**（不是模板复制）
- [ ] Bento Grid 嵌套布局：16维度以 `grid: repeat(auto-fill, minmax(160px, 1fr))` 排列

**验收标准**：
- 15所学校卡片，每所16维度完整显示
- 不同学校推荐专业不同（有计算机的显示计算机，无的显示"相近专业：信息工程"）
- 不同学校学费不同（公办4500-6000，民办15000-30000）
- 不同学校就业率/薪资不同
- 城市分析折叠面板展开显示5个子维度
- 缺数据维度显示骨架屏

---

### T8.3 · PDF 5种水印 + 封面重设计（扁平商务极简风）

| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | T8.2, T3.6 |
| **负责人** | 前端 ★ v4.0 PDF 核心 |

**任务清单**：
- [ ] PDF 封面重设计（对齐 PRD v4.0 §PDF报告规范）：
  - 整体底色：`#E6F0FF` 浅蓝渐变
  - ① 顶部品牌区：学士帽图标 + "高考志愿规划师" + "AI 智能报考分析系统 - 2026"
  - ② 核心大标题："AI 高考志愿智能规划报告 (2026)"
  - ③ 考生信息卡片：白色底，6字段双栏（报告编号/生成时间/昵称/省份分数/位次/选科调剂）
  - ④ 数据权威性保障卡片：浅蓝底，3条项目符号（数据来源/AI引擎/数据规模）
  - ⑤ 底部：免责文字 + 红色"严禁倒卖"
- [ ] 5种水印完整实现：
  1. **报告编号**（页眉）：`GK` + 时间戳 + 随机码，灰色小字
  2. **防伪声明**（页眉/封面底部）：红色 `#E53935` "防伪 · 严禁转卖"
  3. **斜纹全页水印**：主播手机号后4位 + 报告编号，45°斜角，opacity 8-12%，Canvas 绘制
  4. **考生信息卡片**（封面）：6字段双栏白色卡片
  5. **二维码**（封面右下角）：生成含报告编号+考生信息哈希的二维码（使用 qrcode.js 或 Canvas 手绘）
- [ ] 正文页：延续浅蓝渐变 + 页眉报告编号/防伪声明 + 页脚页码
- [ ] PDF画质：`html2canvas({ scale: 3 })` 保证 300DPI
- [ ] 命名：`志愿报告_[网名]_[报告编号].pdf`

**验收标准**：
- PDF打开封面5区块完整（品牌→大标题→考生信息→数据权威→底部免责）
- 正文每页含报告编号页眉 + 红色防伪声明
- 全页45°斜纹水印可见但不遮挡文字
- 封面右下角二维码可扫码
- 300DPI清晰度（放大不失真）

---

### T8.4 · 报告5大板块结构调整

| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T8.2, T3.5 |
| **负责人** | 前端 |

**任务清单**：
- [ ] 将 T3.5 报告页重构为以5大板块为骨架的 DOM 结构（对齐 PRD v4.0 §页面⑥）：
  - **板块一**：封面基础信息（报告编号+考生摘要+数据权威说明）
  - **板块二**：核心定位分析（分数定位+院校分层规划饼图+调剂提示）
  - **板块三**：分层院校明细（冲/稳/保三色卡片区，每区5张学校卡片）
  - **板块四**：AI个性化填报建议书（6节：成绩定位/梯度策略/调剂风险/经济适配/性格匹配/四大原则）
  - **板块五**：免责声明卡片
- [ ] 板块三特别关注区升级：独立 Bento 卡片，★图标+琥珀色强调，置于板块二饼图上方
- [ ] 底部三按钮保持：📥下载PDF / 👤测下一个 / 🤖直播答疑

**验收标准**：
- 报告页面按5大板块清晰分区
- 特别关注区位于板块二之上、独立卡片
- 板块四 AI建议书6节完整
- 板块五免责声明底部居中

---

### T8.5 · 管理后台暗色主题同步 + 密码管理前端

| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T8.1, T4.1, T7.2 |
| **负责人** | 前端+后端 |

**任务清单**：
- [ ] 将 `admin.html` 同步为暗色主题（复用 T8.1 CSS变量）
- [ ] 密码管理前端：
  - 管理员顶部导航新增"修改密码"入口 → 弹窗（旧密码+新密码+确认）
  - 主播管理列表操作列新增"重置密码"按钮 → 确认弹窗 → 显示新密码明文
- [ ] 调用 `POST /admin/change-password` 和 `POST /admin/streamers/{id}/reset-password`
- [ ] 直播模式适配暗色主题（全屏后仍保持暗色）

**验收标准**：
- admin.html 显示暗色主题
- 管理员可修改自己的密码
- 管理员可重置主播密码并获得新密码明文

---

## Phase 9：v4.0 集成验证 ★ 新增

> **此阶段验证 Phase 7-8 新增功能与 Phase 1-6 已有功能的兼容性和数据真实性。**

### T9.1 · v4.0 全流程回归测试

| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | Phase 7+8 全部 |
| **负责人** | 全员 |

**任务清单**：
- [ ] 端到端回归：登录→填表→推荐→付费解锁→完整报告→PDF下载→下一位
- [ ] 验证暗色主题在所有页面一致（登录/考生信息/意向/分析中/付款墙/报告/管理后台）
- [ ] 验证特别关注区：意向学校0%概率正常展示 + 标注
- [ ] 验证16维度卡片：展开所有15所→每所维度完整→不同学校数据差异化
- [ ] 验证城市分析折叠面板展开/收起
- [ ] 验证 PDF 封面5区块 + 5种水印完整
- [ ] 验证密码管理：主播自助改密码→旧密码失效→新密码登录 / 管理员重置密码
- [ ] 验证 admin.html 暗色主题

**验收标准**：
- 全流程无不一致视觉或功能断点
- 不同考生（换省份/分数/选科/专业意向）→ 推荐结果差异化
- Ctrl+F5 强制刷新后所有页面暗色主题一致

---

### T9.2 · 数据差异化验证

| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T9.1 |
| **负责人** | 后端+前端 |

**任务清单**：
- [ ] 构造3个不同考生场景，对比推荐结果：
  | 考生 | 省份 | 分数 | 选科 | 意向专业 | 意向城市 | 验证重点 |
  |------|------|:---:|------|---------|---------|---------|
  | A | 河南 | 580 | 物理 | 计算机 | 郑州 | 基准线 |
  | B | 河南 | 380 | 物理 | 计算机 | 郑州 | 低分阈值(5%) |
  | C | 广东 | 580 | 物理 | 计算机 | 深圳 | 不同省份差异化 |
- [ ] 验证：A和C推荐学校列表完全不同（不同省份）
- [ ] 验证：同一考生A的15所学校：
  - 推荐专业差异化（不能所有学校都是"计算机科学与技术"）
  - 学费差异化（不能所有学校都是"5000-5500元/年"）
  - 就业率差异化（不能所有学校都是"92-97%"）
  - 薪资差异化（985/211学校高于普通院校）
  - 城市分析差异化（不同城市5个子维度不同）
- [ ] 验证低分考生B仍有15所学校推荐（不返回空数组）
- [ ] 验证数据真实性原则：无全校统一模板填充

**验收标准**：
- 3个考生推荐结果全部不同
- 同一考生的15所学校卡片中推荐专业≥3种不同值
- 同一考生的15所学校卡片中学费≥3种不同值
- 无两所学校所有16维度完全相同的"克隆卡片"

---

### T9.3 · 16维度缺数据降级展示验证

| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T9.1 |
| **负责人** | 前端+后端 |

**任务清单**：
- [ ] 模拟以下缺数据场景并验证前端降级展示：
  | 缺数据维度 | 模拟方式 | 预期前端展示 |
  |-----------|---------|------------|
  | school_majors 无数据 | DELETE FROM school_majors WHERE school_id=X | 显示"数据获取中…"骨架屏 |
  | school_tuition 无数据 | DELETE FROM school_tuition WHERE school_id=X | 显示估算值 + `(估算)` 标记 |
  | school_employment 无数据 | DELETE FROM school_employment WHERE school_id=X | 按专业类型估算 + 无数据来源标注 |
  | school_salary 无数据 | DELETE FROM school_salary WHERE school_id=X | 按城市等级估算 |
  | city_analysis 无数据 | DELETE FROM city_analysis WHERE city_name='郑州' | 显示"郑州（数据获取中…）" |
- [ ] 验证缺数据时自动创建对应的爬虫任务：
  ```sql
  SELECT COUNT(*) FROM school_major_crawl_tasks WHERE status='pending';  -- >0
  SELECT COUNT(*) FROM school_tuition_crawl_tasks WHERE status='pending';  -- >0
  ```
- [ ] 恢复数据后验证推荐返回完整数据

**验收标准**：
- 缺数据维度不显示空白/null/undefined
- 骨架屏和数据获取中文字清晰可见
- data_source 标记正确（pending_crawl / estimated）
- 对应爬虫任务表有 pending 记录

---

## 任务依赖图

```
Phase 1 (基础设施)
  T1.1 ──┬── T1.2 ── T1.3
         │
         └── T1.4
               │
Phase 2 (核心后端)         Phase 3 (前端)
  T2.1 ← T1.4              T3.1 (独立)
   ├── T2.2                 ├── T3.2
   ├── T2.3                  │    └── T3.3
   │    └── T2.4             │         └── T3.4 ← [T2.5]
   │         └── T2.5        │              └── T3.5 ← [T2.6]
   │              └── T2.6 ← [T7.1]          ├── T3.6
   ├── T2.7                  │              ├── T3.7
   └── T2.8                  │              └── T3.8
                              │
Phase 4 (管理与交易)          │
  T4.1 ← T2.1               │
   └── T4.2                  │
        ├── T4.3             │
        ├── T4.4             │
        └── T4.5             │
                              │
Phase 5 (集成部署)            │
  T5.1 ← Phase 2+3 ──────────┘
   ├── T5.2 / T5.3 / T5.4 / T5.5
   └── T5.6
        │
Phase 6 (上线加固)
  T6.1~T6.4 ← T5.6
        │
        │   ★ v4.0 新增阶段 ★
        │
Phase 7 (v4.0 数据层升级)
  T7.1 ──┬── T7.4 ← [T2.5]   ← 推荐引擎适配新表
         ├── T7.5             ← 专业映射预置
         └── T7.6             ← 学费预置
  T7.2 ← [T4.1]               ← 密码管理API
  T7.3 ← [T1.3]               ← 6类爬虫表
       └── T7.7               ← 爬虫网关扩展

Phase 8 (v4.0 前端升级)
  T8.1 ← [T3.1]               ← 暗色CSS
   ├── T8.2 ← [T3.5,T7.4]    ← 16维度卡片
   │    ├── T8.3 ← [T3.6]    ← PDF重设计
   │    └── T8.4              ← 5大板块
   └── T8.5 ← [T4.1,T7.2]    ← 管理后台暗色+密码

Phase 9 (验证)
  T9.1 ← Phase 7+8 全部
   ├── T9.2
   └── T9.3
```

```
图例：
  [T2.5] = 跨 Phase 依赖（前置任务在另一个 Phase 中）
  ──     = 同 Phase 串行依赖
  ├──    = 兄弟任务（可并行）
```

---

## 关键路径（最短交付时间）

```
Phase 1: T1.1 → T1.4 → 后端入口     (7h)
Phase 2: T2.1 → T2.3 → T2.4 → T2.5 → T2.6  (17h, 推荐引擎)
Phase 3: T3.1 → T3.2 → T3.3 → T3.4 → T3.5 → T3.6  (21h, 前端主流程)
                                    ↓
Phase 5: T5.1 → T5.6                  (7h, 联调部署)
                                    ↓
Phase 6: T6.1~T6.4                    (6h, 加固)
                                    ↓
Phase 7: T7.1 → T7.4 → T7.7          (11h, v4.0数据层)
Phase 8: T8.1 → T8.2 → T8.3          (12h, v4.0前端)
                                    ↓
Phase 9: T9.1 → T9.2                  (7h, 验证)
                                    ─────────
                                    最短 ~88h (约11人天)
```

> **并行策略**：Phase 2（后端）和 Phase 3（前端）可完全并行开发。Phase 7（数据层）和 Phase 8（前端升级）可并行。Phase 9 必须在 Phase 7+8 全部完成后串行执行。

---

## 工时汇总

| Phase | 任务数 | 工时 | 可并行 |
|-------|:---:|:---:|:---:|
| Phase 1: 基础设施 | 4 | 14h | 部分 |
| Phase 2: 核心后端 | 8 | 24h | 与Phase 3并行 |
| Phase 3: 前端页面 | 8 | 27h | 与Phase 2并行 |
| Phase 4: 管理与交易 | 5 | 14h | 部分 |
| Phase 5: 集成测试 | 6 | 19h | 部分 |
| Phase 6: 上线加固 | 4 | 10h | 部分 |
| ★ Phase 7: v4.0数据层 | 7 | 22h | 与Phase 8并行 |
| ★ Phase 8: v4.0前端 | 5 | 18h | 与Phase 7并行 |
| ★ Phase 9: v4.0验证 | 3 | 10h | 串行 |
| ★ Phase 10: 数据丰富与运营 | 4 | 8h | 串行 |
| **合计** | **54** | **~166h** | — |

> **按2人团队计算**：Phase 1→6 = 后端约50h + 前端约56h ≈ 可并行约56h ≈ 7人天完成MVP。Phase 7→9 = 约30h ≈ 4人天完成v4.0升级。Phase 10 = 约8h ≈ 1人天完成数据丰富与运营看板。**总计约12人天到完整状态。**

---

## Phase 10：数据丰富与运营看板 ★ 新增

> 目标：补全城市分析与就业薪资真实数据、修复前端字段映射、增加估算标注、添加管理后台爬取进度看板，形成完整的数据运营闭环。

### T10.1 · 城市分析数据种子（54城市）
| 属性 | 内容 |
|------|------|
| **工时** | 1.5h |
| **前置** | T7.1（city_analysis表） |
| **负责人** | 后端 |

**任务清单**：
- [x] 编写 `scripts/seed_city_analysis.py`
- [x] 覆盖4个一线城市（北京/上海/广州/深圳）
- [x] 覆盖约16个新一线城市（成都/杭州/武汉/重庆/西安/南京/郑州/长沙/天津/苏州/合肥/青岛/宁波/无锡/佛山/东莞/泉州/珠海）
- [x] 覆盖约30个二线/三线城市
- [x] 5维数据：location/advantage/development/main_business/city_level
- [x] ON DUPLICATE KEY UPDATE 幂等写入

**验收标准**：54个城市，`python scripts/seed_city_analysis.py` 无报错。

---

### T10.2 · 就业率与薪资数据种子（~90院校）
| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | T7.1（school_employment/school_salary表） |
| **负责人** | 后端 |

**任务清单**：
- [x] 编写 `scripts/seed_employment_salary.py`
- [x] 就业率数据：~90所985/211/双一流院校（employment_rate/graduate_rate）
- [x] 薪资数据：~80条（校均 + 计算机/医学/金融专业专项薪资）
- [x] 薪资范围覆盖应届/3年（salary_start/salary_3yr）
- [x] school_name → school_id 映射查询
- [x] ON DUPLICATE KEY UPDATE 幂等写入

**验收标准**：`python scripts/seed_employment_salary.py` 无报错，缺失院校打印跳过日志。

---

### T10.3 · 前端估算标注与城市字段修复
| 属性 | 内容 |
|------|------|
| **工时** | 1.5h |
| **前置** | T8.2（renderSchoolCard），T7.4（aggregate_16_dimensions） |
| **负责人** | 前端+后端 |

**任务清单**：
- [x] **后端**：`recommendation.py` 中 city_analysis 返回字段映射修复：`development` → `disadvantage`，`main_business` → `job_market`，新增 `livability` 合成字段
- [x] **前端**：`renderSchoolCard()` 学费行增加 `dim.tuition_data_quality === 'estimated'` 判断，展示 `<span class="est-badge">估算</span>`
- [x] **前端**：薪资行增加 `dim.salary_data_quality === 'estimated'` 判断，展示估算标注
- [x] **CSS**：新增 `.est-badge` 样式（灰色边框小标签）

**验收标准**：真实数据时城市分析5维全显示；估算数据时学费/薪资行出现灰色"估算"标注。

---

### T10.4 · 管理后台爬取进度看板
| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | T7.1（6类crawl_tasks表），T4.1（admin认证） |
| **负责人** | 后端+前端 |

**任务清单**：
- [x] **后端**：`GET /admin/crawl/progress`：查询6类爬取任务表（admission/major/tuition/employment/salary/city）的状态分布（pending/running/done/failed）
- [x] **后端**：`POST /admin/crawl/retry`：将指定类型的 failed 且 retry_count < max_retry 任务重置为 pending
- [x] **前端**：admin.html 新增"数据爬取"Tab
- [x] **前端**：6张爬取进度卡片（进度条 + 4态统计），失败任务显示"重试"按钮
- [x] **前端**：使用 DOM createElement 构建（非 innerHTML，通过安全校验）

**验收标准**：进度看板正确显示6类任务状态；"重试"按钮点击后自动刷新；表不存在时显示"表不存在"提示而不报错。

---

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-06-16 | 初始任务拆分：35任务6Phase~122h（对齐Architecture v1.2） |
| v2.0 | 2026-06-17 | 对齐 Architecture v2.0 / PRD v4.0 新增：Phase 7（数据层升级 7任务22h）+ Phase 8（前端升级 5任务18h）+ Phase 9（验证 3任务10h），总计50任务~158h |
| **v2.1** | **2026-06-17** | **★ 新增 Phase 10（数据丰富与运营看板 4任务8h）：T10.1城市种子/T10.2就业薪资种子/T10.3估算标注/T10.4爬取看板；总计54任务~166h** |
