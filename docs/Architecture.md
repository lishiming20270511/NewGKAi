# AI高考志愿规划师 — 技术架构文档

| 文档信息 | 内容 |
|---------|------|
| 产品名称 | AI高考志愿规划师 · 直播辅助工具 |
| 架构版本 | v1.3 (已修复 ARR 致命问题) |
| 作者 | 系统架构师 |
| 创建日期 | 2026-06-16 |
| 上级文档 | [PRD.md](./PRD.md) · [UI_Spec.md](./UI_Spec.md) |

---

## 一、系统整体架构

### 1.1 架构全景图

```
                            ┌─────────────────────────┐
                            │   爬虫服务器 (海外)       │
                            │   199.193.126.80         │
                            │   fetch_school_facts.py  │
                            │   → POST /internal/      │
                            │     crawler/ingest       │
                            └───────────┬─────────────┘
                                        │ HTTPS + JWT(内部)
                                        ▼
┌──────────────┐    ┌──────────────────────────────────────┐
│ 主播浏览器    │    │       生产服务器 (121.41.69.234)       │
│              │    │                                      │
│ index.html   │◄──►│  Nginx :443                          │
│ (SPA 单文件)  │    │  ├─ / → /www/wwwroot/.../index.html  │
│              │    │  ├─ /auth/* → FastAPI :8000          │
│ admin.html   │    │  ├─ /api/* → FastAPI :8000           │
│              │    │  ├─ /admin/* → FastAPI :8000         │
│              │    │  ├─ /internal/* → FastAPI :8000      │
│              │    │  └─ /schools/* → FastAPI :8000       │
└──────────────┘    └──────────┬───────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
       ┌──────────┐    ┌──────────┐    ┌──────────────┐
       │  MySQL   │    │  Redis   │    │  阿里云 OSS   │
       │ gaokao_ai│    │ (缓存)   │    │ (PDF 存储)    │
       │          │    │          │    │ (每日备份)    │
       │ +crawler │    │ 端口 6379│    │              │
       │ _staging │    │          │    │              │
       └──────────┘    └──────────┘    └──────────────┘
```

### 1.2 核心设计决策（为什么这样设计）

| 决策 | 选择 | 为什么 |
|------|------|--------|
| **前端架构** | 单文件 `index.html` + 静态数据文件 | ① 直播投屏场景，首屏加载必须 <2s（SPA框架太重）；② 单文件部署，运维零成本；③ 学校搜索/院校数据展示在前端本地，推荐计算由后端API返回 |
| **后端框架** | FastAPI (Python 3.11+) | ① 旧版已有完整 FastAPI 工程，可复用；② Python 生态对数据科学友好（NumPy/Pandas 处理一分一段表）；③ 异步原生支持，50并发无压力 |
| **数据库** | MySQL 8.0 (现有) | ① 已存 1.17M 录取记录 + 15 张表，迁移成本高；② 关系型数据模型（学校/考生/订单天然关联）；③ 行级锁支持原子扣费（`SELECT ... FOR UPDATE`） |
| **缓存** | Redis 7 | ① JWT 黑名单（注销/禁用即时生效）；② 扣费操作分布式锁；③ 搜索建议缓存（学校名前缀查询）；④ 未来限流/排行榜 |
| **对象存储** | 阿里云 OSS | ① 服务器已在国内阿里云，同机房低延迟；② PDF 报告 + MySQL 备份统一存储；③ 按量付费，MVP 成本极低 |
| **LLM 集成** | OpenAI 兼容 API（DeepSeek/Claude） | ① AI 点评 + 直播答疑双场景；② 不参与决策，仅负责文本生成（低风险）；③ DeepSeek 国产 API 性价比高 |
| **爬虫** | 独立 Python 脚本，海外服务器 | ① 绕过国内网站反爬；② 与主系统解耦，互不影响；③ 数据通过 SSH 隧道写入生产 MySQL |

### 1.3 架构原则

```
┌──────────────────────────────────────────────────┐
│  ★ 算法负责计算（基于 MySQL 真实录取数据）        │
│  ★ 规则引擎负责约束（过滤 + 分层）                │
│  ★ LLM 负责解释（不参与决策）                     │
│  ★ 推荐引擎在服务端执行，前端只负责渲染            │
│  ★ 数据缺失时自动触发爬虫补全                      │
└──────────────────────────────────────────────────┘
```

---

## 二、模块拆解

### 2.1 模块全景

```
┌──────────────────────────────────────────────────────────┐
│                     AI高考志愿规划师                       │
├──────────┬──────────┬──────────┬──────────┬──────────────┤
│ 主播前端  │ 管理后台  │ API 服务 │ 数据层   │ 外部依赖      │
│index.html│admin.html│ FastAPI  │ MySQL    │ 爬虫服务器     │
│          │          │          │ Redis    │ LLM API       │
│          │          │          │ OSS      │               │
└──────────┴──────────┴──────────┴──────────┴──────────────┘
```

### 2.2 前端模块（index.html）

| 模块 | 职责 | 为什么需要 | MVP |
|:---:|------|------|:---:|
| **页面路由** | hash-based 页面切换 (`#login`→`#student`→…→`#report`) | 单文件必须自行管理视图，无需引入 Vue Router 等重框架 | ✅ |
| **AuthManager** | JWT 存储/验证/过期检测、登录态守卫 | 前端需拦截未登录用户访问，避免无效请求 | ✅ |
| **FormValidator** | 7字段表单校验（必填/格式/分数钳制） | STEP1 录入必须在客户端即时校验，直播场景不能等后端 | ✅ |
| **SubjectSelector** | 动态选科组件（3+3 / 3+1+2） | 31省选科规则不同，必须根据省份动态渲染 | ✅ |
| **SchoolSearch** | 意向院校模糊搜索（防抖300ms） | 2673所学校，用户输入 ≥2 字触发搜索 | ✅ |
| **RecommendAPI** | 调用 `POST /api/recommendation/generate` 获取推荐结果 | 推荐计算已移至后端基于 MySQL 真实数据执行，前端仅传参+渲染 | ✅ |
| **PaywallManager** | 付款墙渲染 + 乐观扣费 + 回滚 | 核心变现点，必须原子操作保证扣费准确 | ✅ |
| **ReportRenderer** | 15所学校卡片 + 16维度 + 饼图 | 用户最终看到的价值输出 | ✅ |
| **PDFGenerator** | html2canvas + jsPDF 生成 PDF + 5种水印 | 主播需要下载发送给考生 | ✅ |
| **QAModule** | 直播答疑（10预设问题 + LLM回答） | P1 | ✅ |
| **LiveMode** | 全屏 + 无导航 + 大字 | 直播投屏时主播的展示需求 | ✅ |
| **StaticFiles** | `school_data.js`（仅用于院校搜索下拉+标签展示） | 学校基础信息（名称/省份/985/211标签）前端本地读取，避免搜索时每次请求后端 | ✅ |

### 2.3 后端模块（FastAPI）

| 模块 | 路由前缀 | 职责 | 为什么需要 |
|:---:|------|------|------|
| **Auth** | `/auth/` | 登录验证、JWT签发、Token刷新、注销 | 用户身份认证是所有操作的入口 |
| **Streamer** | `/auth/streamer/` | 主播信息查询、余额查询 | 前端需实时显示剩余次数 |
| **Deduction** | `/auth/deduct` | 原子扣费（`SELECT FOR UPDATE`） | **核心交易**——必须事务保证不超扣 |
| **Recommendation** ★ | `/api/recommendation/` | 基于 MySQL 真实录取数据的推荐计算：位次估算→特别关注区(独立)→四层填充(城市→本省→周边→全国)→概率计算→Tier分层→性格tiebreaker排序 | **系统核心价值**——所有推荐结果来自爬虫数据库中的真实录取记录 |
| **School API** | `/api/schools/` | 学校搜索（?q=郑州）、学校详情 | 意向院校搜索框需要后端模糊查询 |
| **Crawler Trigger** | `/api/recommendation/` (内嵌) | 检测数据覆盖缺口，自动生成爬虫任务 | 真实数据必有缺失省份/年份，需持续补全 |
| **Crawler Gateway** ★ | `/internal/crawler/` (内部JWT) | 爬虫数据入口：写入 `crawler_staging` 临时表 → 校验通过 → MERGE INTO `admission_history` | **ARR R2修复**——爬虫不直连MySQL，必须经API层校验 |
| **Report** | `/api/report/` | 报告生成记录、防倒卖检测 | 记录每份报告用于防倒卖+订单追溯 |
| **QA** | `/api/qa/` | 直播答疑（调用 LLM，返回口语化回答） | 主播在直播时回答观众提问 |
| **Admin** | `/admin/` | 主播CRUD、充值、订单查看、系统配置 | 管理员运营必须的后台接口 |

### 2.4 数据层

| 组件 | 用途 | 为什么需要 |
|------|------|------|
| **MySQL `gaokao_ai`** | 核心业务数据（11表） | 关系型数据天然适合学校/考生/订单模型 |
| **Redis** | JWT黑名单 + 分布式锁 + 搜索缓存 | ①注销后JWT立即失效；②扣费防并发；③学校搜索毫秒响应 |
| **阿里云 OSS** | PDF报告存储 + MySQL每日备份 | PDF量大后服务器磁盘不够，OSS按量付费弹性 |

### 2.5 外部依赖

| 依赖 | 说明 | 为什么需要 |
|------|------|------|
| **爬虫服务器** | `199.193.126.80`，Python + Playwright | 国内高校网站反爬严格，海外服务器可绕过 |
| **LLM API** | DeepSeek / Claude / GPT 兼容接口 | AI点评文本 + 直播答疑回答 |
| **Nginx** | 反向代理 + 静态文件 + HTTPS | 生产标配，已配置 Let's Encrypt |

---

## 三、核心流程

### 3.1 主流程时序图（主播端）

```
主播             index.html              Nginx            FastAPI          MySQL/Redis
 │                   │                     │                │                  │
 │  打开页面          │                     │                │                  │
 ├──────────────────►│                     │                │                  │
 │                   │ 加载静态数据文件     │                │                  │
 │                   │ (school_data.js等)  │                │                  │
 │                   │                     │                │                  │
 │  输入手机号+密码   │                     │                │                  │
 ├──────────────────►│                     │                │                  │
 │                   │ POST /auth/login    │                │                  │
 │                   ├────────────────────►├───────────────►│                  │
 │                   │                     │                │ 验证bcrypt密码   │
 │                   │                     │                ├─────────────────►│
 │                   │                     │                │ 签发JWT(24h)     │
 │                   │                     │                │ 返回balance      │
 │                   │◄────────────────────┤◄───────────────┤                  │
 │                   │ 存储JWT+balance     │                │                  │
 │                   │                     │                │                  │
 │  填7字段→下一步    │                     │                │                  │
 ├──────────────────►│                     │                │                  │
 │                   │ 前端校验 → #pref    │                │                  │
 │                   │                     │                │                  │
 │  填意向→开始分析   │                     │                │                  │
 ├──────────────────►│                     │                │                  │
 │                   │ POST /api/recommendation/generate  │                  │
 │                   │ {province,score,subject,...}       │                  │
 │                   ├────────────────────►├───────────────►│                  │
 │                   │                     │                │ ① 位次估算(yfd)  │
 │                   │                     │                │ ② 特别关注区(意向学校独立提取)│
 │                   │                     │                │ ③ 四层填充(城市→本省→周边→全国) │
 │                   │                     │                │ ④ 概率计算(admission_history)│
 │                   │                     │                │ ⑤ Tier分层+性格tiebreaker │
 │                   │                     │                │ ⑥ 过滤+排序       │
 │                   │                     │                │ ⑦ 检测数据缺口    │
 │                   │                     │                │ (~500ms, Redis缓存)│
 │                   │◄── {schools:[15所+16维]}──┤◄─────────┤                  │
 │                   │ 跳转 #paywall         │                │                  │
 │                   │                     │                │                  │
 │  看付款墙→解锁     │                     │                │                  │
 ├──────────────────►│                     │                │                  │
 │                   │ 乐观扣减 balance-1  │                │                  │
 │                   │ POST /auth/deduct   │                │                  │
 │                   ├────────────────────►├───────────────►│                  │
 │                   │                     │                │ BEGIN TRANSACTION│
 │                   │                     │                │ SELECT...FOR      │
 │                   │                     │                │ UPDATE            │
 │                   │                     │                │ UPDATE balance    │
 │                   │                     │                │ COMMIT            │
 │                   │◄── {balance, used} ─┤◄───────────────┤                  │
 │                   │ 渲染完整报告         │                │                  │
 │                   │                     │                │                  │
 │  看报告→下一位     │                     │                │                  │
 ├──────────────────►│                     │                │                  │
 │                   │ 清空student→#student│                │                  │
```

### 3.2 推荐引擎核心流程（服务端 `recommend()`）

```
输入: student { score, province, subject_category, rank?, cityPreference[], intendedSchools[], ... }
                      │
                      ▼
┌────────────────────────────────────────────────────────────────┐
│ PHASE 0: 位次估算                                               │
│  IF student.rank IS NOT NULL → 直接使用                          │
│  ELSE → 查询 yifenyidang 表:                                    │
│    SELECT cumulative_count FROM yifenyidang                     │
│    WHERE province=? AND year=2025 AND category=?                │
│    AND score <= ? ORDER BY score DESC LIMIT 1                   │
│  输出: estimated_rank                                           │
└──────────────────────┬─────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────────┐
│ PHASE 1: 分离特别关注区（意向学校） + 四层填充推荐池                │
│                                                                 │
│ ═══ 特别关注区（★ 不计入15所推荐总数）═════                        │
│   schools WHERE name IN (intendedSchools)                       │
│   精确名称匹配 `===`，标记 _intended=true                         │
│   ★ 无论概率多少一律展示（含0%）                                  │
│   ★ 占据报告最顶部「📌 特别关注」独立区域                           │
│   ★ 0% 概率学校加注"您的成绩无法达到该校录取线"                      │
│                                                                 │
│ ═══ 推荐池四层填充（逐层去重，固定15所）═════                       │
│                                                                 │
│ L1 — 意向城市学校                                                 │
│   城市→省份映射（60+城市表）→ schools WHERE province IN (...)     │
│   不设概率门槛，标记 _intended_city=true, ●强制保留                │
│                                                                 │
│ L2 — 生源地本省学校（考生所在省份）                                 │
│   schools WHERE province = student_province                     │
│   去除L1已有学校，按rankProb降序取                                 │
│                                                                 │
│ L3 — 意向城市周边（地理邻省/邻市）                                  │
│   城市邻省映射表 → 邻省学校                                        │
│   去除L1/L2已有学校，按rankProb降序取                               │
│                                                                 │
│ L4 — 全国兜底                                                     │
│   邻省 → 沿海发达省份 → 全国                                       │
│   去除L1/L2/L3已有学校，按rankProb降序填充至15所                    │
│                                                                 │
│ ★ 填充优先级: 意向城市 > 本省 > 意向城市周边 > 全国                 │
│ ★ 每层去重: 学校在上一层已出现过则跳过                              │
│ ★ 总推荐数固定15所(尽量维持5+5+5 tier分布)                         │
└──────────────────────┬─────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────────┐
│ PHASE 2: 概率计算（基于 admission_history 真实数据）              │
│                                                                 │
│ 对候选池中每所学校:                                               │
│                                                                 │
│ 2a. 查询该学校在考生省份的历年录取数据:                            │
│     SELECT year, min_rank, min_score, batch                     │
│     FROM admission_history                                      │
│     WHERE school_id = ? AND province = ?                        │
│     ORDER BY year DESC                                          │
│                                                                 │
│ 2b. 计算成绩排名推荐率 (rankProb):                                │
│     取最新年份的 min_rank 作为 school_rank                         │
│     IF student_rank <= school_rank:  # 考生位次更好               │
│       gap_ratio = (school_rank - student_rank) / school_rank     │
│       rankProb = 85 + gap_ratio * 14    # 范围 85-99%            │
│     ELSE:  # 考生位次更差                                         │
│       rankProb = 85 * (school_rank / student_rank)               │
│       # 或使用多年度平均: 取最近3年 min_rank 的中位数              │
│     钳制到 [1, 99]                                               │
│                                                                 │
│ 2c. 计算加权综合推荐率 (weightedProb):                            │
│     weightedProb = rankProb × 0.35                              │
│        + major_match × 0.20      (专业方向匹配, 见3.6.3)          │
│        + employment × 0.15       (就业前景, 查 employment_data)   │
│        + city_pref × 0.10        (城市偏好)                       │
│        + personality × 0.10      (性格匹配, 见下方)               │
│        + economic_fit × 0.10     (经济适应, 见下方)               │
│                                                                 │
│ 2c-1. 性格→院校类型匹配（占personality 10%）:                      │
│     外向活泼/社交沟通/领导管理 → 综合类/文科类院校 +10%              │
│     沉稳内敛/逻辑分析/钻研学术 → 理工科类院校 +10%                   │
│     艺术创作 → 艺术类/设计类院校 +10%                               │
│     动手实践 → 工科/应用型院校 +10%                                 │
│     院校类型判定: school_type字段 → 名称关键词回退                   │
│                                                                 │
│ 2c-2. 家庭经济→院校类型倾向（占economic_fit 10%）:                  │
│     较为困难+师范意向 → 师范类院校 +10% (免学费/补贴政策)            │
│     较为困难+无师范意向 → 学费≤5000元公办院校 +10%                   │
│     一般/良好/比较优越 → 无特殊加权，按正常评分                       │
│                                                                 │
│ 2c-3. 专业方向→院校匹配（占major_match 20%）:                      │
│     国家一流专业建设点 → 满分(20%)                                  │
│     省级一流专业建设点 → 15%                                        │
│     有该专业但非一流 → 10%                                          │
│     无该专业 → 0%                                                  │
│                                                                 │
│ 2d. 数据完整性标记:                                              │
│     has_admission_data: true/false (该省是否有录取记录)            │
│     data_years: [2022, 2023, 2024, 2025] (有数据的年份列表)        │
│     data_gap: true → 写入 crawler_tasks 触发爬虫补全              │
└──────────────────────┬─────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────────┐
│ PHASE 3: Tier 分层 + 过滤                                       │
│                                                                 │
│ ★ 特别关注区学校不参与 Tier 分类（独立区域展示）                    │
│                                                                 │
│ 推荐池中按 rankProb 分层:                                         │
│ ┌─────────────┬───────────────┬──────────────┐                  │
│ │  🚀 冲刺     │  🎯 稳妥      │  🟢 保底     │                  │
│ │ rankProb:   │ rankProb:     │ rankProb:    │                  │
│ │ 30% - 60%   │ 60% - 85%    │ ≥ 85%        │                  │
│ │ 最多5所      │ 最多5所       │ 最多5所       │                  │
│ └─────────────┴───────────────┴──────────────┘                  │
│                                                                 │
│ 特殊规则:                                                        │
│  - score < 400 → 概率阈值降至 5%（扩大候选范围）                   │
│  - _intended_city 学校 → 不设概率门槛                             │
│  - 某 tier 不足5所 → 从 L4 全国兜底池按分数接近度补足              │
│  - 无 admission_history 的学校 → rankProb 按同级学校均值估算       │
│  - 意向学校 → 不在此处处理，已在特别关注区独立展示                  │
└──────────────────────┬─────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────────┐
│ PHASE 4: 排序输出                                               │
│                                                                 │
│ ★ 特别关注区 → 报告最顶部「📌 特别关注」区域，按填写顺序展示        │
│                                                                 │
│ 推荐池的同 tier 内排序优先级:                                     │
│   ① _intended_city=true (● 意向城市学校) → 置顶                  │
│   ② rankProb 降序                                               │
│   ③ rankProb 差距 ≤ 5% → 性格匹配 tiebreaker（见Phase 2c-1）     │
│   ④ 性格未填或匹配度相同 → weightedProb 降序                      │
│                                                                 │
│ 输出: 15所学校，每所包含:                                         │
│   { school_info, rankProb, weightedProb, tier,                  │
│     admission_trend,  16维度数据, data_quality_flag }            │
└──────────────────────┬─────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────────┐
│ PHASE 5: 数据缺口检测 → 触发爬虫                                  │
│                                                                 │
│ FOR EACH school WHERE data_gap = true:                          │
│   INSERT INTO school_admission_crawl_tasks                      │
│     (school_id, province, year, status='pending')               │
│     ON DUPLICATE KEY UPDATE (已有pending任务不重复创建)            │
│                                                                 │
│ 前端标记: 返回字段 data_quality_flag:                             │
│   "full"      → 4年数据完整 (<200条/major数据也完整)              │
│   "partial"   → 1-3年数据有 (<100条/部分缺失)                     │
│   "estimated" → 无直接数据，使用同 tier 学校均值估算               │
│   "no_data"   → 完全无数据，仅有学校基础信息                        │
└────────────────────────────────────────────────────────────────┘
```

### 3.3 扣费流程（原子操作 + 幂等）

```
前端 doDirectUnlock():
  ① 生成 idempotency_key = crypto.randomUUID()  ← ★ 幂等键
  ② localBalance -= 1           ← 乐观扣减，即时更新UI
  ③ POST /auth/deduct           ← Bearer token + {idempotency_key}
  ④ 失败/超时 → 复用同一 idempotency_key 重试
  │
  ▼
后端 deduct():
  try: redis.set(lock_key, "1", nx=True, ex=5)  ← Redis 可用时加速
  except: pass  ← Redis 不可用降级，仅靠 DB 锁

  BEGIN TRANSACTION
    ① 幂等检查:
       SELECT id FROM orders 
       WHERE streamer_id=? AND idempotency_key=?
       → 已存在 → ROLLBACK，返回 {already_processed:true, order_id}
    
    ② SELECT balance FROM streamer_accounts WHERE id=? FOR UPDATE
       IF balance < 1 → ROLLBACK → 400
    
    ③ UPDATE balance = balance - 1, used_total = used_total + 1
    
    ④ INSERT INTO orders (id, streamer_id, idempotency_key, ...)
       INSERT INTO report_tasks (...)
  COMMIT
  │
  ├─ 200 → 前端确认 localBalance，展示完整报告
  ├─ 409 (already_processed) → 前端确认，无需回滚余额
  └─ 400/500 → 前端 localBalance += 1 (回滚)，Toast 提示错误
```

---

## 推荐引擎设计（核心）★

> **这是整个系统的核心价值所在。推荐引擎完全基于爬虫数据库中真实的录取数据（`admission_history` 117万条 + `yifenyidang` 4.2万条），不使用任何硬编码近似值。**

### 数据流架构

```
┌──────────────────────────────────────────────────────────────────┐
│                        推荐引擎数据流                              │
│                                                                  │
│  考生数据 ──┐                                                     │
│  {province, │     ┌─────────────────┐                            │
│   score,    │────►│  推荐引擎入口     │                            │
│   subject,  │     │  recommend()     │                            │
│   ...}      │     └────────┬────────┘                            │
│             │              │                                     │
│             │     ┌────────┼────────┐                            │
│             │     ▼        ▼        ▼                            │
│             │  ┌──────┐ ┌──────┐ ┌──────┐                        │
│             │  │Redis │ │MySQL │ │Config│                        │
│             │  │缓存   │ │主查询 │ │表    │                        │
│             │  └──┬───┘ └──┬───┘ └──────┘                        │
│             │     │        │                                     │
│             │     │  ┌─────┴──────────────────────────────┐      │
│             │     │  │          核心数据查询                │      │
│             │     │  │                                    │      │
│             │     │  │ ① yifenyidang → 分数↔位次互查       │      │
│             │     │  │    WHERE province+year+category     │      │
│             │     │  │                                    │      │
│             │     │  │ ② schools → 学校基础信息+标签       │      │
│             │     │  │    JOIN 城市映射表                   │      │
│             │     │  │                                    │      │
│             │     │  │ ③ admission_history → 录取数据       │      │
│             │     │  │    WHERE school_id+province         │      │
│             │     │  │    GROUP BY school_id              │      │
│             │     │  │    → min_rank, trend (逐年)         │      │
│             │     │  │                                    │      │
│             │     │  │ ④ employment_data → 就业数据        │      │
│             │     │  │    WHERE major_name IN (...)        │      │
│             │     │  └────────────────────────────────────┘      │
│             │     │                                              │
│             │     ▼                                              │
│             │  ┌──────────────────────────────────────────┐      │
│             │  │        推荐结果 (15所学校)                 │      │
│             │  │  {schools: [...], meta: {data_quality}}  │      │
│             │  └──────────────────────────────────────────┘      │
│             │     │                                              │
│             │     ▼                                              │
│             │  ┌──────────────────────────────────────────┐      │
│             │  │     数据缺口检测 → 爬虫任务队列            │      │
│             │  │  INSERT INTO school_admission_crawl_tasks │      │
│             │  └──────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────────┘
```

### 核心算法：概率计算

**为什么不能用旧公式**：
```
旧公式: rankProb = (1 - 位次比值) × 100
  问题: 当 student_rank < school_min_rank 时（考生更好），
        位次比值 < 1, prob = 正数但偏小。
        如: student_rank=35000, school_min_rank=45000
        比值=0.778, prob=22.2% → 把有把握的学校拉到了冲刺区
```

**新公式（基于真实位次比较）**：

```python
def calc_rank_prob(student_rank: int, school_min_rank: int, 
                    multi_year_history: list[dict]) -> float:
    """
    基于 admission_history 真实数据的位次比较概率
    
    Args:
        student_rank: 考生的省内位次（或由 yifenyidang 估算）
        school_min_rank: 该校在考生省份最近一年的最低录取位次
        multi_year_history: [{year, min_rank, min_score}, ...] 多年度数据
    """
    # 取最近3年数据（有则用，无则取最近1年）
    years = sorted(multi_year_history, key=lambda x: x['year'], reverse=True)[:3]
    
    if len(years) >= 2:
        # 多年度趋势：用中位数避免某一年波动
        ranks = [y['min_rank'] for y in years if y.get('min_rank')]
        school_rank = sorted(ranks)[len(ranks)//2] if ranks else years[0]['min_rank']
    else:
        school_rank = years[0]['min_rank'] if years else None
    
    if not school_rank:
        return None  # 无数据，标记为 estimated
    
    if student_rank <= school_rank:
        # 考生位次在第2校录取线之上 → 高概率
        gap_ratio = (school_rank - student_rank) / school_rank
        prob = 85 + gap_ratio * 14  # 范围: 85% ~ 99%
    else:
        # 考生位次在录取线之下 → 线性衰减
        prob = 85 * (school_rank / student_rank)  # 范围: 1% ~ 85%
    
    # 趋势修正（如果学校录取位次逐年收紧趋势，概率下调）
    if len(years) >= 2:
        if years[0]['min_rank'] < years[-1]['min_rank']:
            prob *= 0.95  # 位次收紧趋势→下调5%
    
    return max(1.0, min(99.0, prob))
```

**示例验证**：

| 场景 | student_rank | school_min_rank | 旧公式 prob | 新公式 prob | 合理性 |
|------|:---:|:---:|:---:|:---:|------|
| 考生优于学校 | 35000 | 45000 | 22.2% ❌ | 88.1% ✅ | 应该保底 |
| 考生劣于学校 | 50000 | 30000 | -66.7% ❌ | 51.0% ✅ | 应该冲刺 |
| 刚好持平 | 40000 | 40000 | 0% ❌ | 85.0% ✅ | 边界稳妥 |
| 大幅超越 | 10000 | 50000 | 80% | 96.2% | 极安全 |
| 大幅落后 | 80000 | 20000 | -300% | 21.3% | 极难录取 |

### MySQL 查询优化

**核心查询（单次推荐最关键的性能瓶颈）**：

```sql
-- ① 批量查询候选学校在目标省份的录取数据（避免 N+1）
SELECT 
    ah.school_id,
    ah.year,
    ah.min_rank,
    ah.min_score,
    ah.batch
FROM admission_history ah
WHERE ah.school_id IN (id1, id2, ..., idN)  -- 候选池学校ID
  AND ah.province = '河南'
  AND ah.year >= 2022                        -- 只取近4年
ORDER BY ah.school_id, ah.year DESC;

-- ② 位次估算（单次查询）
SELECT cumulative_count, score
FROM yifenyidang
WHERE province = '河南'
  AND year = 2025
  AND category = '理科'
  AND score <= 580
ORDER BY score DESC
LIMIT 1;
```

**索引要求**（现有索引 + 建议新增）：

| 表 | 索引 | 用途 | 状态 |
|------|------|------|:---:|
| `admission_history` | `idx_school_prov_year(school_id, province, year)` | 批量录取数据查询 | ⚠️ 需确认 |
| `admission_history` | `idx_prov_year_score(province, year, min_score)` | 按省份分数范围筛选 | 现有 |
| `yifenyidang` | `uk_prov_year_sub_score(province, year, category, score)` | 位次估算精确查询 | 现有 |

### Redis 缓存策略

```
缓存层级设计（减少 1.17M 行表的重复查询）:

┌───────────────────────────────────────────────────────────┐
│ L1: 省份-学校录取摘要缓存                                    │
│ Key:   recommend:admission:{province}:{school_id}          │
│ Value: { latest_rank, latest_score, years:[2022,2023,...],  │
│          trend: "rising"/"stable"/"falling" }              │
│ TTL:   1 小时（录取数据不频繁变化）                           │
│ 命中率: ~80%（同省重复查询多）                               │
├───────────────────────────────────────────────────────────┤
│ L2: 位次估算缓存                                            │
│ Key:   recommend:rank:{province}:{year}:{category}:{score} │
│ Value: { cumulative_count }                                │
│ TTL:   24 小时（一分一段表极少更新）                          │
│ 命中率: ~95%                                               │
├───────────────────────────────────────────────────────────┤
```python
# L3: 全量推荐结果缓存（使用确定性哈希，跨进程安全）
import hashlib, json

def make_cache_key(req: RecommendRequest) -> str:
    payload = json.dumps({
        "province": req.province,
        "score": req.score,
        "subject": req.subject_category,
        "city_pref": sorted(req.city_preference or []),
        "intended": sorted(req.intended_schools or []),
        "major": sorted(req.major_preference or []),
        "personality": sorted(req.personality or []),
        "economic": req.economic_level,
    }, sort_keys=True)
    return f"recommend:result:{hashlib.md5(payload.encode()).hexdigest()}"
```
└───────────────────────────────────────────────────────────┘
```

### 数据缺口检测 + 爬虫触发

```python
async def detect_data_gaps(school_id: int, province: str) -> str:
    """
    检测某学校在目标省份的数据覆盖情况
    返回: "full" | "partial" | "estimated" | "no_data"
    """
    result = await db.fetch_all(
        """SELECT year, min_rank FROM admission_history
           WHERE school_id = ? AND province = ? AND year >= 2022
           ORDER BY year DESC""",
        (school_id, province)
    )
    
    years = [r['year'] for r in result]
    has_rank  = any(r['min_rank'] is not None for r in result)
    
    if len(years) >= 4 and has_rank:
        return "full"
    elif len(years) >= 1 and has_rank:
        # 数据不完整 → 触发爬虫补全
        missing_years = [y for y in [2022, 2023, 2024, 2025] if y not in years]
        await _create_crawl_tasks(school_id, province, missing_years)
        return "partial"
    elif len(years) == 0:
        # 无直接数据 → 尝试同 tier 学校均值估算 + 触发爬虫
        await _create_crawl_tasks(school_id, province, [2022, 2023, 2024, 2025])
        return "estimated"
    else:
        return "no_data"


async def _create_crawl_tasks(school_id: int, province: str, years: list[int]):
    """创建爬虫任务，避免重复"""
    for year in years:
        await db.execute(
            """INSERT IGNORE INTO school_admission_crawl_tasks
               (school_id, province, year, status, created_at)
               VALUES (?, ?, ?, 'pending', NOW())""",
            (school_id, province, year)
        )
```

**爬虫任务表**（已有 556 条，`school_admission_crawl_tasks`）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `school_name` | VARCHAR | 学校名称 |
| `school_code` | VARCHAR | 学校代码 |
| `year` | INT | 爬取年份 |
| `status` | ENUM | pending/running/done/failed |
| `retry_count` | INT | 重试次数（>3 → 跳过） |
| `error_msg` | TEXT | 失败原因 |

### 性能预算

| 指标 | 目标 | 方案 |
|------|:---:|------|
| 推荐计算耗时 | <500ms (P50) / <1s (P99) | Redis L1+L2缓存 + 批量SQL + 候选池上限105所 |
| 位次估算 | <50ms | yifenyidang 精确查询（UK索引命中） |
| 录取数据批量查询 | <100ms (105所学校) | `WHERE school_id IN (...)` 批量查询 |
| 就业数据查询 | <10ms | 110条数据全量缓存到内存 |
| 前端渲染 | <200ms | DOM操作在浏览器主线程，无网络请求 |

---

## 四、数据库设计

### 4.1 表结构总览

```
                         ┌───────────────────┐
                         │  streamer_accounts │  ← 主播账号（核心）
                         └────────┬──────────┘
                                  │ 1:N
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
          ┌──────────────┐ ┌──────────┐ ┌──────────────┐
          │recharge_logs │ │  orders  │ │ report_tasks │
          │  充值记录     │ │  订单    │ │  报告任务     │
          └──────────────┘ └──────────┘ └──────────────┘

┌───────────┐  ┌───────────┐  ┌────────────────┐
│  schools  │  │yifenyidang│  │admission_history│
│ 学校基础   │  │一分一段表  │  │  历年录取记录    │
└───────────┘  └───────────┘  └────────────────┘

┌────────────────┐  ┌──────────┐  ┌──────────────┐
│employment_data │  │major_ranks│  │system_config │
│  就业数据       │  │专业排名   │  │  系统配置     │
└────────────────┘  └──────────┘  └──────────────┘
```

### 4.2 核心业务表（DDL）

#### `streamer_accounts` — 主播账号

```sql
CREATE TABLE streamer_accounts (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    phone           VARCHAR(11)  NOT NULL UNIQUE COMMENT '手机号（登录账号）',
    password_hash   VARCHAR(255) NOT NULL       COMMENT 'bcrypt哈希',
    name            VARCHAR(64)  NOT NULL       COMMENT '主播花名',
    balance         INT          NOT NULL DEFAULT 0 COMMENT '剩余可用次数',
    purchased_total INT          NOT NULL DEFAULT 0 COMMENT '累计购买次数',
    used_total      INT          NOT NULL DEFAULT 0 COMMENT '累计已用次数',
    status          ENUM('active','disabled') NOT NULL DEFAULT 'active',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_phone (phone),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='主播账号表';
```

**为什么这样设计**：
- `balance` 语义是**剩余次数**（非金额），全站统一用"剩余次数"表述
- `password_hash` 用 bcrypt，成本因子 12
- `purchased_total` + `used_total` 用于统计，`balance` = `purchased_total - used_total`（逻辑校验，非物理约束）
- InnoDB 支持行级锁，保证 `SELECT FOR UPDATE` 扣费原子性

#### `streamer_recharge_logs` — 充值记录

```sql
CREATE TABLE streamer_recharge_logs (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    streamer_id   INT          NOT NULL COMMENT '主播ID',
    amount        DECIMAL(10,2) NOT NULL COMMENT '充值金额（元）',
    count         INT          NOT NULL COMMENT '充值次数',
    operator      VARCHAR(64)  NOT NULL COMMENT '操作管理员',
    remark        VARCHAR(255) DEFAULT NULL COMMENT '备注',
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (streamer_id) REFERENCES streamer_accounts(id),
    INDEX idx_streamer (streamer_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='充值记录表';
```

**为什么需要**：审计追溯，管理员充值有据可查，防止纠纷。

#### `orders` — 订单

```sql
CREATE TABLE orders (
    id              VARCHAR(32)  PRIMARY KEY COMMENT '订单号（GK+时间戳+随机码）',
    streamer_id     INT          NOT NULL COMMENT '主播ID',
    student_nickname VARCHAR(64) NOT NULL COMMENT '考生抖音昵称',
    student_province VARCHAR(32) NOT NULL COMMENT '考生省份',
    student_score   INT          NOT NULL COMMENT '高考分数',
    student_subject VARCHAR(32)  NOT NULL COMMENT '选科',
    intended_schools TEXT        DEFAULT NULL COMMENT '意向学校（JSON数组）',
    idempotency_key VARCHAR(36)  DEFAULT NULL COMMENT '幂等键（UUID v4，防网络重试重复扣费）',
    status          ENUM('unlocked','refunded') NOT NULL DEFAULT 'unlocked',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (streamer_id) REFERENCES streamer_accounts(id),
    UNIQUE INDEX uk_idempotency (streamer_id, idempotency_key),
    INDEX idx_streamer_time (streamer_id, created_at),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';
```

**为什么需要**：
- 每份报告对应一条订单，关联主播 + 考生信息
- 管理员可查看所有订单（管理后台订单查看页）
- `intended_schools` 用于防倒卖检测（同省+同分±5+同意向学校 → 告警）

#### `report_tasks` — 报告任务（防倒卖）

```sql
CREATE TABLE report_tasks (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    order_id        VARCHAR(32)  NOT NULL COMMENT '关联订单号',
    streamer_id     INT          NOT NULL COMMENT '主播ID',
    student_hash    VARCHAR(64)  NOT NULL COMMENT '考生信息哈希（去敏）',
    score_range     VARCHAR(16)  NOT NULL COMMENT '分数段（如560-565）',
    province        VARCHAR(32)  NOT NULL COMMENT '省份',
    school_hash     VARCHAR(64)  DEFAULT NULL COMMENT '意向学校哈希',
    similarity_flag TINYINT      NOT NULL DEFAULT 0 COMMENT '相似度标记 0=正常 1=疑似 2=告警',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    INDEX idx_streamer_time (streamer_id, created_at),
    INDEX idx_hash (student_hash),
    INDEX idx_similarity (similarity_flag)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='报告任务表（防倒卖检测）';
```

**为什么需要**：
- 主播倒卖同一份报告给多个考生（核心风控需求）
- 检测逻辑：相同主播 + 相同省份 + 相同分数段（±5分）+ 相同意向学校哈希 → 连续3次 → 告警
- `student_hash` 脱敏存储，保护考生隐私

### 4.3 数据表（静态/准静态）

#### `schools` — 学校基础信息

```sql
-- 现有表，~2700条
CREATE TABLE schools (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(128) NOT NULL COMMENT '学校名称',
    province    VARCHAR(32)  DEFAULT NULL COMMENT '所在省份',
    city        VARCHAR(32)  DEFAULT '' COMMENT '所在城市（96%为空，需从校名提取）',
    tags        VARCHAR(64)  DEFAULT NULL COMMENT '985/211/双一流/公办/民办/专科',
    score985    INT          DEFAULT NULL COMMENT '985分数参考',
    score211    INT          DEFAULT NULL COMMENT '211分数参考',
    -- ...
    INDEX idx_name (name),
    INDEX idx_province (province),
    FULLTEXT idx_name_ft (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学校基础信息表';
```

#### `yifenyidang` — 一分一段表

```sql
CREATE TABLE yifenyidang (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    province    VARCHAR(32)  NOT NULL COMMENT '省份',
    year        INT          NOT NULL COMMENT '年份',
    subject_group VARCHAR(16) NOT NULL COMMENT '科类（物理/历史/综合）',
    score       INT          NOT NULL COMMENT '分数',
    cumulative  INT          NOT NULL COMMENT '累计人数（位次上限）',
    UNIQUE KEY uk_prov_year_sub_score (province, year, subject_group, score),
    INDEX idx_lookup (province, year, subject_group, score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='一分一段表';
```

#### `admission_history` — 历年录取记录（~1.17M 条）

```sql
CREATE TABLE admission_history (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    school_id       INT          NOT NULL COMMENT '学校ID（关联schools.school_id）',
    major_name      VARCHAR(128) DEFAULT NULL COMMENT '专业名称（多数为NULL）',
    year            INT          NOT NULL COMMENT '录取年份',
    province        VARCHAR(32)  NOT NULL COMMENT '录取省份',
    category        VARCHAR(16)  DEFAULT NULL COMMENT '科类（物理/历史/综合）',
    batch           VARCHAR(32)  DEFAULT NULL COMMENT '批次',
    min_score       INT          DEFAULT NULL COMMENT '最低分',
    min_rank        INT          DEFAULT NULL COMMENT '最低位次',
    INDEX idx_school_prov_year (school_id, province, year),
    INDEX idx_prov_year_score (province, year, min_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='历年录取记录表';
```

#### `employment_data` — 就业数据

```sql
CREATE TABLE employment_data (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    major           VARCHAR(64)  NOT NULL COMMENT '专业名称',
    employment_rate DECIMAL(5,2) DEFAULT NULL COMMENT '就业率(%)',
    graduate_rate   DECIMAL(5,2) DEFAULT NULL COMMENT '深造率(%)',
    avg_salary_start INT         DEFAULT NULL COMMENT '应届起薪(元)',
    avg_salary_3yr  INT          DEFAULT NULL COMMENT '3年后薪资(元)',
    core_positions  TEXT         DEFAULT NULL COMMENT '核心岗位(JSON)',
    other_positions TEXT         DEFAULT NULL COMMENT '外围岗位(JSON)',
    trend_5yr       TEXT         DEFAULT NULL COMMENT '5年趋势',
    UNIQUE KEY uk_major (major)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专业就业数据表';
```

#### `system_config` — 系统配置（KV）

```sql
CREATE TABLE system_config (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    config_key  VARCHAR(64)  NOT NULL UNIQUE COMMENT '配置键',
    config_value TEXT         NOT NULL COMMENT '配置值（JSON）',
    description VARCHAR(255) DEFAULT NULL COMMENT '说明',
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统配置表';

-- 预置配置项：
-- score_max          → {"上海":660,"其他":750}
-- tier_thresholds    → {"boost":30,"solid":60,"safe":85,"low_score":5}
-- price_per_query    → 29.9
-- low_score_boundary → 400
```

**为什么用 KV 表而非配置文件**：管理员可在后台上可视化修改阈值，无需重启服务。

### 4.4 Redis 数据结构

| Key Pattern | 类型 | 用途 | TTL |
|-------------|------|------|-----|
| `jwt:blacklist:{jti}` | String | JWT 黑名单（注销/禁用后即时失效） | 24h |
| `deduct:lock:{streamer_id}` | String (NX) | 扣费分布式锁，防止并发重复扣费 | 5s |
| `school:search:{prefix}` | Sorted Set | 学校名称前缀搜索缓存 | 1h |
| `rate:{ip}` | String (INCR) | IP 限流计数器 | 60s |

---

## 五、API 设计

### 5.1 接口总览

| 方法 | 路径 | 认证 | 说明 | MVP |
|:---:|------|:---:|------|:---:|
| POST | `/auth/login` | 无 | 手机号+密码登录 | ✅ |
| POST | `/auth/logout` | JWT | 注销（加入黑名单） | ✅ |
| GET | `/auth/streamer/profile` | JWT | 查询主播信息+剩余次数 | ✅ |
| POST | `/auth/streamer/deduct` | JWT | 扣费（原子事务） | ✅ |
| **POST** | **`/api/recommendation/generate`** ★ | JWT | **核心推荐计算（基于MySQL真实录取数据），返回15所学校16维度** | ✅ |
| GET | `/api/schools/search?q=郑州&limit=8` | JWT | 学校名称模糊搜索 | ✅ |
| GET | `/api/schools/{id}` | JWT | 学校详情 | ✅ |
| POST | `/api/qa/ask` | JWT | 直播答疑（调用LLM） | ✅ |
| POST | `/api/report/log` | JWT | 记录报告生成（防倒卖） | ✅ |
| GET | `/admin/streamers` | Admin | 主播列表（分页） | ✅ |
| POST | `/admin/streamers` | Admin | 新增主播 | ✅ |
| PUT | `/admin/streamers/{id}` | Admin | 编辑主播 | ✅ |
| PATCH | `/admin/streamers/{id}/status` | Admin | 启用/禁用主播 | ✅ |
| POST | `/admin/streamers/{id}/recharge` | Admin | 充值 | ✅ |
| GET | `/admin/orders` | Admin | 订单列表（分页/筛选） | ✅ |
| GET | `/admin/config` | Admin | 获取系统配置 | ✅ |
| PUT | `/admin/config` | Admin | 更新系统配置 | ✅ |
| GET | `/health` | 无 | 健康检查 | ✅ |

### 5.2 核心接口详情

#### `POST /auth/login` — 登录

```
Request:
  { "phone": "13800138000", "password": "xxx" }

Response 200:
  {
    "token": "eyJhbGciOi...",
    "streamer": {
      "id": 1,
      "name": "主播大明",
      "phone": "138****8000",
      "balance": 8
    }
  }

Error 401: { "error": "账号或密码错误" }
Error 403: { "error": "账号已被禁用，请联系管理员" }
```

#### `POST /auth/streamer/deduct` — 扣费（✅ 本接口）

```
Headers: Authorization: Bearer {token}

Response 200:
  {
    "success": true,
    "balance": 7,
    "used_total": 13,
    "order_id": "GK260616-1528-a3f2"
  }

Error 400: { "error": "剩余次数不足", "balance": 0 }
Error 401: { "error": "未登录或Token已过期" }
Error 429: { "error": "操作过于频繁，请稍后重试" }
```

**后端实现要点**：
```python
@router.post("/auth/deduct")
async def deduct(current_streamer=Depends(get_current_streamer)):
    lock_key = f"deduct:lock:{current_streamer.id}"
    # ① 获取分布式锁
    if not await redis.set(lock_key, "1", nx=True, ex=5):
        raise HTTPException(429, "操作过于频繁")

    try:
        async with db.transaction():
            # ② SELECT FOR UPDATE 行锁
            account = await db.fetch_one(
                "SELECT balance, used_total FROM streamer_accounts "
                "WHERE id = :id FOR UPDATE",
                {"id": current_streamer.id}
            )
            if account["balance"] < 1:
                raise HTTPException(400, "剩余次数不足")

            # ③ 原子更新
            await db.execute(
                "UPDATE streamer_accounts SET balance = balance - 1, "
                "used_total = used_total + 1 WHERE id = :id",
                {"id": current_streamer.id}
            )

            # ④ 生成订单号
            order_id = generate_order_id()
            await db.execute(
                "INSERT INTO orders (id, streamer_id, ...) VALUES (...)",
                {"id": order_id, ...}
            )
    finally:
        await redis.delete(lock_key)

    return {"success": True, "balance": account["balance"] - 1, ...}
```

#### `POST /api/recommendation/generate` ★ — 核心推荐（基于爬虫数据库）

```
Headers: Authorization: Bearer {token}

Request:
{
  "province": "河南",
  "score": 580,
  "subject_category": "理科",      // 物理/历史/综合
  "rank": null,                     // 位次（null=自动从yifenyidang估算）
  "city_preference": ["郑州","武汉"],
  "intended_schools": ["郑州大学"],
  "major_preference": ["计算机","软件工程"],
  "personality": ["逻辑分析","沉稳内敛"],
  "economic_level": "一般"          // 较为困难/一般/良好/比较优越
}

Response 200:
{
  "student_rank": 35210,            // 估算或用户提供的位次
  "rank_source": "estimated",       // "provided"|"estimated"
  "special_attention": [             // ★ 特别关注区（意向学校，不计入15所）
    {
      "school_id": 11,
      "name": "北京大学",
      "rank_prob": 0.0,             // 可能为0%
      "is_intended": true,
      "note": "您的成绩无法达到该校录取线"
    },
    {
      "school_id": 456,
      "name": "河南科技大学",
      "rank_prob": 65.0,
      "is_intended": true
    }
  ],
  "schools": [                      // 推荐池15所
    {
      "school_id": 123,
      "name": "郑州大学",
      "province": "河南",
      "city": "郑州",
      "tags": ["211","双一流"],
      "rank_prob": 53.4,             // ★ 成绩排名推荐率（tier分层以此为准）
      "weighted_prob": 58.2,         // 加权综合推荐率（仅供参考）
      "tier": 0,                     // 0=冲刺 1=稳妥 2=保底
      "tier_label": "冲刺",
      "is_intended": true,           // ★ 意向学校标记
      "is_intended_city": false,
      "admission_data": {
        "latest_year": 2025,
        "latest_min_rank": 22000,
        "latest_min_score": 604,
        "trend": "rising",           // rising/stable/falling
        "trend_detail": "602→606→609→612（↑微升）",
        "years_available": [2022,2023,2024,2025],
        "data_quality": "full"       // full/partial/estimated/no_data
      },
      "dimensions": {                // 16维度（预填充）
        "recommended_major": "计算机科学与技术",
        "tuition": "5000-5500元/年",
        "tuition_total": "4年约2.2万",
        "tuition_fit": "中等家庭可接受",
        "employment_rate": "92-97%",
        "avg_salary_start": "7400-11300元/月",
        "avg_salary_3yr": "12700-18600元/月",
        "core_positions": "软件开发/算法/架构(62%)",
        "other_positions": "产品经理/数据分析/公务员信息化岗(38%)",
        "trend_5yr": "AI大模型全面落地，2025-2030岗位需求年增≥15%",
        "city_analysis": "郑州(新一线)，物流/电商/食品/交通枢纽..."
      },
      "ai_review": null              // AI点评异步生成，先null
    },
    // ... 共15所
  ],
  "tier_summary": {
    "boost": {"count": 5, "range": "30%-60%"},
    "solid": {"count": 5, "range": "60%-85%"},
    "safe":  {"count": 5, "range": "≥85%"}
  },
  "data_quality_summary": {
    "full_count": 12,                // 4年数据完整的学校数
    "partial_count": 2,              // 1-3年数据/部分缺失
    "estimated_count": 1,            // 无直接数据，使用估算
    "crawl_tasks_created": 3         // 本次触发了3个爬虫补全任务
  },
  "generated_at": "2026-06-16T15:28:00Z",
  "cache_hit": false                 // 是否命中Redis缓存
}

Error 400: { "error": "缺少必填参数", "missing": ["province","score"] }
Error 422: { "error": "分数超出该省满分", "max_score": 660, "province": "上海" }
```

**后端实现伪代码**：
```python
@router.post("/api/recommendation/generate")
async def generate_recommendation(
    req: RecommendRequest,
    current_streamer = Depends(get_current_streamer)
):
    # ① 检查缓存（L3: 全量结果缓存）
    cache_key = f"recommend:result:{hash(req)}"
    if cached := await redis.get(cache_key):
        return json.loads(cached)
    
    # ② 位次估算（L2缓存）
    rank = req.rank or await estimate_rank(
        req.province, req.score, req.subject_category
    )
    
    # ③ 提取特别关注区（意向学校，不计入15所）
    intended_schools = extract_intended_schools(req, db)
    # → 精确名称匹配，标记 _intended=true
    
    # ④ 四层填充推荐池（意向城市→本省→周边→全国）
    candidate_pool = build_candidate_pool_four_tiers(req, db)
    # → L1意向城市 → L2本省 → L3周边 → L4全国
    # → 每层去重，最多105候选
    
    # ⑤ 批量查询录取数据（L1缓存）
    admission_data = await batch_query_admission(
        candidate_pool, req.province, redis, db
    )
    
    # ⑥ 概率计算 + 性格tiebreaker + Tier分层
    schools = []
    for school_id in candidate_pool:
        data = admission_data.get(school_id)
        rank_prob = calc_rank_prob(rank, data)
        weighted_prob = calc_weighted_prob(req, rank_prob, data)
        # ↑ 含性格匹配、经济偏好、专业匹配
        tier = assign_tier(rank_prob, req.score)
        data_quality = detect_data_gaps(school_id, req.province)
        schools.append({...})
    
    # ⑦ 排序 + 截取15所（含性格tiebreaker决胜）
    schools = sort_and_slice_with_tiebreaker(schools, req.personality)
    # 同tier: _intended_city置顶 → rankProb降序 → ≤5%→性格tiebreaker → weightedProb
    
    # ⑧ 组装结果：特别关注区 + 推荐池15所
    result = {
        "special_attention": intended_schools,  # 独立区域
        "schools": schools,                      # 15所推荐池
        ...
    }
    
    # ⑨ 缓存结果
    await redis.setex(cache_key, 600, json.dumps(result))
    
    return result
```

#### `GET /api/schools/search?q=郑州&limit=8` — 学校搜索

```
Response 200:
  {
    "results": [
      { "id": 123, "name": "郑州大学", "city": "郑州", "province": "河南", "tags": "211" },
      { "id": 456, "name": "郑州轻工业大学", "city": "郑州", "province": "河南", "tags": "公办" },
      ...
    ]
  }
```

#### `POST /api/qa/ask` — 直播答疑

```
Request:
  { "question": "计算机专业好就业吗？" }

Response 200:
  {
    "answer": "计算机这专业吧，不能说闭着眼都能找到工作，但确实就业面最广..."
  }
```

#### `POST /admin/streamers/{id}/recharge` — 充值

```
Request:
  { "count": 10, "amount": 299.00, "remark": "微信转账" }

Response 200:
  {
    "success": true,
    "streamer": { "id": 1, "balance": 18, "purchased_total": 30 }
  }
```

**后端实现**（必须事务）：
```python
async with db.transaction():
    # ① 更新主播余额
    await db.execute(
        "UPDATE streamer_accounts SET balance = balance + :count, "
        "purchased_total = purchased_total + :count WHERE id = :id",
        {"id": streamer_id, "count": count}
    )
    # ② 写入充值记录
    await db.execute(
        "INSERT INTO streamer_recharge_logs (streamer_id, amount, count, operator, remark) "
        "VALUES (:sid, :amt, :cnt, :op, :rmk)",
        {"sid": streamer_id, "amt": amount, "cnt": count, "op": operator, "rmk": remark}
    )
```

---

## 六、AI Agent 设计

### 6.1 设计理念

```
┌───────────────────────────────────────────────┐
│  ★ MVP阶段：LLM 仅用于文本生成（点评+答疑）     │
│  ★ V2阶段：引入 Agent 辅助数据增强+异常检测     │
│  ★ 核心推荐算法始终由规则引擎执行，Agent不替代   │
│     （原因：高考志愿填报涉及考生前途，必须可解释）│
└───────────────────────────────────────────────┘
```

### 6.2 MVP 阶段：LLM 文本生成

| 调用场景 | 触发时机 | Prompt 类型 | 模型推荐 |
|----------|----------|-------------|----------|
| **AI点评**（16维第16项） | 报告渲染时逐校调用 | `点评生成Prompt`：基于学校+专业+16维数据，生成50-100字口语化点评 | DeepSeek V3 |
| **直播答疑** | 主播在qa.html发送问题 | `答疑Prompt`：基于预设问题/自由输入，生成200字内口语化回答 | DeepSeek V3 |

**为什么要预生成点评而非实时调用**：
- 15所学校 × LLM调用 = 可能5-10秒延迟（直播场景不可接受）
- MVP方案：报告解锁时后台异步生成，前端先渲染14维数据 + 骨架屏占位，点评逐步填充

### 6.3 V2 阶段：AI Agent 扩展

```
                     ┌────────────────────┐
                     │   AI Agent 调度器   │
                     └────────┬───────────┘
                              │
        ┌─────────────┬───────┼───────┬─────────────┐
        ▼             ▼       ▼       ▼             ▼
  ┌──────────┐ ┌──────────┐ ┌──────┐ ┌──────────┐ ┌──────────┐
  │数据增强    │ │推荐解释    │ │异常   │ │质量巡检    │ │用户意图   │
  │Agent      │ │Agent      │ │检测   │ │Agent      │ │Agent      │
  ├──────────┤ ├──────────┤ │Agent  │ ├──────────┤ ├──────────┤
  │爬取缺失的  │ │将规则引擎  │ ├──────┤ │检测推荐    │ │理解主播    │
  │专业级数据  │ │输出转为    │ │识别   │ │结果质量    │ │自然语言    │
  │填补NULL   │ │自然语言    │ │主播   │ │一致性检查  │ │查询意图    │
  │字段       │ │解释推荐    │ │倒卖   │ │           │ │            │
  └──────────┘ └──────────┘ └──────┘ └──────────┘ └──────────┘
```

| Agent | 触发条件 | 能力 | 为什么需要 |
|-------|----------|------|------|
| **数据增强Agent** | 爬虫数据缺失（major_name为NULL） | 搜索公开信息补全专业名/学费/就业率 | admission_history 中 major_name 大量为NULL，手动补不现实 |
| **推荐解释Agent** | 用户查看报告时 | 将规则引擎的"为什么推荐这所学校"转为口语化解释 | 提高主播信任度，减少答疑负担 |
| **异常检测Agent** | 每次报告生成后 | 检查同主播近N份报告相似度，标记疑似倒卖 | 自动化风控，无需人工盯着 |
| **质量巡检Agent** | 定时（每日） | 抽样检查推荐结果合理性（同分不同省是否差异化、低分是否全空等） | 规则引擎需要持续调优，Agent 自动发现边界case |
| **用户意图Agent** | V3 在线支付/SaaS时 | 自然语言理解用户查询（"帮我看看560分在河南能上什么好学校"→结构化参数） | SaaS化后需求，降低使用门槛 |

### 6.4 Agent 技术实现路径

```
MVP (当前)          V2 (7月)              V3 (8月+)
─────────          ────────              ────────
单一LLM调用         Agent + 工具调用       Agent链 + 记忆
文字生成           数据增强 + 异常检测      多Agent协作
同步返回           异步队列（Celery）      实时流式
```

---

## 七、技术栈选型

### 7.1 完整技术栈

| 层级 | 技术 | 版本 | 选择原因 |
|------|------|:---:|------|
| **前端** | 原生 HTML/CSS/JS | — | 单文件架构，无框架依赖，首屏<2s。直播投屏场景下 SPA 框架（React/Vue）引入的 bundle size 和 hydration 时间不划算 |
| **前端图表** | Canvas API（原生） | — | 饼图+柱状图用原生 Canvas，体积=0KB，性能最优 |
| **PDF生成** | html2canvas + jsPDF | 1.4+ / 2.5+ | 前端直接截图合成，无需后端 puppeteer；jsPDF 支持水印叠加 |
| **后端框架** | FastAPI (Python) | 0.110+ | 异步原生（uvicorn），自动 OpenAPI 文档，数据验证（Pydantic v2） |
| **ORM** | SQLAlchemy 2.0 (async) | 2.0+ | 异步数据库操作，与 FastAPI 深度集成，原生事务支持 |
| **数据库驱动** | aiomysql | 0.2+ | FastAPI 异步 MySQL 驱动 |
| **数据库** | MySQL | 8.0 | 现有数据库，1.17M 数据，不作迁移 |
| **缓存** | Redis | 7.x | JWT黑名单 + 分布式锁 + 搜索缓存 |
| **Redis驱动** | redis-py (async) | 5.0+ | 原生 async/await 支持 |
| **认证** | python-jose (JWT) + bcrypt | 3.3+ / 4.1+ | JWT 无状态认证 + bcrypt Cost12 密码哈希 |
| **LLM客户端** | httpx (直接调用) | 0.27+ | 调用 DeepSeek/Claude API 兼容接口（通过 LiteLLM proxy 或直连） |
| **任务队列** | Celery + Redis (V2) | 5.3+ | 异步生成AI点评、异步PDF生成、定时巡检（MVP不用） |
| **对象存储** | oss2 (阿里云SDK) | 2.18+ | PDF上云 + MySQL备份 |
| **反向代理** | Nginx | 1.24+ | 已配置 Let's Encrypt HTTPS，7个 location 代理 |
| **进程管理** | systemd | — | gaokao-api.service 守护 FastAPI |
| **部署** | SCP + Python patch脚本 | — | 简单可靠，避免 sed `${}` 问题 |

### 7.2 为什么不选其他技术

| 候选 | 不选的原因 |
|------|------|
| **React/Vue** | ① 需要构建工具链，增加部署复杂度；② Bundle size 500KB+ 拖慢首屏；③ 直播投屏场景不需要 SPA 的路由/状态管理；④ 单人开发效率不如原生 HTML |
| **PostgreSQL** | 现有 MySQL 存有 1.17M 数据 + 15张表，迁移成本和风险高；MySQL 的事务+行锁能力足够 |
| **Node.js** | 旧版已是 Python/FastAPI，数据科学相关操作（一分一段表查询、Numpy）Python 生态更优 |
| **Docker** | MVP 阶段增加运维复杂度；单机部署 systemd 足够；V3 SaaS化时再容器化 |
| **K8s** | 严重过度设计，50并发的高峰无需编排 |
| **MongoDB** | 学校/订单/考生数据是强关系型，MongoDB 的文档模型反而增加JOIN复杂度 |

---

## 八、MVP 版本（最小闭环）

### 8.1 MVP 目标

**6月25日前具备可用状态**，主播可完成：登录→录入→推荐→付费解锁→完整报告→下一位学生。

### 8.2 MVP 功能矩阵

```
P0 (必须):
  ✅ ① 登录 (jwt)
  ✅ ② 考生信息 (7字段 + 动态选科)
  ✅ ③ 意向偏好 (4区域输入 + 院校搜索)
  ✅ ④ 分析中 (过渡动画 ~1.5s)
  ✅ ⑤ 付款墙 (加密遮蔽 + 解锁)
  ✅ ⑥ 完整报告 (15校 + 16维度 + PDF + 下一位)
  ✅ ⑦ 报告样板 (静态演示)
  ✅ 管理后台 - 主播CRUD + 充值

P1 (重要):
  ✅ ⑧ 直播答疑 (10预设 + AI回答)
  ✅ 管理后台 - 订单查看
  ✅ 直播模式 (全屏+隐藏导航)

P2 (不做):
  ❌ 在线支付 (先走线下转账→后台充值)
  ❌ 专业级数据 (major_name非NULL，爬虫补)
  ❌ 柱状图/雷达图 (MVP文字展示)
  ❌ 微信小程序 (备案中)
  ❌ Celery异步队列 (同步LLM调用可接受)
```

### 8.3 MVP 开发路线（2人 × 10天）

```
Day 1-2  │ Day 3-5   │ Day 6-7  │ Day 8-9   │ Day 10
─────────┼───────────┼──────────┼───────────┼────────
后端:     │ 后端:      │ 后端:     │ 联调+测试  │ 部署上线
Auth模块  │ 扣费+学校  │ 管理后台  │           │
数据库    │ API       │ API      │           │
─────────┼───────────┼──────────┼───────────┼────────
前端:     │ 前端:      │ 前端:     │ 联调+测试  │ 部署上线
登录页     │ 偏好+分析  │ 报告+PDF  │           │
考生信息   │ +付款墙    │ +样板+答疑│           │
选科组件   │ +推荐引擎  │ +直播模式 │           │
```

### 8.4 MVP 部署清单

| 项目 | 位置 | 说明 |
|------|------|------|
| 后端代码 | `/root/gaokao-ai/` | FastAPI，systemd 守护 |
| 前端主页 | `/www/wwwroot/gaokao.lumenaistudio.co/index.html` | 主播端 |
| 管理后台 | `/www/wwwroot/gaokao.lumenaistudio.co/admin.html` | 管理员 |
| 静态数据 | 同目录 `school_data.js`（仅用于院校搜索下拉+标签展示，~1.5MB） | 学校基础信息 |
| 直播答疑 | `/www/wwwroot/gaokao.lumenaistudio.co/qa.html` | P1 |
| Nginx配置 | `/etc/nginx/sites-enabled/gaokao` | 7个proxy_pass |
| MySQL | 本地 `gaokao_ai` 库 | 已有数据 |
| Redis | 本地 :6379 | 新安装 |

---

## 九、V2 扩展方向

### 9.1 扩展路线图

```
MVP (6/25)          V2.1 (7月中)            V2.2 (8月)             V3 (2027)
────────           ──────────              ──────────             ─────────
单机部署            Celery 异步队列          在线支付接入            SaaS多租户
同步LLM             AI点评异步预生成          微信/支付宝            独立实例管理
管理员人工充值       Agent数据增强            多主播排行榜           用量计费
线下转账             Agent异常检测            GitHub CI/CD          容器化部署
静态报告            Canvas图表(柱状/雷达)      Agent推荐解释         Agent链+记忆
                    PostgreSQL 迁移评估       专业数据补全
                    小程序备案
```

### 9.2 V2 关键架构变化

#### ① 引入 Celery 异步任务队列

```
FastAPI                 Celery Worker            Redis (broker)
   │                        │                       │
   ├─ 解锁报告              │                       │
   │  POST /auth/deduct     │                       │
   │  返回 order_id ──────► │                       │
   │  dispatch:             │                       │
   │  celery.send_task(     │                       │
   │    "generate_review",  ├─ consume ────────────►│
   │    args=[order_id]     │                       │
   │  )                     │  ① 查询学校16维数据    │
   │                        │  ② 调用LLM生成点评     │
   │                        │  ③ 写入点评缓存       │
   │                        │  ④ WebSocket推送完成  │
   │  ◄── WebSocket通知 ────┤                       │
   │  (前端渲染点评)         │                       │
```

**为什么需要**：
- 15所学校 × LLM调用 = 10-30秒（取决于并发策略）
- 同步调用让主播等待太久，异步生成 + 前端骨架屏占位体验更好

#### ② SaaS 多租户架构（V3）

```
                     ┌─────────────────┐
                     │   SaaS Gateway   │
                     │   (Nginx + 域名)  │
                     └────────┬────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
 ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
 │ Tenant A     │    │ Tenant B     │    │ Tenant C     │
 │ 独立 MySQL   │    │ 独立 MySQL   │    │ 独立 MySQL   │
 │ 独立 Redis   │    │ 独立 Redis   │    │ 独立 Redis   │
 │ 独立 OSS     │    │ 独立 OSS     │    │ 独立 OSS     │
 └──────────────┘    └──────────────┘    └──────────────┘
```

**当前设计对SaaS的兼容性**：
- ✅ streamer_accounts 已有关联字段，可加 `tenant_id`
- ✅ 扣费系统天然支持按次数计费（SaaS计费基础）
- ✅ 管理后台已有充值/订单模型，可直接复用
- ⚠️ 需改造：`tenant_id` 隔离、独立数据库/共享库方案选型、在线支付网关

---

## 十、部署方案

### 10.1 服务器拓扑

```
┌──────────────────────────────────────────────────────┐
│              生产服务器 121.41.69.234                    │
│  OS: Ubuntu 22.04                                     │
│                                                       │
│  ┌─────────────────┐  ┌─────────────────────────┐    │
│  │ Nginx :443       │  │ FastAPI :8000           │    │
│  │ 反向代理+静态文件  │  │ systemd: gaokao-api     │    │
│  │ SSL: Let'sEncrypt│  │ uvicorn workers=4        │    │
│  └─────────────────┘  └───────────┬─────────────┘    │
│                                    │                   │
│  ┌──────────┐  ┌──────────┐       │                   │
│  │ MySQL :3306│  │ Redis :6379│◄────┘                  │
│  │ gaokao_ai │  │ 缓存+锁   │                          │
│  └──────────┘  └──────────┘                          │
│                                                       │
│  静态文件：/www/wwwroot/gaokao.lumenaistudio.co/       │
│  后端代码：/root/gaokao-ai/                            │
└──────────────────────────────────────────────────────┘
```

### 10.2 关键配置文件

#### systemd 服务 (`/etc/systemd/system/gaokao-api.service`)

```ini
[Unit]
Description=Gaokao AI FastAPI Service
After=network.target mysql.service redis.service

[Service]
Type=simple
User=gaokao
WorkingDirectory=/root/gaokao-ai
ExecStart=/root/gaokao-ai/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

#### Nginx 核心配置

```nginx
# /etc/nginx/sites-enabled/gaokao
server {
    listen 443 ssl;
    server_name gaokao.lumenaistudio.co;

    ssl_certificate     /etc/letsencrypt/live/radar.lumenaistudio.co/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/radar.lumenaistudio.co/privkey.pem;

    root /www/wwwroot/gaokao.lumenaistudio.co;
    index index.html;

    # 静态文件（前端 SPA）
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理
    location /auth/     { proxy_pass http://127.0.0.1:8000/auth/; ... }
    location /api/      { proxy_pass http://127.0.0.1:8000/api/; ... }
    location /admin/    { proxy_pass http://127.0.0.1:8000/admin/; ... }
    location /health    { proxy_pass http://127.0.0.1:8000/health; }

    # ACME 验证
    location /.well-known/acme-challenge/ { root /var/www/html; }
}
```

### 10.3 部署命令（快速参考）

```bash
# === 后端部署 ===
# 1. 拷贝代码
scp api/services/ai_pro.py root@121.41.69.234:/root/gaokao-ai/api/services/
scp api/routers/auth.py root@121.41.69.234:/root/gaokao-ai/api/routers/

# 2. 重启服务（避免 systemctl restart 卡SSH）
ssh root@121.41.69.234 "pkill -HUP -f 'uvicorn.*main:app'"

# 3. 验证
curl -s http://127.0.0.1:8000/health  # → {"status":"ok"}

# === 前端部署 ===
# 1. 备份
ssh root@121.41.69.234 "cp /www/wwwroot/gaokao.lumenaistudio.co/index.html{,.bak_\$(date +%Y%m%d_%H%M%S)}"

# 2. 部署（用Python patch脚本，禁用sed以避免${}问题）
# 参考 skill: references/ssh-consent-workaround.md

# 3. 验证
ssh root@121.41.69.234 "nginx -t && systemctl reload nginx"
curl -sk 'https://127.0.0.1/' -H 'Host: gaokao.lumenaistudio.co' | head -1  # → HTTP 200

# === 数据库备份 ===
# 每日备份到OSS
mysqldump gaokao_ai | gzip | ossutil cp - oss://bucket/backup/gaokao_ai_$(date +%Y%m%d).sql.gz
```

### 10.4 监控与告警（MVP最小集）

| 监控项 | 方式 | 阈值 |
|--------|------|------|
| `/health` 可用性 | cron 每分钟 curl | 连续3次失败→告警 |
| MySQL 连接 | `mysqladmin ping` | 失败→告警 |
| 磁盘使用率 | `df -h` | >80%→告警 |
| 异常扣费 | DB 查询 `balance < 0` | 任何情况→告警 |
| 证书过期 | `openssl x509 -checkend` | <7天→告警 |

---

## 附录 A：关键技术约束速查表

| 约束 | 要点 |
|------|------|
| **96%学校city为空** | 必须用 `getCityFromSchoolName()` 从校名提取城市，再查城市→省份映射 |
| **山东选科归类** | 阳光高考官方列为3+3，非标杆产品的3+1+2 |
| **上海满分660** | 其余30省750，`SCORE_MAX = { '上海': 660 }` |
| **全站术语** | 统一用"剩余次数"，禁止"余额/金额" |
| **点评标签** | 统一用"💡 点评"，禁止"张雪峰点评" |
| **tier分层依据** | `rankProb`（成绩排名推荐率），非 `weightedProb` |
| **低分<400** | 阈值降到5%，意向城市学校加 `_intended_city` 绕过过滤 |
| **★ 特别关注区** | 意向学校独立展示区，不计入15所推荐总数。0%概率如实标注+特别提示 |
| **★ 四层填充** | L1意向城市→L2本省→L3周边→L4全国兜底，逐层去重 |
| **★ 性格tiebreaker** | rankProb差距≤5% → 外向偏文科、内向偏理工科、动手偏工科、艺术偏艺术类 |
| **★ 经济偏好** | 困难+师范→师范类院校加权；困难+无师→≤5000元年费公办加权 |
| **sed/${} 陷阱** | 生产部署禁止用 sed，必用 Python str.replace() |
| **证书续期** | standalone 模式，移走 sites-enabled 中所有 .bak 文件 |

## 附录 B：文件清单

```
D:\dev\NewGKAi\
├── docs/
│   ├── PRD.md              ★ 产品需求文档（权威参考）
│   ├── UI_Spec.md          ★ UI交互规格说明书
│   ├── Architecture.md     ★ 本文档
│   ├── Decisions.md        架构决策记录（ADRs，待填充）
│   ├── Tasks.md            开发任务拆分（待填充）
│   ├── prototype.html      可交互HTML原型
│   └── BOOT.md             
├── data/
│   └── gaokao_export/      MySQL 15表CSV导出
├── api/                    FastAPI 后端代码
│   ├── main.py
│   ├── routers/
│   │   ├── auth.py         认证 + 扣费
│   │   ├── schools.py      学校搜索API
│   │   ├── qa.py           直播答疑
│   │   ├── report.py       报告记录
│   │   └── admin.py        管理后台
│   ├── services/
│   │   ├── ai_pro.py       AI Pro推荐（LLM增强，预留）
│   │   ├── deduction.py    扣费服务
│   │   └── anti_fraud.py   防倒卖检测
│   └── models/
│       ├── streamer.py     主播模型
│       ├── school.py       学校模型
│       └── order.py        订单模型
├── frontend/
│   ├── index.html          主播端（主文件）
│   ├── admin.html          管理后台
│   ├── school_data.js      学校数据（~2MB）
│   ├── yfd_data.js         一分一段表（~100KB）
│   └── employment_data.js  就业数据（~11KB）
├── config/
│   ├── .env.example        环境变量模板
│   └── nginx-gaokao.conf   Nginx配置模板
├── scripts/
│   ├── deploy.sh           部署脚本
│   ├── backup.sh            数据库备份脚本
│   └── patch_frontend.py   前端patch部署脚本
└── requirements.txt        Python依赖
```

---

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-06-16 | 初始架构文档：系统架构、模块拆解、核心流程、数据库、API、AI Agent、技术栈、MVP、V2扩展、部署 |
| **v1.1** | **2026-06-16** | **★ 推荐引擎重大重构：从前端纯JS → 后端基于MySQL真实录取数据（admission_history 117万条 + yifenyidang 4.2万条）。新增：概率计算公式修正（位次比较法）、三级Redis缓存策略、数据缺口自动触发爬虫任务、`POST /api/recommendation/generate` 接口完整规格。移除前端 yfd_data.js/employment_data.js 静态文件依赖。** |
| **v1.2** | **2026-06-16** | **★ 对齐 PRD v3.1 …（略）** |
| **v1.3** | **2026-06-17** | **★ 修复 ARR 致命问题：① R1 扣费幂等——orders表新增 `idempotency_key` + `uk_idempotency` 唯一索引，前端生成UUID复用重试，后端幂等检查防重复扣费；② R2 爬虫数据网关——爬虫不再直连MySQL，改为 `POST /internal/crawler/ingest` → `crawler_staging` 临时表 → 校验 → MERGE INTO `admission_history`；③ R3 Redis降级——扣费`SET NX`失败降级为仅DB锁，JWT黑名单不可用时不检查（日志告警）；④ R5 缓存key——`hash()` 替换为 `hashlib.md5` 确定性哈希；⑤ R6 DDL修复——`admission_history.school_name` 改为 `school_id INT`；⑥ R7 systemd安全——`User=root` 改为 `User=gaokao`；⑦ L3全量结果缓存标记为V2推迟（ARR A6）。** |
