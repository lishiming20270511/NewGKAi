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

### L2：推荐引擎核心逻辑

| 编号 | 锁定内容 | 来源 |
|------|---------|------|
| L2-01 | `calcRankProb` 6档离散值：>5000→95%，2000-5000→80%，0-2000→65%，-2000-0→45%，-5000- -2000→25%，<-5000→8% | Architecture.md |
| L2-02 | Tier阈值：冲刺 [30, 50) / 稳妥 [50, 85) / 保底 [85, 100]（**冲刺上界是50%不是60%**） | v5.10修复，BUG |
| L2-03 | 低概率过滤：非意向学校 rankProb < 30% 必须移除（低分段<400分阈值降至5%） | BUG-006/BUG-013 |
| L2-04 | 意向学校匹配必须是严格精确 `===`，**禁止**模糊匹配/子串匹配 | BUG-005 |
| L2-05 | `_merge_must_diag` 实现为 `diag_recs + recs`，不限数量，强制置顶 | BUG-004 |
| L2-06 | 排序三级优先级：`_intended(★)` → `_intended_city(●)` → rankProb 降序 | BUG-014 |
| L2-07 | 城市→省份映射含60+城市，跨省宽口径查询 | BUG-003 |
| L2-08 | 当 `city` 字段为空时，必须先调 `getCityFromSchoolName()`，再走 `CITY_PROV` 映射 | BUG-015 |
| L2-09 | `SCHOOL_POOL` 构建时：city为空→ `getCityFromSchoolName()` 提取；prov为空→ `CITY_PROV[city]` 映射 | BUG-015 |
| L2-10 | 城市池**不设** rp>=30 概率门槛，标记 `_intended_city` 强制保留 | BUG-013 |
| L2-11 | 空池时必须回退到分数接近度排序（兜底池不可全空） | BUG-013 |
| L2-12 | `_is_vocational` 职业院校检测须包含"技术学院"关键词，精英院校豁免（985/211/TOP100） | v5.13修复 |
| L2-13 | backfill逻辑执行后，**必须**同步更新 `s.tier`，保证前端计数器准确 | v5.13修复 |
| L2-14 | 高分段（高一分一段位次），候选池须过4层：prior不可过高/L4门槛不可屏蔽高校/globe_expanded不过滤/segment兜底存在 | v5.12修复 |

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

状态：OPEN

允许修改：

- rankProb
- tier
- candidate_pool
- city_pool
- 意向学校逻辑
- 排序逻辑

原因：

当前存在严重推荐错误。

允许优化。

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

### 🔴 高风险（禁止改动，除非有明确Bug报告）

| 模块 | 路径 | 原因 |
|------|------|------|
| 推荐引擎主函数 `generateSchools()` | `index.html` | 历次最复杂Bug来源，26个Bug已修复，修改风险极高 |
| PDF生成 `buildPDFWrap()` | `index.html` | 水印/页码/QR码/_tierTotals独立计算，多处紧耦合 |
| 扣费原子逻辑 | `api/auth.py` | SELECT FOR UPDATE + 幂等 + Redis锁，任何简化都可能造成重复扣费 |
| JWT认证中间件 | `api/auth.py` | 黑名单 + 过期校验链路，修改可能造成安全漏洞 |

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

*本文档由 Claude Code 于 2026-06-20 基于 PROJECT_CONTEXT.md / BUG_CLOSED.md / docs/Progress.md / docs/Architecture.md 整理生成。*
