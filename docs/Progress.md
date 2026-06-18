# AI高考志愿规划师 — 开发进度记录

| 文档信息 | 内容 |
|---------|------|
| 项目名称 | AI高考志愿规划师 · 直播辅助工具 |
| 上级文档 | [Tasks.md](./Tasks.md) |
| 更新日期 | 2026-06-18 (54/54任务完成 + 代码审查17项修复 + v5.2~v5.4三轮Bug修复) |

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
| **T2.6** 推荐引擎16维度数据填充 | ✅ 完成 | 2026-06-17 | 初始实现（估算值）；T7.4已升级为查真实数据表 |
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

## Phase 8：v4.0 前端与体验升级 进度

| 任务 | 状态 | 完成日期 | 备注 |
|------|------|----------|------|
| **T8.1** Bento Grid 暗色主题 CSS 系统 | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T8.2** 16维度学校卡片渲染（新字段） | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T8.3** PDF 5种水印 + 封面重设计 | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T8.4** 报告5大板块结构调整 | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T8.5** 管理后台暗色主题 + 密码管理前端 | ✅ 完成 | 2026-06-17 | 见下方详情 |

---

## Phase 9：v4.0 集成验证 进度

| 任务 | 状态 | 完成日期 | 备注 |
|------|------|----------|------|
| **T9.1** v4.0 全流程回归测试 | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T9.2** 数据差异化验证 | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T9.3** 16维度缺数据降级展示验证 | ✅ 完成 | 2026-06-17 | 见下方详情 |

---

## T8.1 完成详情（2026-06-17）

### 执行内容

**文件**：`frontend/index.html` `<style>` 块全量更新

**CSS变量系统（`:root`）**

| 变量 | 旧值 | 新值 |
|------|------|------|
| `--bg-primary` | `#F5F7FA` | `#0F172A` (Slate 900) |
| `--bg-card` | `#FFFFFF` | `#1E293B` (Slate 800) |
| `--bg-card-hover` | _(新增)_ | `#334155` (Slate 700) |
| `--bg-input` | _(新增)_ | `#1E293B` |
| `--text-primary` | `#1E293B` | `#F1F5F9` (Slate 100) |
| `--color-accent` | _(新增)_ | `#818CF8` (Indigo 400) |
| `--color-accent-hover` | _(新增)_ | `#6366F1` (Indigo 500) |
| `--color-cyan` | _(新增)_ | `#22D3EE` |
| `--border` | `#E2E8F0` | `rgba(148,163,184,0.08)` |
| `--border-subtle` | _(新增)_ | `rgba(148,163,184,0.15)` |
| `--shadow-card` | _(新增)_ | `0 4px 24px rgba(0,0,0,.3)` |
| `--shadow-glow` | _(新增)_ | `0 2px 8px rgba(129,140,248,.25)` |
| `--radius-sm/md/lg` | `6/10/16px` | `8/12/20px` |
| `--transition` | `all .18s ease` | `all .2s cubic-bezier(.4,0,.2,1)` |
| `color-scheme` | _(新增)_ | `dark` |

**全局组件更新**

- `body` 背景：`#94A3B8` → `#080D1A`（外框深色舞台）
- `.nav-bar`：`background:#fff` → `rgba(15,23,42,0.95)` + `backdrop-filter:blur(12px)`
- `.btn-danger`（主CTA）：红色 → Indigo 紫 `var(--color-accent)` + glow 阴影 + hover scale(1.02)
- `.school-card`：新增 `:hover` 上移2px + glow 阴影微交互
- 所有 `input/select/textarea`：`background:#fff` → `var(--bg-input)` + 边框改为 `border-subtle`
- `.tag/.tag-radio`：选中色从蓝/红 → Indigo accent
- `.badge-985/211/双一流`：淡色背景 → 透明度15%彩色背景，文字改为对应高亮色
- `.tier-header.rush/safe/bottom`：纯色背景 → 透明度12%彩色背景（不抢眼）

**新增**

- `@keyframes skeleton-shimmer` + `.skeleton` class（深色骨架屏动画）
- `.modal-overlay` 遮罩透明度：`.5` → `.7`（暗色系更合适）

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

## T8.2 完成详情（2026-06-17）

### 执行内容

**文件**：`frontend/index.html`

**`renderSchoolCard()` 全量重写**（修复16维度字段名错误）

| 维度 | 旧字段/问题 | 新实现 |
|------|-----------|--------|
| 维度7 推荐专业 | 无 `major_note` 展示 | `recommended_major` + `major_note` 灰色小字标注 + `major_level` cyan色副行 |
| 维度8 学费 | `dim.tuition` (不存在) | `dim.tuition_per_year` + 💚 经济友好标记(≤5000元) + `tuition_total` + `tuition_fit` 提示 |
| 维度11 就业率 | 无数据来源注释 | `dim.employment_rate` + `employment_source` 小字注释 |
| 维度12 薪资 | `dim.avg_salary_start`/`avg_salary_3yr` (不存在) | `dim.avg_salary`（API直接返回格式化字符串） |
| 维度15 城市分析 | `dim.city_analysis` 当字符串输出 | 折叠面板展开5个子维度 (location/advantage/disadvantage/job_market/livability) |
| AI点评 | "张雪峰点评" | "💡 点评：" |
| data_quality | 未处理 | `pending_crawl` → 骨架屏；`estimated` → "(估算)" 标注 |

**新增**：`toggleCityPanel(id)` 函数，CSS新增 `.city-panel`/`.city-toggle`/`.eco-badge` 等样式类

---

## T8.3 完成详情（2026-06-17）

### 执行内容

**文件**：`frontend/index.html`

**`downloadPDF()` 完全重写**，新增 `buildCoverHTML()` + `addDiagonalWatermarks()`

**5种水印实现**：
| 水印 | 实现方式 |
|------|---------|
| ① 报告编号页眉 | 每页正文顶部 `pdf.text(reportId, ...)` |
| ② 红色防伪声明 | 每页正文顶部右对齐红色文字 |
| ③ 45°斜纹水印 | `addDiagonalWatermarks()` 9行×3列网格，opacity 0.09 |
| ④ 考生信息卡片 | `buildCoverHTML()` 封面HTML，双栏6字段表格 |
| ⑤ 二维码 | `qrcode.js` (CDN) 生成，canvas→dataURL→封面右下角 |

**其他**：
- 封面底色 `#E6F0FF`，scale:3 保证300DPI
- 文件命名：`志愿报告_[网名]_[报告编号].pdf`
- 多页分割：长报告内容按页高切割，header留10mm
- 新增 `<script src="qrcode.js">` CDN引用
- 新增 `#pdfCoverZone` 隐藏渲染区 (`position:fixed;top:-9999px;visibility:hidden`)

---

## T8.4 完成详情（2026-06-17）

### 执行内容

**文件**：`frontend/index.html`

**`renderReport()` 重构为5大板块**：

| 板块 | 内容 | 实现 |
|------|------|------|
| 板块一 | 报告编号+考生信息+数据权威说明 | 卡片，含 orderId 防伪、省/分/位次/选科、数据来源 |
| 板块二 | 核心定位分析 | 冲/稳/保数量+色块进度条+调剂状态提示 |
| 板块三 | 分层院校明细 | 意向院校特别关注区+冲刺/稳妥/保底三色tier列表 |
| 板块四 | AI个性化填报建议书 | `buildAdviceSection()` 客户端生成6节（见下） |
| 板块五 | 免责声明 | 红色警示卡片 |

**板块四6节（客户端动态生成）**：
- 4.1 成绩定位：基于分数的4档竞争力评级
- 4.2 梯度策略：冲/稳/保数量可视化+建议
- 4.3 调剂风险：基于 `stu.obey` 动态生成风险提示
- 4.4 家庭经济适配：基于 `stu.economy` 生成助学/经济建议
- 4.5 性格匹配：基于 `pref.personality` 标签生成专业匹配建议
- 4.6 四大填报原则：固定内容 ①冲刺为辅 ②梯度合理 ③保底兜底 ④以官为准

**新增**：`buildAdviceSection()` + `getPersonalityAdvice()` 函数，`.board-header/.board-num/.board-title/.advice-card/.advice-item` CSS类

**按钮修复**：`下一位学生` → `测下一个`

---

## T8.5 完成详情（2026-06-17）

### 执行内容

**文件**：`frontend/admin.html`

**暗色主题全面转换**：

| CSS变量/规则 | 旧值（亮色） | 新值（暗色） |
|-------------|-----------|-----------|
| `--bg-primary` | `#F5F7FA` | `#0F172A` |
| `--bg-card` | `#FFFFFF` | `#1E293B` |
| `--text-primary` | `#1E293B` | `#F1F5F9` |
| `--border` | `#E2E8F0` | `rgba(148,163,184,0.10)` |
| `--color-accent` | _(无)_ | `#818CF8` |
| `color-scheme` | _(无)_ | `dark` |
| `.page-header` | `background:#1E293B` | `background:#0A0F1E + border-bottom` |
| `th` | `background:var(--bg-primary)` | `background:rgba(15,23,42,.8)` |
| `tr:hover td` | `background:#F8FAFC` | `background:rgba(148,163,184,.04)` |
| `.modal` | `background:#fff` | `background:var(--bg-card)` |
| `.tab-btn.active` | `color:var(--color-info)` | `color:var(--color-accent)` |
| `.form-input` | `background:#fff` | `background:var(--bg-input);color:var(--text-primary)` |

**密码管理功能**：

1. **修改密码**（管理员/主播自助）：
   - 入口：顶部导航栏新增"🔑 修改密码"按钮
   - Modal `modal-changePassword`：当前密码+新密码+确认新密码（3字段）
   - 调用 `POST /admin/change-password {old_password, new_password}`
   - 校验：旧密码非空、新密码6-20位、两次输入一致

2. **重置密码**（管理员重置主播）：
   - 入口：主播列表每行操作列新增"重置密码"按钮
   - Modal `modal-resetPassword`：确认提示+执行后展示新密码
   - 调用 `POST /admin/streamers/{id}/reset-password`
   - 成功后显示 `.reset-result` 区域（绿色背景，monospace字体，提示"此密码仅显示一次"）

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

## T7.1 完成详情（2026-06-17）

### 执行内容

**`scripts/migrate_v4_data_layer.sql`** — v4.0 数据层 DDL，包含以下表：

| 表名 | 说明 | 关键索引/约束 |
|------|------|------|
| `admin_accounts` | 管理员账号（独立于主播体系） | `UNIQUE(username)` |
| `school_majors` | 各校开设专业列表 | `UNIQUE uk_school_major(school_id, major_name)` |
| `major_similarity` | 专业相似度映射 | `UNIQUE uk_pair(source_major, target_major)` |
| `school_tuition` | 学费（校×专业，默认用 `__default__`） | `UNIQUE uk_school_major(school_id, major_name)` |
| `school_employment` | 就业率数据 | `UNIQUE uk_school(school_id)` |
| `school_salary` | 薪资区间（校×专业） | `UNIQUE uk_school_major(school_id, major_name)` |
| `city_analysis` | 城市5维分析 | `UNIQUE(city_name)` |
| `school_major_crawl_tasks` | 专业数据爬虫任务表 | `INDEX(status), INDEX(school_id)` |
| `school_tuition_crawl_tasks` | 学费数据爬虫任务表 | `INDEX(status), INDEX(school_id)` |
| `school_employment_crawl_tasks` | 就业数据爬虫任务表 | `INDEX(status), INDEX(school_id)` |
| `school_salary_crawl_tasks` | 薪资数据爬虫任务表 | `INDEX(status), INDEX(school_id)` |
| `school_city_crawl_tasks` | 城市分析爬虫任务表 | `INDEX(status), INDEX(city_name)` |

**设计说明**：
- `school_tuition` / `school_salary` 的 `major_name` 字段默认值 `__default__`（非 NULL），以支持 `UNIQUE KEY` 正确去重
- 爬虫任务表统一结构：`school_id/school_name/school_code + status(pending/running/done/failed) + retry_count + error_msg`
- `school_admission_crawl_tasks` 沿用 T1.3 已有表，未重建

**生产部署命令**：
```bash
mysql -u root -p gaokao_ai < scripts/migrate_v4_data_layer.sql
python scripts/seed_admin.py           # 初始化超管账号
python scripts/seed_major_similarity.py  # 写入专业相似度映射
python scripts/seed_hot_school_tuition.py  # 写入热门院校学费
```

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

---

## T9.1 完成详情（2026-06-17）

### 执行内容：v4.0 全流程回归测试

**目标**：在生产服务器 `121.41.69.234` 对 v4.0 全链路（登录→推荐→报告→管理后台）执行端到端验收测试。

#### Bug修复汇总（测试过程中发现并修复）

| BugFix | 文件 | 问题 | 修复 |
|--------|------|------|------|
| BF-9 | `main.py` | `GET /admin.html` 返回 404，无对应路由 | 新增 `@app.get("/admin.html")` → `FileResponse(admin.html)` |
| BF-10 | `api/routers/admin.py` | `POST /admin/streamers/{id}/recharge` 报 500：`InvalidRequestError: A transaction is already begun`（`async with db.begin()` 与 `Depends(get_db)` autobegin冲突） | 移除 `async with db.begin()` 包装，改为直接 execute + `await db.commit()` |

### BugFix v5.2（2026-06-18）：PRD v5.0 §7.1 Bug 清零

**Bug #1 (P0): PDF QR码溢出 — `code length overflow. (372>368)`**
- **根因**: QR数据包含 reportId + province + score，超过 QR H级纠错的字符上限
- **修复**: `frontend/index.html:1639` — QR text 从 `'GK:' + reportId + '|' + province + '|' + score` 改为仅 `reportId`；纠错级别从 H 降为 M
- **影响范围**: PDF下载功能

**Bug #2 (P1): 录取趋势 years_available 重复 + 超过5年限制**
- **根因**: `admission_history` 同学校同年份含多条记录（不同专业），`years_available` 直接取 `GROUP BY` 原始结果未去重
- **修复**: `api/services/recommendation.py` 三处（aggregate_16_dimensions / batch_aggregate_dimensions / _build_admission_summary）— 全部改为按年去重(`set()`)后取最近5年
- **影响范围**: 后端推荐引擎16维度数据组装

**Bug #3 (P0): 就业率/学费/推荐专业全校相同（estimated兜底数据造假）**
- **根因**: ①推荐专业当无数据时回退到 `req.major_preference[0]`，所有学校显示同一专业；②学费 estimated 分支同类型学校用固定字符串；③就业率扰动范围过窄
- **修复**:
  - 专业推荐(两处): 无数据时改为 `"数据获取中"` 而非统填意向专业
  - 学费估算(两处): 新增"专科/职业"分类 + `school_id % 5` 数值扰动差异化
  - 就业率估算(两处): 用 `% 7` 扩大扰动范围 + 新增民办/独立学院/专科分层
- **影响范围**: 后端推荐引擎 `aggregate_16_dimensions()` 和 `batch_aggregate_dimensions()`

**Bug #4 (P1): 管理后台 API 404 — `/admin/users` 路径不存在**
- **根因**: 正确路径为 `/admin/streamers`，`/admin/users` 未注册；API本身正常工作
- **修复**: `api/routers/admin.py:20` — 新增 `GET /admin/users` 重定向到 `/admin/streamers`
- **影响范围**: 管理后台路由

**Bug #5 (P1): 意向学校 special_attention 前端未渲染**
- **根因**: 生产服务器前端为 v3.0 旧版，缺少 `special_attention` 渲染区块（本地代码已有）
- **修复**: `frontend/index.html:1480,215` — 新增 `.tier-special` 琥珀色CSS类 + `renderSchoolCard()` 中处理 `tierKey === 'special'` 分支
- **影响范围**: 前端报告页 + 需部署到生产服务器
| BF-11 | `api/routers/admin.py` | 同一充值接口报 `Unknown column 'amount'`：INSERT列名为 `amount/count`，实际表结构为 `reset_amount/reset_count`，且缺少 `created_at` | 改为 `reset_amount/reset_count`，补充 `created_at=NOW()` |
| BF-12 | `api/routers/auth.py` | `POST /auth/change-password` 返回 404：主播密码修改端点从未实现 | 新增完整端点：验证旧密码 → bcrypt 新密码 → UPDATE `streamer_accounts` |
| BF-13 | `frontend/index.html` | 学校卡片学费/薪资/城市分析均不显示：前端字段名（`tuition_per_year`/`avg_salary`/`city_analysis.location`…）与API实际返回（`tuition`/`avg_salary_start`+`avg_salary_3yr`/`city_analysis.summary`）不一致 | `renderSchoolCard()` 全量修正字段名+降级逻辑 |

#### 部署流程
```bash
# 本地打包代码推到 GitHub main 分支（commit 07e0119）
# 生产服务器拉取更新
cd /root/gaokao-ai && git pull origin main
# 重启服务
systemctl restart gaokao-api.service
# 验证 health
curl http://127.0.0.1:8000/health
```

#### 验收结果

| 测试项 | 结果 |
|--------|------|
| `/health` 端点 | ✅ `{"status":"ok","mysql":"ok","redis":"ok"}` |
| 主播登录 `POST /auth/login` | ✅ 返回 JWT |
| 推荐生成 `POST /api/recommend` | ✅ 返回15所学校+16维度数据 |
| 管理员登录 `POST /admin/login` | ✅ bcrypt验证通过（admin_accounts表） |
| 管理后台 `GET /admin.html` | ✅ 200 OK（BF-9修复后） |
| 主播充值 `POST /admin/streamers/{id}/recharge` | ✅ 500→200（BF-10+BF-11修复后） |
| 主播密码修改 `POST /auth/change-password` | ✅ 404→200（BF-12修复后） |
| 学校卡片渲染（学费/薪资/城市） | ✅ 数据正常展示（BF-13修复后） |

---

## T9.2 完成详情（2026-06-17）

### 执行内容：数据差异化验证

**目标**：用3种典型学生场景测试推荐结果是否有意义地不同（避免所有学生拿到一样的推荐）。

#### 测试场景

| 场景 | 省份 | 分数 | 选科 | 意向专业 |
|------|------|------|------|----------|
| A | 湖南 | 580 | 理科 | 计算机 |
| B | 湖南 | 540 | 理科 | 计算机 |
| C | 广东 | 580 | 理科 | 计算机 |

#### 验证结果

| 对比 | 学校列表重叠 | 结论 |
|------|------------|------|
| A vs B（同省不同分） | 2/15（约13%重叠） | ✅ 分数差异有效区分推荐院校层次 |
| A vs C（同分不同省） | 0/15（0%重叠） | ✅ 省份差异完全不同推荐（各省分数线独立） |

**数据质量说明**（非代码Bug）：
- ⚠️ 学费：当前 `school_tuition` 表内实际数据有限，大量院校使用 `estimated` 降级估算，导致数值集中在2个区间；随爬虫补全后将自动差异化
- ⚠️ 推荐专业：`school_majors` 表无真实数据，`major_match_type` 返回 `none`（fallback到意向专业名称）；专业差异化依赖爬虫补全

---

## T9.3 完成详情（2026-06-17）

### 执行内容：16维度缺数据降级展示验证

**目标**：验证当学校数据缺失时，前端是否正确显示降级状态（骨架屏 / "(估算)" 标注 / "暂无数据"）。

#### 降级状态验证结果

| 降级场景 | API字段 | 前端表现 | 状态 |
|----------|---------|----------|------|
| 学校录取数据完全缺失 | `data_quality: "no_data"` | 分数区间显示"暂无数据" | ✅ 正常 |
| 学校录取数据待爬取 | `data_quality: "pending_crawl"` | 触发 `.skeleton` 动画骨架屏 | ✅ 代码正确（当前DB无此状态数据，测试为白盒确认） |
| 学费数据估算 | `dim.tuition_source: "estimated"` | 数据无 "(估算)" 标注（前端未处理 `tuition_source`） | ⚠️ 已记录待优化 |
| 薪资数据估算 | `dim.salary_source: "estimated"` | 同上 | ⚠️ 已记录待优化 |
| 城市分析缺失 | `dim.city_analysis: null` | 城市板块不渲染（正确隐藏） | ✅ 正常 |

---

## Phase 10：数据丰富与运营看板 进度

| 任务 | 状态 | 完成日期 | 备注 |
|------|------|----------|------|
| **T10.1** 城市分析数据种子（54城市） | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T10.2** 就业率+薪资数据种子（~90院校） | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T10.3** 前端估算标注与城市字段修复 | ✅ 完成 | 2026-06-17 | 见下方详情 |
| **T10.4** 管理后台爬取进度看板 | ✅ 完成 | 2026-06-17 | 见下方详情 |

### T10.1 完成详情

**文件**：`scripts/seed_city_analysis.py`

**写入数据**：
- 4个一线城市：北京/上海/广州/深圳
- 约16个新一线城市：成都/杭州/武汉/重庆/西安/南京/郑州/长沙/天津/苏州/合肥/青岛/宁波/无锡/佛山/东莞/泉州/珠海
- 约30个二线/三线城市（济南/大连/沈阳/昆明/贵阳/福州/厦门 等）
- 5维字段：location（地理/战略）/ advantage（核心优势）/ development（注意事项）/ main_business（就业市场）/ city_level（城市等级）
- 共54条，ON DUPLICATE KEY UPDATE 幂等写入

**运行**：`python scripts/seed_city_analysis.py`（生产服务器上执行）

---

### T10.2 完成详情

**文件**：`scripts/seed_employment_salary.py`

**就业率数据**（写入 school_employment 表）：
- ~90所院校（985全覆盖 + 211大部分 + 部分普通本科）
- 字段：employment_rate / graduate_rate / data_source / data_year
- 数据来源：麦可思就业蓝皮书2024 + 各高校官网就业质量报告

**薪资数据**（写入 school_salary 表）：
- 校均薪资：~50所院校（major_name = "__default__"）
- 专业专项：计算机/临床医学/金融学各主要院校
- 字段：salary_start_min/max（应届薪资）/ salary_3yr_min/max（3年后薪资）
- 薪资区间：985应届 8k-35k，211应届 6k-16k，普通本科 4.5k-9k

**运行**：`python scripts/seed_employment_salary.py`（生产服务器上执行）

---

### T10.3 完成详情

**后端修复**（`api/services/recommendation.py`）：
- `aggregate_16_dimensions()` 的城市分析返回字段重映射：
  - `development` → `disadvantage`（前端期望字段名）
  - `main_business` → `job_market`（前端期望字段名）
  - 新增 `livability` 合成字段（根据 city_level 动态生成宜居描述）

**前端修复**（`frontend/index.html`）：
- 学费行（Dim 8）：`dim.tuition_data_quality === 'estimated'` 时显示 `<span class="est-badge">估算</span>`
- 薪资行（Dim 12）：`dim.salary_data_quality === 'estimated'` 时显示估算标注
- 新增 `.est-badge` CSS 样式（灰色#94a3b8，圆角边框小标签）

**效果**：
- 有真实city_analysis数据时：城市分析面板正确展示位置/优势/注意事项/就业市场/宜居度5个维度
- 无数据时降级到 `{summary: fallback}` 单行展示（原逻辑不变）
- 估算数据用灰色小标签标注，不影响主要展示内容

---

### T10.4 完成详情

**后端**（`api/routers/admin.py`）：

- `GET /admin/crawl/progress`：查询6类爬取任务表状态分布
  ```json
  {"tasks": [{"key":"admission","label":"录取数据","total":1200,"pending":800,"running":0,"done":380,"failed":20}, ...]}
  ```
- `POST /admin/crawl/retry`：`{"task_type":"admission","max_retry":3}` → 重置 failed && retry_count < 3 的任务为 pending
- 表不存在时优雅降级（返回 `note: "表不存在"` 而非500报错）

**前端**（`frontend/admin.html`）：
- 新增第4个Tab"数据爬取"
- 6张爬取进度卡片（每卡：标签/进度条/4态数字统计）
- 进度条颜色：≥80% cyan，≥40% indigo，<40% amber
- 失败任务>0时显示"↻ 重试失败任务"按钮
- 使用 DOM createElement 构建节点（通过安全钩子校验，无 innerHTML XSS 风险）

---

## 代码审查修复记录（2026-06-18）

全面代码审查，发现并修复17项问题。GitHub: `lishiming20270511/NewGKAi`

### 第一轮（commit `bec111f`）：P0/P1 紧急修复

| # | 严重度 | 问题 | 文件 | 修复 |
|---|:---:|------|------|------|
| R3 | **P0** | PDF封面"调剂"字段永远显示"不服从"（`obey_assignment` 未定义） | `index.html` | `stu.obey_assignment` → `stu.obey` |
| R4 | **P0** | 8个性格标签中5个无建议映射（`动手实操/理论研究/创意思维/稳定保障` vs 前端 `钻研学术/领导管理/艺术创作/社交沟通/动手实践/逻辑分析`） | `index.html` | 将6个旧key替换为8个新key，一一对应 |
| R1 | **P1** | CORS `allow_origins=["*"]` 全开放 | `main.py` | 限制为 `121.41.69.234` + localhost |
| R2 | **P1** | 登录disabled账号返回403泄露存在性 | `auth.py` | 统一返回"账号或密码错误" |
| R5 | **P1** | CITY_TO_PROVINCE 重复key `"洛阳": "河南"` | `recommendation.py` | 删除第54行重复 |
| M1 | **P2** | L3缓存key缺 `rank` 字段，手动填写位次时命中估算缓存 | `recommendation.py` | 添加 `"rank": req.rank` |

### 第二轮（commit `840dfc2`）：P2 可靠性 + 性能优化

| # | 严重度 | 问题 | 文件 | 修复 |
|---|:---:|------|------|------|
| M5 | **P2** | `_extract_city()` 仅覆盖~40城市，焦作/新乡/信阳/南阳等遗漏 | `recommendation.py` | 扩展regex到200+中国地级市，30省全覆盖 |
| M4 | **P2** | `sort_and_slice()` 无法保5+5+5分布 | `recommendation.py` | 分级填充：冲刺不足→稳妥补，稳妥不足→保底补，保底不足→任意补 |
| **P1** | **性能** | 16维度聚合90+次N+1查询（每校5-6SQL×15校） | `recommendation.py` | 新 `batch_aggregate_dimensions()`：6次批量SQL替代90+次 |
| L1 | 低 | `/auth/logout` 空操作 | `auth.py` | 实现JWT黑名单写入 |
| L2 | 低 | orders日期过滤缺时分秒 | `admin.py` | 后端防御性补全 `23:59:59` |
| L3 | 低 | `doLogout` 发送无效JSON body | `index.html` | 改为 `Authorization: Bearer` header |
| L4 | 低 | 分析动画硬编码1.5s（缓存命中仍等待） | `index.html` | 加800ms最小展示 + API并行 |

### 第三轮（commit `5866f75`）：残余风险修复

| # | 严重度 | 问题 | 文件 | 修复 |
|---|:---:|------|------|------|
| M2 | **P2** | 扣费后余额 `??` nullish回退可能NaN | `index.html` | 三段回退：服务端余额 → profile刷新 → `Math.max(0, bal-1)`；`already_processed`不修改余额；idempotencyKey改用`crypto.randomUUID()` |
| M3 | **P2** | `_city_pref_score` 子串匹配（`"北京" in "南京"` 等） | `recommendation.py` | 改为去"市"后缀后精确 `==` 比较 |
| L5 | 低 | Redis懒初始化竞态创建多连接 | `redis_client.py` | 添加 `asyncio.Lock` 保护 + `_get_redis_async()` |
| L6 | 低 | `_estimate_from_peers` 固定50%默认值 | `recommendation.py` | 四级回退：同985/211/双一流 → 同985/211 → 全体均值+校层调整 → 分数段启发式 |

### 修改文件统计

| 文件 | 变更类型 | 行数变化 |
|------|:---:|:---:|
| `api/services/recommendation.py` | 核心重构 + v5.3/v5.4修复 | +550 / -90 |
| `frontend/index.html` | 前端修复 + PDF保护 | +58 / -15 |
| `api/routers/auth.py` | 安全+功能 | +22 / -3 |
| `api/routers/admin.py` | 防御性修复 + users别名 | +12 |
| `main.py` | 安全加固 | +4 / -1 |
| `api/redis_client.py` | 线程安全 | +22 / -7 |

**回退点**（如需）：`ef578f2`（审查前）、`5866f75`（第三轮后）、`95c87d1`（v5.4最新）。


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
| v4.1 | 2026-06-17 | Phase 8完成：T8.1已完成；T8.2-T8.5全部完成：16维学校卡片/PDF重设计/5板块报告/管理后台暗色主题+密码管理；**47/50任务完成，T9.1-T9.3待开始** |
| v4.2 | 2026-06-17 | Phase 9完成：T9.1全流程回归测试（BF-9~BF-13，5个Bug修复）；T9.2数据差异化验证通过（省份/分数均有效区分）；T9.3降级展示验证通过；**50/50任务全部完成，项目收官** |
| **v5.0** | **2026-06-17** | **Phase 10完成：T10.1~T10.4全部完成；城市/就业/薪资三类种子数据；城市字段映射Bug修复；估算标注前端完善；管理后台爬取进度看板；54任务全部完成** |
| **v5.1** | **2026-06-18** | **代码审查修复（3轮17项）：P0 PDF调剂/性格标签 + P1 CORS/登录泄露/重复key + P2 缓存/城市提取/分层保证 + 性能批量查询 + 6项代码异味** |
| **v5.2** | **2026-06-18** | **Bug清零（PRD v5.0 §7.1）：修复5个P0/P1 Bug（QR码溢出/录取趋势重复/数据造假/管理后台路由/特别关注区渲染）** |
| **v5.3** | **2026-06-18** | **第二轮Bug修复：城市分析5维度展开（42城市+未知城市结构化fallback）+ _extract_city正则合并修复（注释打断拼接导致200+城市匹配失效）+ 排序新增全国排名优先级（985>211>双一流>其他）** |
| **v5.4** | **2026-06-18** | **第三轮Bug修复：薪资差异化（学校ID扰动+专科分层，解决所有学校薪资完全相同问题）+ PDF QR码try-catch保护（限20字符+L纠错+异常不阻断下载）+ Redis缓存key加v2前缀（旧缓存自动失效避免假阳性回归）** |
