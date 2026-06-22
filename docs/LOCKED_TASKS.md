# LOCKED_TASKS.md — 锁定任务与稳定代码区域

**生成日期**：2026-06-20  
**版本**：v1.0 (初版)  
**用途**：记录哪些功能/行为已锁定，禁止修改或回退；哪些模块稳定，改动需极度谨慎。

> **规则**：本文档列出的所有条目在没有明确 Bug 报告和充分测试验证的情况下，**禁止任何修改、重构或"优化"**。

---

## 一、锁定代码行为（禁止回退）

### L1：登录认证链路

| 编号 | 锁定内容 | 来源 |
|------|---------|------|
| L1-01 | `doLogin()` 必须调用 `fetch('/auth/streamer/login')` DB验证，**禁止**读 localStorage | BUG-001 |
| L1-02 | JWT Token 使用 Bearer 方案，24h 有效期，Redis黑名单注销 | 架构设计 |
| L1-03 | 登录顺序：先验密码正确→再检查 status，status=disabled 返回 403 | TC-06验证通过 |
| L1-04 | 无效/过期 Token 返回 401 `{"detail":"未登录或Token已过期"}` | TC-05验证通过 |

### L2：推荐引擎核心逻辑（Python后端，`api/services/recommendation.py`）

> ⚠️ **修改此模块须事先获得用户审批**（见本文末"审批要求"节）。

| 编号 | 锁定内容 | 来源 |
|------|---------|------|
| L2-01 | Tier阈值：冲刺 [30%, 50%) / 稳妥 [50%, 85%) / 保底 [85%, 100%]；精英回填下界 15% | v5.10修复+BUG-012+BUG-018 |
| L2-02 | 回填顺序：**冲刺→稳妥→保底**，禁止颠倒（防保底>稳妥倒挂） | BUG-009 |
| L2-03 | 冲刺回填优先级：tier=-1精英院校（最高概率优先）→ 最后才借用tier1/2剩余学校 | BUG-012/BUG-011 |
| L2-04 | 意向学校（`apply_tier_adjustment=False`）：**跳过** tier_mult 和先验混合，直接基于位次展示原始录取概率 | BUG-013 |
| L2-05 | `calc_rank_prob` 年份去重：同年多批（提前批+普通批）保留 min_rank 最高（最易入学）的批次 | BUG-013 |
| L2-06 | `tier_mult` 折减因子：985→0.82，211/双一流→0.88，专科/职业→1.18，民办/独立→1.10 | BUG-001 |
| L2-07 | 先验混合比例：90% 数据驱动 + 10% 先验；意向学校不使用先验 | BUG-001/BUG-013 |
| L2-08 | `is_intended_city` 学校**不豁免**质量过滤（仅 `is_intended` 明确意向校豁免） | BUG-008 |
| L2-09 | 冲刺档 globe_expanded（全国扩展）学校上限 2 所 | BUG-002 |
| L2-10 | `_is_vocational` 须包含"技术学院"关键词，985/211/双一流豁免职业院校判定 | v5.13修复 |
| L2-11 | 省会映射（`_PROVINCE_CAPITAL`）：省份名回退省会城市，禁止直接用省份名作城市 | BUG-010 |
| L2-12 | 缓存键须包含 personality 和 economic_level 的**完整值**，不得使用排序值 | BUG-005 |

### L3：付费墙与报告

| 编号 | 锁定内容 | 来源 |
|------|---------|------|
| L3-01 | 付费墙着色按 `s.tier`（实际tier），**禁止**按位置索引 `i<3` | BUG-010 |
| L3-02 | 饼图/报告摘要/PDF分层标签必须用预计算 `_tierTotals`，**禁止**硬编码"5所" | BUG-011 |
| L3-03 | `buildPDFWrap` 函数内**必须独立计算** `_tierTotals`，不可引用 `renderReport` 局部变量 | BUG-012 |

### L4：扣费系统

| 编号 | 锁定内容 | 来源 |
|------|---------|------|
| L4-01 | 扣费必须调用 `POST /auth/deduct` 后端端点，**禁止**仅前端本地扣减 | BUG-002 |
| L4-02 | 前端乐观更新 + API失败回滚机制必须保留 | BUG-002 |
| L4-03 | 后端扣费使用 `SELECT FOR UPDATE` 行锁 + 幂等key + Redis分布式锁+DB降级 | 架构设计 |
| L4-04 | 余额不足返回 400，错误信息含"次数不足"语义 | TC-04验证通过 |
| L4-05 | Redis宕机期间扣费仍成功（降级为DB直写），health显示 `degraded` | TC-08验证通过 |

### L5：一次性链接

| 编号 | 锁定内容 | 来源 |
|------|---------|------|
| L5-01 | `/s/validate` 接口返回字段为 `"valid"`（**不是** `"active"`） | v5.13修复 |
| L5-02 | token消费使用行锁原子操作，防重复消费 | 架构设计 |

### L6：爬虫网关

| 编号 | 锁定内容 | 来源 |
|------|---------|------|
| L6-01 | 仅允许 IP `199.193.126.80` 和 `127.0.0.1` 访问（Nginx层） | T5.4验证通过 |
| L6-02 | `min_score` Field约束 `le=900`（第一层）+ validator `>800` 拒绝（第二层） | TC-09分析 |
| L6-03 | 无内部JWT Token 返回 401 `{"detail":"Missing internal token"}` | TC-09验证 |

# PDF报告模块

状态：PARTIAL_LOCK

## 已锁定

### PDF样式

状态：LOCKED

锁定内容：

- 配色方案
- 字体
- Logo位置
- 页面布局
- 页眉页脚
- 图表样式
- 封面设计

原因：

客户已确认。

禁止修改。

---

### PDF结构

状态：LOCKED

锁定内容：

- 报告章节顺序
- 学校展示顺序
- 专业展示结构
- 风险提示区域

原因：

验收通过。

禁止修改。

---

## 允许修改

### 推荐算法

状态：**REVIEW_REQUIRED**

> 算法已通过多轮测试验证，推荐结果符合预期。后续任何修改须事先获得用户审批。

可讨论优化（须审批后实施）：

- Tier 阈值边界调整
- tier_mult 折减因子数值
- 先验混合比例
- 冲刺回填策略
- 意向学校概率计算方式

禁止未经审批直接修改：

- `TIER_BOOST_MIN` / `TIER_SOLID_MIN` / `TIER_SAFE_MIN`
- `calc_rank_prob` 核心逻辑
- `sort_and_slice` 分层与回填逻辑
- `apply_tier_adjustment` 开关的触发条件

---

### 数据映射

状态：OPEN

允许修改：

- 城市映射
- 省份映射
- 数据清洗逻辑

---

## 二、废弃方案（禁止再次引用）

> 这些方案曾被使用，已被更好方案替代，**任何情况下不得恢复**。

| 编号 | 废弃方案 | 替代方案 |
|------|---------|---------|
| D-01 | 旧版 localStorage 登录 | `fetch('/auth/streamer/login')` + Bearer token |
| D-02 | 模糊城市匹配（`in` / `contains`） | 标准化后严格等值匹配 |
| D-03 | 付费墙位置索引着色（`i<3 ? red`） | 按 `s.tier` 实际tier着色 |
| D-04 | 前台扣费不调后端 | 同步调用 `POST /auth/deduct` 端点 |
| D-05 | 推荐列表忽略意向学校 | 强制纳入意向学校+置顶 |
| D-06 | 整文件重写部署方式 | 服务器端最小片段替换 |

---

## 三、稳定模块（改动需极度谨慎）

### 🔴 高风险（禁止改动，除非有明确Bug报告 + 用户审批）

| 模块 | 路径 | 原因 |
|------|------|------|
| 推荐引擎 `generate_recommendation()` / `sort_and_slice()` / `calc_rank_prob()` | `api/services/recommendation.py` | 历经12+ Bug修复方才稳定，参数高度耦合，修改须审批 |
| PDF生成 `buildPDFWrap()` | `frontend/index.html` | 水印/页码/QR码/_tierTotals独立计算，多处紧耦合 |
| 扣费原子逻辑 | `api/routers/auth.py` | SELECT FOR UPDATE + 幂等 + Redis锁，任何简化都可能造成重复扣费 |
| JWT认证中间件 | `api/deps.py` | 黑名单 + 过期校验链路，修改可能造成安全漏洞 |

### 🟡 中风险（需测试验证后才可修改）

| 模块 | 路径 | 注意事项 |
|------|------|---------|
| `calcRankProb()` | `index.html` | 6档离散值已经过大量测试，改动需重新测试所有边界分数段 |
| Tier分层逻辑 | `index.html` | 30/50/85阈值已修正，修改需重验TC-01场景 |
| `_is_vocational()` | `index.html` | 精英院校豁免逻辑与职业院校关键词配对，需同步测试 |
| 推荐缓存键生成 | `api/recommendation.py` | Redis L1/L2缓存，改动可能造成缓存污染 |
| 爬虫数据校验schema | `api/crawler.py` | 双层校验（Field+validator），修改影响6类数据入库 |

### 🟢 低风险（可修改，建议回归测试）

| 模块 | 描述 |
|------|------|
| 后端API路由 | 新增端点安全，修改现有端点注意向后兼容 |
| 管理后台 `admin.html` | Vue3 SPA，与核心业务逻辑隔离 |
| 学生自助页 `s.html` | 除一次性链接验证字段（L5-01）外，其余可修改 |
| Nginx配置 | 注意保留IP白名单（L6-01）和API no-cache headers |
| 数据库Schema | 新增表/索引安全；修改现有表字段需确认无隐式依赖 |
| broadcast_scripts | 独立功能，无核心业务依赖 |

---

## 四、Nginx硬约束

| 约束 | 内容 |
|------|------|
| IP白名单 | `199.193.126.80`（爬虫服务器）必须在 `/internal/crawler/` 路由的 allow 列表 |
| API no-cache | 所有 `/api/` 路径必须设置 `Cache-Control: no-cache, no-store` |
| 安全 headers | X-Frame-Options、X-Content-Type-Options、X-XSS-Protection 必须保留 |
| CORS | `allow_origins` **禁止**使用通配符 `"*"`（v5.1修复，已限定具体域名） |

---

## 五、数据库约束

| 约束 | 内容 |
|------|------|
| 幂等键 | `deduction_logs.idempotency_key` UNIQUE 约束不可删除 |
| 软删除 | `streamer_accounts.status` 使用 enum('active','disabled')，禁止物理删除主播记录 |
| 外键 | `crawler_staging` 无 school_id FK（故意设计，避免ingest时外键阻塞） |

---

---

## 六、审批要求

以下操作**必须先描述意图、获得用户明确同意后**才能执行：

1. 修改 `api/services/recommendation.py` 中任何 Tier 阈值、折减因子、先验混合比例
2. 改变 `sort_and_slice` 的回填顺序或策略
3. 修改 `calc_rank_prob` 中的概率计算公式或年份窗口
4. 更改意向学校是否跳过 tier_mult/先验混合的逻辑
5. 调整质量过滤（`is_intended` vs `is_intended_city` 豁免规则）

**审批流程**：在对话中说明"要改什么、为什么改、预期效果"，等待用户回复同意后再动代码。

---

*本文档最后更新：2026-06-21，基于 BugReport.md / Progress.md / PROJECT_STATUS.md 整理。*
