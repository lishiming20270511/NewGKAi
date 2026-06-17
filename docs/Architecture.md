# AI高考志愿规划师 — 技术架构文档

| 文档信息 | 内容 |
|---------|------|
| 产品名称 | AI高考志愿规划师 · 直播辅助工具 |
| 架构版本 | v2.0（对齐 PRD v4.0：6类爬虫/16维度/5张新表/密码管理/IP直连HTTP） |
| 作者 | 系统架构师 |
| 创建日期 | 2026-06-17 |
| 上级文档 | [PRD.md](./PRD.md) v4.0 · [UI_Spec.md](./UI_Spec.md) v4.0 |

---

## 一、系统整体架构

### 1.1 架构全景图

```
                            ┌─────────────────────────┐
                            │   爬虫服务器 (海外)       │
                            │   199.193.126.80         │
                            │   Python + Playwright    │
                            │   → POST /internal/      │
                            │     crawler/ingest       │
                            └───────────┬─────────────┘
                                        │ HTTP + 内部JWT
                                        ▼
┌──────────────┐    ┌──────────────────────────────────────┐
│ 主播浏览器    │    │       生产服务器 (121.41.69.234)       │
│              │    │                                      │
│ index.html   │◄──►│  Nginx :80                           │
│ (SPA 单文件)  │    │  ├─ / → /www/wwwroot/.../index.html  │
│              │    │  ├─ /auth/* → FastAPI :8000          │
│ admin.html   │    │  ├─ /api/* → FastAPI :8000           │
│              │    │  ├─ /admin/* → FastAPI :8000         │
│              │    │  ├─ /internal/* → FastAPI :8000      │
│              │    │  └─ /health → FastAPI :8000          │
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
| **前端架构** | 单文件 `index.html` + Bento Grid 暗色主题 | ① 直播投屏场景，首屏加载必须 <2s；② 单文件部署运维零成本；③ v4.0 Bento Grid 暗色主题适配直播视觉需求 |
| **后端框架** | FastAPI (Python 3.11+) | ① 旧版已有完整 FastAPI 工程可复用；② Python 生态对数据科学友好；③ 异步原生支持，50并发无压力 |
| **数据库** | MySQL 8.0 | ① 已存 1.17M 录取记录 + 现有业务表，迁移成本高；② 行级锁保证原子扣费；③ v4.0 新增 5 张数据表适配 16 维度需求 |
| **缓存** | Redis 7 | ① JWT 黑名单即时失效；② 扣费分布式锁；③ 推荐结果缓存（L1:1h / L2:24h） |
| **对象存储** | 阿里云 OSS | ① 同机房低延迟；② PDF 报告 + MySQL 备份统一存储；③ 按量付费低成本 |
| **LLM 集成** | OpenAI 兼容 API（DeepSeek/Claude/GPT） | ① AI 点评 + 直播答疑双场景；② 不参与决策仅负责文本生成 |
| **爬虫** | 独立 Python 脚本，海外服务器 | ① 绕过国内网站反爬；② 6 类任务表驱动（录取/专业/学费/就业/薪资/城市） |
| **HTTP 协议** | IP 直连 HTTP（非 HTTPS） | 域名购自国外注册商，阿里云 ICP 备案拦截境外域名；内部主播使用，安全组限制端口 |

### 1.3 架构原则

```
┌──────────────────────────────────────────────────┐
│  ★ 算法负责计算（基于 MySQL 真实录取数据 + 16维度） │
│  ★ 规则引擎负责约束（过滤 + 分层 + 性格决胜）      │
│  ★ LLM 负责解释（不参与决策）                     │
│  ★ 推荐引擎在服务端执行，前端只负责渲染            │
│  ★ 数据缺失时自动触发 6 类爬虫任务补全             │
│  ★ 所有数据差异化呈现，禁止全校统一模板            │
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
│(Bento    │(暗色主题) │          │ Redis    │ LLM API       │
│ Grid暗色) │          │          │ OSS      │               │
└──────────┴──────────┴──────────┴──────────┴──────────────┘
```

### 2.2 前端模块（index.html — Bento Grid 暗色主题）

| 模块 | 职责 | 为什么需要 | MVP |
|:---:|------|------|:---:|
| **页面路由** | hash-based 页面切换 (`#login`→`#student`→…→`#report`) | 单文件 SPA，无需框架 | ✅ |
| **AuthManager** | JWT 存储/验证/过期检测、登录态守卫 | 拦截未登录访问 | ✅ |
| **FormValidator** | 7字段表单校验（必填/格式/分数钳制） | 直播场景不能等后端 | ✅ |
| **SubjectSelector** | 动态选科组件（3+3 / 3+1+2，31省全覆盖） | 31省选科规则不同 | ✅ |
| **SchoolSearch** | 意向院校模糊搜索（防抖300ms） | ~2700所学校需快速检索 | ✅ |
| **RecommendAPI** | 调用 `POST /api/recommendation/generate` | 后端基于 MySQL 真实数据计算 | ✅ |
| **PaywallManager** | 付款墙渲染 + 乐观扣费 + 幂等重试 + 回滚 | 核心变现点，原子扣费保证 | ✅ |
| **ReportRenderer** | 5大板块报告渲染，16维度学校卡片 | 用户最终价值输出 | ✅ |
| **PDFGenerator** | html2canvas(scale:3) + jsPDF + 5种水印 | 主播下载发送给考生 | ✅ |
| **QAModule** | 直播答疑（10预设问题 + LLM回答） | P1 | ✅ |
| **LiveMode** | 全屏 + 无导航 + 大字 | 直播投屏需求 | ✅ |
| **BentoGridTheme** | 暗色主题 CSS 变量系统（Slate 900底色 + Indigo紫） | v4.0 视觉重塑 | ✅ |
| **StaticFiles** | `school_data.js`（仅用于院校搜索下拉+标签展示） | 避免搜索时每次请求后端 | ✅ |

### 2.3 后端模块（FastAPI）

| 模块 | 路由前缀 | 职责 | 为什么需要 |
|:---:|------|------|------|
| **Auth** | `/auth/` | 登录验证、JWT签发、Token刷新、注销（JWT黑名单） | 用户身份认证入口 |
| **Streamer** | `/auth/streamer/` | 主播信息查询、剩余次数查询 | 前端需实时显示次数 |
| **Deduction** ★ | `/auth/deduct` | 原子扣费（`SELECT FOR UPDATE` + 幂等键 + Redis锁降级） | **核心交易**——保证不超扣不重复扣 |
| **Recommendation** ★ | `/api/recommendation/` | 位次估算→特别关注区(独立)→四层填充(城市→本省→周边→全国)→概率计算(双推荐率)→Tier分层→性格tiebreaker→16维度数据组装→数据缺口检测 | **系统核心价值** |
| **School API** | `/api/schools/` | 学校搜索（?q=郑州）、学校详情 | 意向院校搜索框 |
| **Crawler Trigger** | `/api/recommendation/` (内嵌) | 检测16维度数据覆盖缺口，自动生成6类爬虫任务 | 真实数据必有缺失，需持续补全 |
| **Crawler Gateway** ★ | `/internal/crawler/` (内部JWT) | 爬虫数据入口：写入 `crawler_staging` → 校验 → MERGE INTO 目标表 | **ARR R2修复**——爬虫不直连MySQL |
| **Report** | `/api/report/` | 报告生成记录、防倒卖检测（相似度告警） | 订单追溯+风控 |
| **QA** | `/api/qa/` | 直播答疑（调用 LLM，返回口语化回答） | 主播直播时回答观众 |
| **Admin** | `/admin/` | 主播CRUD、充值、订单查看、密码管理、系统配置 | 管理员运营后台 |
| **Health** | `/health` | MySQL + Redis 连通性检查 | 监控告警 |

### 2.4 数据层

| 组件 | 用途 | 为什么需要 |
|------|------|------|
| **MySQL `gaokao_ai`** | 核心业务数据 + 16维度数据表 | 关系型数据天然适合学校/考生/订单模型 |
| **Redis** | JWT黑名单 + 分布式锁 + 推荐缓存(L1/L2) | ①注销即时生效；②扣费防并发；③缓存减少1.17M表查询 |
| **阿里云 OSS** | PDF报告存储 + MySQL每日备份 | PDF量大后服务器磁盘不够 |

### 2.5 外部依赖

| 依赖 | 说明 | 为什么需要 |
|------|------|------|
| **爬虫服务器** | `199.193.126.80`，Python + Playwright | 海外服务器绕过国内反爬，6类任务表驱动 |
| **LLM API** | DeepSeek / Claude / GPT 兼容接口 | AI点评文本 + 直播答疑 |
| **Nginx** | 反向代理 + 静态文件 + HTTP(:80) | IP 直连，无域名无 SSL |

---

## 三、核心流程

### 3.1 主流程时序图（主播端）

```
主播             index.html              Nginx            FastAPI          MySQL/Redis
 │                   │                     │                │                  │
 │  打开页面          │                     │                │                  │
 ├──────────────────►│                     │                │                  │
 │                   │ 加载静态数据文件     │                │                  │
 │                   │                     │                │                  │
 │  输入手机号+密码   │                     │                │                  │
 ├──────────────────►│                     │                │                  │
 │                   │ POST /auth/login    │                │                  │
 │                   ├────────────────────►├───────────────►│                  │
 │                   │                     │                │ 验证bcrypt密码   │
 │                   │                     │                │ 签发JWT(24h)     │
 │                   │◄── {token, balance}──┤◄───────────────┤                  │
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
 │                   │                     │                │ ② 特别关注区      │
 │                   │                     │                │ ③ 四层填充       │
 │                   │                     │                │ ④ 概率计算       │
 │                   │                     │                │ ⑤ Tier分层+性格  │
 │                   │                     │                │ ⑥ 16维度数据组装 │
 │                   │                     │                │ ⑦ 数据缺口检测    │
 │                   │◄── {schools:[15所+16维], special_attention}──┤         │
 │                   │ 跳转 #paywall         │                │                  │
 │                   │                     │                │                  │
 │  看付款墙→解锁     │                     │                │                  │
 ├──────────────────►│                     │                │                  │
 │                   │ 乐观扣减 balance-1  │                │                  │
 │                   │ POST /auth/deduct   │                │                  │
 │                   │ {idempotency_key}   │                │                  │
 │                   ├────────────────────►├───────────────►│                  │
 │                   │                     │                │ 幂等检查→行锁扣费│
 │                   │                     │                │ INSERT orders    │
 │                   │◄── {balance, order_id}──┤◄───────────┤                  │
 │                   │ 渲染完整报告(5大板块) │                │                  │
 │                   │                     │                │                  │
 │  看报告→测下一个   │                     │                │                  │
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
│  ELSE → 查询 yifenyidang 表（Redis L2缓存，TTL 24h）            │
└──────────────────────┬─────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────────┐
│ PHASE 1: 分离特别关注区 + 四层填充推荐池                          │
│                                                                 │
│ ═══ 特别关注区（★ 不计入15所）══════                              │
│   精确名称匹配(===)，标记 _intended=true                         │
│   无论概率多少一律展示（含0%）                                    │
│   0%概率加注"您的成绩无法达到该校录取线"                            │
│                                                                 │
│ ═══ 推荐池四层填充（逐层去重，固定15所）═══════                    │
│   L1 意向城市 → L2 本省 → L3 周边 → L4 全国兜底                  │
│   每层去重，总推荐数固定15所                                      │
│   偏好顺序: 意向城市 > 本省 > 意向城市周边 > 全国                 │
└──────────────────────┬─────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────────┐
│ PHASE 2: 概率计算（基于 admission_history 真实数据）              │
│                                                                 │
│ 2a. 批量查询 admission_history（Redis L1缓存，TTL 1h）           │
│ 2b. 成绩排名推荐率 (rankProb) — tier分层以此为准                  │
│     IF student_rank <= school_rank: prob = 85 + gap_ratio*14    │
│     ELSE: prob = 85 * (school_rank/student_rank)               │
│     多年度趋势修正：取最近3年min_rank中位数，紧缩趋势×0.95        │
│ 2c. 加权综合推荐率 (weightedProb) — 六维度加权                    │
│     = rankProb×0.35 + major_match×0.20 + employment×0.15       │
│       + city_pref×0.10 + personality×0.10 + economic_fit×0.10  │
└──────────────────────┬─────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────────┐
│ PHASE 3: Tier 分层 + 过滤                                       │
│                                                                 │
│ 特别关注区不参与 Tier 分类                                       │
│ 推荐池按 rankProb 分层:                                          │
│   冲刺(30-60%) / 稳妥(60-85%) / 保底(≥85%)                       │
│   低分<400 → 阈值降至5%                                          │
│   _intended_city 学校不设概率门槛                                │
│   某tier不足5所 → 从L4全国兜底池按分数接近度补足                  │
└──────────────────────┬─────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────────┐
│ PHASE 4: 16维度数据组装                                          │
│                                                                 │
│ 每所学校组装16个信息维度:                                        │
│   ①学校标签 ②录取概率 ③城市 ④近年分数线                          │
│   ⑤位次匹配 ⑥分数线趋势 ⑦推荐专业(相似度映射)                     │
│   ⑧学费(年费+4年总费+家庭承受力) ⑨录取趋势 ⑩专业地位             │
│   ⑪就业率(标注来源+年份) ⑫平均薪资 ⑬主要岗位                     │
│   ⑭5年趋势 ⑮城市分析(5子维度) ⑯AI点评                           │
│                                                                 │
│ 数据来源优先级:                                                   │
│   维度4/6/9: admission_history                                   │
│   维度7: school_majors + major_similarity映射                    │
│   维度8: school_tuition（热门已爬即时展示，冷门"查询中…"）        │
│   维度11: school_employment（标注来源+年份）                      │
│   维度12: school_salary（第三方交叉验证）                         │
│   维度15: city_analysis（前4维度同城缓存，第5维度按学校差异化）   │
│   维度16: LLM异步生成                                            │
└──────────────────────┬─────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────────────┐
│ PHASE 5: 排序输出 + 数据缺口检测 → 触发6类爬虫任务                │
│                                                                 │
│ 排序: _intended_city●置顶 → rankProb降序 → ≤5%→性格tiebreaker   │
│                                                                 │
│ 数据缺口检测（逐维度）→ 自动创建爬虫任务:                          │
│   school_admission_crawl_tasks      (录取数据缺失)               │
│   school_major_crawl_tasks          (专业数据缺失)               │
│   school_tuition_crawl_tasks        (学费数据缺失)               │
│   school_employment_crawl_tasks     (就业数据缺失/过期)          │
│   school_salary_crawl_tasks         (薪资数据缺失/过期)          │
│   school_city_crawl_tasks           (城市分析数据缺失)           │
│                                                                 │
│ 前端标记 data_quality_flag: "full"/"partial"/"estimated"/"no_data" │
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
  ├─ 200 → 前端确认，展示完整报告
  ├─ 409 (already_processed) → 前端确认，无需回滚
  └─ 400/500 → 前端 localBalance += 1 (回滚)，Toast 提示错误
```

### 3.4 密码修改流程

```
主播修改密码:
  ① 管理后台 → 点击「修改密码」
  ② 输入旧密码 + 新密码×2
  ③ POST /admin/change-password (Bearer token + {old_password, new_password})
  ④ 后端: 验证旧密码 → bcrypt哈希新密码 → UPDATE streamer_accounts
  ⑤ 成功 → Toast "密码修改成功"

管理员重置主播密码:
  ① 管理后台 → 主播列表 → 点击「重置密码」
  ② 后端: 生成随机8位密码 → bcrypt哈希 → UPDATE streamer_accounts
  ③ 返回: {new_password: "a3bF7kQ9"} → 管理员告知主播
```

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
          │  充值记录     │ │   订单   │ │  报告任务     │
          └──────────────┘ └──────────┘ └──────────────┘

┌───────────┐  ┌───────────┐  ┌────────────────┐  ┌─────────────┐
│  schools  │  │yifenyidang│  │admission_history│  │  admin_     │
│ 学校基础   │  │一分一段表  │  │  历年录取记录    │  │  accounts   │
└───────────┘  └───────────┘  └────────────────┘  └─────────────┘

┌───────────────┐ ┌──────────────┐ ┌────────────────┐ ┌──────────────┐
│ school_majors │ │major_        │ │ school_tuition │ │school_       │
│  各校专业列表  │ │similarity    │ │  学费(校×专业)  │ │employment    │
└───────────────┘ └──────────────┘ └────────────────┘ └──────────────┘

┌──────────────┐ ┌──────────────┐ ┌──────────────────────────────┐
│school_salary │ │city_analysis │ │ 6 类爬虫任务表                │
│薪资(校×专业)  │ │城市5维分析    │ │ admission / major / tuition   │
└──────────────┘ └──────────────┘ │ employment / salary / city    │
                                  └──────────────────────────────┘
```

### 4.2 核心业务表（DDL）

#### `streamer_accounts` — 主播账号

```sql
CREATE TABLE streamer_accounts (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    phone           VARCHAR(11)  NOT NULL UNIQUE COMMENT '手机号（登录账号）',
    password_hash   VARCHAR(255) NOT NULL       COMMENT 'bcrypt哈希(cost=12)',
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

#### `admin_accounts` — 管理员账号（v4.0 新增）

```sql
CREATE TABLE admin_accounts (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    username        VARCHAR(64)  NOT NULL UNIQUE COMMENT '管理员用户名',
    password_hash   VARCHAR(255) NOT NULL       COMMENT 'bcrypt哈希(cost=12)',
    role            ENUM('super_admin','admin') NOT NULL DEFAULT 'admin' COMMENT '角色',
    status          ENUM('active','disabled') NOT NULL DEFAULT 'active',
    last_login_at   DATETIME     DEFAULT NULL  COMMENT '最后登录时间',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='管理员账号表（独立于主播体系）';
```

**为什么需要**：管理员账号独立于主播账号体系；super_admin 可重置其他管理员密码。

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

**防倒卖检测逻辑**：同主播 + 同省 + 同分数段(±5分) + 同意向学校哈希 → 连续3次 → 告警。

### 4.3 数据表（静态/准静态）

#### `schools` — 学校基础信息

```sql
CREATE TABLE schools (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(128) NOT NULL COMMENT '学校名称',
    province    VARCHAR(32)  DEFAULT NULL COMMENT '所在省份',
    city        VARCHAR(32)  DEFAULT '' COMMENT '所在城市（96%为空，需从校名提取）',
    tags        VARCHAR(64)  DEFAULT NULL COMMENT '985/211/双一流/公办/民办/专科',
    school_type VARCHAR(32)  DEFAULT NULL COMMENT '院校类型（综合/理工/师范/艺术/…）',
    score985    INT          DEFAULT NULL COMMENT '985分数参考',
    score211    INT          DEFAULT NULL COMMENT '211分数参考',
    INDEX idx_name (name),
    INDEX idx_province (province),
    FULLTEXT idx_name_ft (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学校基础信息表';
```

#### `admission_history` — 历年录取记录（~1.17M 条）

```sql
CREATE TABLE admission_history (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    school_id       INT          NOT NULL COMMENT '学校ID（关联schools.id）',
    major_name      VARCHAR(128) DEFAULT NULL COMMENT '专业名称',
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

### 4.4 v4.0 新增数据表（16维度数据支撑）

#### `school_majors` — 各校专业列表

```sql
CREATE TABLE school_majors (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    school_id       INT          NOT NULL COMMENT '学校ID',
    major_name      VARCHAR(128) NOT NULL COMMENT '专业名称',
    major_level     VARCHAR(32)  DEFAULT NULL COMMENT '专业等级（国家级一流/省级一流/普通）',
    discipline      VARCHAR(64)  DEFAULT NULL COMMENT '学科门类',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_school_major (school_id, major_name),
    INDEX idx_school (school_id),
    INDEX idx_major (major_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='各校开设专业列表';
```

**为什么需要**：维度7（推荐专业）的数据源——若该校无意向专业，通过 `major_similarity` 映射最相近专业。

#### `major_similarity` — 专业相似度映射表（v4.0 新增）

```sql
CREATE TABLE major_similarity (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    source_major    VARCHAR(64)  NOT NULL COMMENT '源专业（考生意向）',
    target_major    VARCHAR(64)  NOT NULL COMMENT '目标专业（该校实际开设）',
    similarity      DECIMAL(3,2) NOT NULL DEFAULT 1.00 COMMENT '相似度 0.00-1.00',
    UNIQUE KEY uk_pair (source_major, target_major),
    INDEX idx_source (source_major)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专业相似度映射表';

-- 预置映射示例:
-- 通信工程 ↔ 信息工程(0.95) / 电子信息工程(0.90) / 电子科学与技术(0.85)
-- 计算机科学与技术 ↔ 软件工程(0.95) / 人工智能(0.85) / 数据科学(0.80)
```

**为什么需要**：当学校没有考生意向专业时，自动推荐最相近的专业并标注"相近专业"，保证不同学校推荐的专业差异化。

#### `school_tuition` — 学费数据（v4.0 新增）

```sql
CREATE TABLE school_tuition (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    school_id       INT          NOT NULL COMMENT '学校ID',
    major_name      VARCHAR(128) NOT NULL COMMENT '专业名称（NULL=校级通用）',
    tuition_per_year INT         NOT NULL COMMENT '年学费（元）',
    duration_years  TINYINT      NOT NULL DEFAULT 4 COMMENT '学制（年）',
    data_source     VARCHAR(255) DEFAULT NULL COMMENT '数据来源（学校官网URL）',
    data_year       INT          DEFAULT NULL COMMENT '数据年份',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_school (school_id),
    INDEX idx_school_major (school_id, major_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学费数据表（校×专业）';
```

**为什么需要**：维度8（学费）的数据源。混合爬取策略：985/211/双一流提前全量爬取，普通院校首次被推荐时后台异步爬取。不同学校学费必须差异化。

#### `school_employment` — 就业数据（v4.0 新增）

```sql
CREATE TABLE school_employment (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    school_id       INT          NOT NULL COMMENT '学校ID',
    employment_rate DECIMAL(5,2) DEFAULT NULL COMMENT '就业率(%)',
    graduate_rate   DECIMAL(5,2) DEFAULT NULL COMMENT '深造率(%)',
    data_source     VARCHAR(255) DEFAULT NULL COMMENT '数据来源（教育部报告/学校官网/第三方）',
    data_year       INT          DEFAULT NULL COMMENT '数据年份',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_school (school_id),
    INDEX idx_school (school_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='就业数据表';
```

**为什么需要**：维度11（就业率）的数据源。数据来源优先级：教育部2025报告 → 2024 → 第三方交叉验证。每所学校数据独立。

#### `school_salary` — 薪资数据（v4.0 新增）

```sql
CREATE TABLE school_salary (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    school_id       INT          NOT NULL COMMENT '学校ID',
    major_name      VARCHAR(128) DEFAULT NULL COMMENT '专业名称',
    salary_start_min INT         DEFAULT NULL COMMENT '应届起薪下限（元/月）',
    salary_start_max INT         DEFAULT NULL COMMENT '应届起薪上限（元/月）',
    salary_3yr_min  INT          DEFAULT NULL COMMENT '3年后薪资下限（元/月）',
    salary_3yr_max  INT          DEFAULT NULL COMMENT '3年后薪资上限（元/月）',
    data_source     VARCHAR(255) DEFAULT NULL COMMENT '数据来源',
    data_year       INT          DEFAULT NULL COMMENT '数据年份',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_school (school_id),
    INDEX idx_school_major (school_id, major_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='薪资数据表（校×专业）';
```

**为什么需要**：维度12（平均薪资）的数据源。需体现城市/学校层次差异，不同学校薪资数据不可相同。

#### `city_analysis` — 城市5维分析（v4.0 新增）

```sql
CREATE TABLE city_analysis (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    city_name       VARCHAR(32)  NOT NULL UNIQUE COMMENT '城市名称',
    location        TEXT         NOT NULL COMMENT '维度1: 城市位置（地理区位+交通枢纽）',
    advantage       TEXT         NOT NULL COMMENT '维度2: 城市优势（政策/产业/人才）',
    development     TEXT         NOT NULL COMMENT '维度3: 发展现状（GDP/人口/城市等级）',
    main_business   TEXT         NOT NULL COMMENT '维度4: 主要业务（支柱产业/名企）',
    city_level      VARCHAR(16)  DEFAULT NULL COMMENT '城市等级（一线/新一线/二线/…）',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='城市5维分析数据表';
```

**为什么需要**：维度15（城市分析）的数据源。同城高校的前4维度可缓存复用，第5维度（就业影响）需结合学校专业特点微调。

### 4.5 6 类爬虫任务表

```sql
-- 模板结构（6张表共用）
CREATE TABLE school_admission_crawl_tasks (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    school_id       INT          NOT NULL COMMENT '学校ID',
    province        VARCHAR(32)  DEFAULT NULL COMMENT '目标省份',
    year            INT          DEFAULT NULL COMMENT '目标年份',
    status          ENUM('pending','running','done','failed') NOT NULL DEFAULT 'pending',
    retry_count     INT          NOT NULL DEFAULT 0,
    error_msg       TEXT         DEFAULT NULL,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_school (school_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='录取数据爬取任务表';

CREATE TABLE school_major_crawl_tasks (
    -- 同上结构，用于专业数据爬取
    ...
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专业数据爬取任务表';

CREATE TABLE school_tuition_crawl_tasks (
    -- 同上结构，用于学费数据爬取
    ...
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学费数据爬取任务表';

CREATE TABLE school_employment_crawl_tasks (
    -- 同上结构，用于就业数据爬取
    ...
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='就业数据爬取任务表';

CREATE TABLE school_salary_crawl_tasks (
    -- 同上结构，用于薪资数据爬取
    ...
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='薪资数据爬取任务表';

CREATE TABLE school_city_crawl_tasks (
    -- 同上结构，city_name 替代 school_id
    ...
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='城市分析数据爬取任务表';
```

**爬取优先级**：录取分数 > 专业列表 > 学费 > 就业率 > 薪资 > 城市分析

### 4.6 Redis 数据结构

| Key Pattern | 类型 | 用途 | TTL |
|-------------|------|------|-----|
| `jwt:blacklist:{jti}` | String | JWT 黑名单（注销/禁用即时失效） | 24h |
| `deduct:lock:{streamer_id}` | String (NX) | 扣费分布式锁，防并发重复扣费 | 5s |
| `school:search:{prefix}` | Sorted Set | 学校名称前缀搜索缓存 | 1h |
| `recommend:admission:{province}:{school_id}` | String (JSON) | L1: 省份-学校录取摘要缓存 | 1h |
| `recommend:rank:{province}:{year}:{category}:{score}` | String (JSON) | L2: 位次估算缓存 | 24h |

---

## 五、API 设计

### 5.1 接口总览

| 方法 | 路径 | 认证 | 说明 | MVP |
|:---:|------|:---:|------|:---:|
| POST | `/auth/login` | 无 | 手机号+密码登录 | ✅ |
| POST | `/auth/logout` | JWT | 注销（加入黑名单） | ✅ |
| GET | `/auth/streamer/profile` | JWT | 查询主播信息+剩余次数 | ✅ |
| POST | `/auth/streamer/deduct` | JWT | 扣费（原子事务+幂等） | ✅ |
| **POST** | **`/api/recommendation/generate`** ★ | JWT | **核心推荐（返回15所+16维度+特别关注区）** | ✅ |
| GET | `/api/schools/search?q=郑州&limit=8` | JWT | 学校名称模糊搜索 | ✅ |
| GET | `/api/schools/{id}` | JWT | 学校详情 | ✅ |
| POST | `/api/qa/ask` | JWT | 直播答疑（调用LLM） | ✅ |
| POST | `/api/report/log` | JWT | 记录报告生成（防倒卖） | ✅ |
| GET | `/admin/streamers` | Admin | 主播列表（分页） | ✅ |
| POST | `/admin/streamers` | Admin | 新增主播 | ✅ |
| PUT | `/admin/streamers/{id}` | Admin | 编辑主播 | ✅ |
| PATCH | `/admin/streamers/{id}/status` | Admin | 启用/禁用主播 | ✅ |
| POST | `/admin/streamers/{id}/recharge` | Admin | 充值 | ✅ |
| POST | `/admin/streamers/{id}/reset-password` | Admin | 重置主播密码（v4.0新增） | ✅ |
| POST | `/admin/change-password` | Admin | 管理员/主播自助修改密码（v4.0新增） | ✅ |
| GET | `/admin/orders` | Admin | 订单列表（分页/筛选） | ✅ |
| GET | `/admin/config` | Admin | 获取系统配置 | ✅ |
| PUT | `/admin/config` | Admin | 更新系统配置 | ✅ |
| POST | `/internal/crawler/ingest` | 内部JWT | 爬虫数据入口（Nginx IP白名单） | ✅ |
| GET | `/health` | 无 | 健康检查 `{mysql:"ok", redis:"ok"}` | ✅ |

### 5.2 核心接口详情

#### `POST /api/recommendation/generate` ★ — 核心推荐（v4.0 16维度）

```
Headers: Authorization: Bearer ***

Request:
{
  "province": "河南",
  "score": 580,
  "subject_category": "物理",        // 物理/历史/综合
  "rank": null,                     // 位次（null=自动从yifenyidang估算）
  "city_preference": ["郑州","武汉"],
  "intended_schools": ["北京大学","郑州大学"],
  "major_preference": ["计算机","软件工程"],
  "personality": ["逻辑分析","沉稳内敛"],
  "economic_level": "一般"          // 较为困难/一般/良好/比较优越
}

Response 200:
{
  "student_rank": 35210,
  "rank_source": "estimated",
  "special_attention": [              // ★ 特别关注区（不计入15所）
    {
      "school_id": 11,
      "name": "北京大学",
      "rank_prob": 0.0,
      "is_intended": true,
      "note": "您的成绩无法达到该校录取线"
    },
    {
      "school_id": 456,
      "name": "郑州大学",
      "rank_prob": 88.1,
      "is_intended": true
    }
  ],
  "schools": [                        // 推荐池15所（16维度）
    {
      "school_id": 123,
      "name": "郑州大学",
      "province": "河南",
      "city": "郑州",
      "tags": ["211","双一流"],
      "school_type": "综合",
      "rank_prob": 88.1,
      "weighted_prob": 91.2,
      "tier": 2,
      "tier_label": "保底",
      "is_intended": false,
      "is_intended_city": true,
      "admission_data": {
        "latest_year": 2025,
        "latest_min_rank": 22000,
        "latest_min_score": 604,
        "trend": "rising",
        "trend_detail": "河南：602→606→609→612分（↑微升）",
        "years_available": [2022,2023,2024,2025],
        "data_quality": "full"
      },
      "dimensions": {                   // ★ v4.0 16维度
        "school_tags": "211 双一流",
        "admit_probability": "88.1%",
        "city_info": "郑州（新一线）",
        "recent_score": "2025年最低604分",
        "rank_match": "✓位次匹配",
        "score_trend": "602→606→609→612（↑微升）",
        "recommended_major": "计算机科学与技术",
        "major_note": null,             // null=原专业, "相近专业"=映射
        "tuition_per_year": "5000-5500元/年",
        "tuition_total": "4年约2.2万",
        "tuition_fit": "中等家庭可接受",
        "admit_trend": "河南：602→606→609→612分（↑微升）",
        "major_level": "国家级一流专业建设点",
        "employment_rate": "92-97%，深造占比约28%",
        "employment_source": "数据来源：郑州大学2025届就业质量报告",
        "avg_salary": "应届起薪7400-11300元/月；3年后可达12700-18600元/月",
        "core_positions": "核心(62%)：软件开发/算法/架构",
        "other_positions": "外围(38%)：产品经理/数据分析/公务员信息化岗",
        "trend_5yr": "AI大模型全面落地，2025-2030年岗位需求年增≥15%",
        "city_analysis": {
          "location": "郑州，地处中原腹地，国家级交通枢纽，米字型高铁网覆盖",
          "advantage": "国家中心城市、中原经济区核心，双一流高校2所，人才落户补贴丰厚",
          "development": "2025年GDP超1.3万亿，常住人口1300万，新一线城市",
          "main_business": "支柱：物流/电商/食品加工/装备制造。名企：富士康/宇通客车/思念食品/蜜雪冰城",
          "career_impact": "应届起薪5000-7500元/月，消费水平较低，工资留存率高。留本地性价比优"
        },
        "ai_review": null               // AI点评异步生成，先null
      }
    }
    // ... 共15所
  ],
  "tier_summary": {
    "boost": {"count": 5, "range": "30%-60%"},
    "solid": {"count": 5, "range": "60%-85%"},
    "safe":  {"count": 5, "range": "≥85%"}
  },
  "data_quality_summary": {
    "full_count": 12,
    "partial_count": 2,
    "estimated_count": 1,
    "crawl_tasks_created": {"admission": 0, "major": 1, "tuition": 2, "employment": 1, "salary": 1, "city": 0}
  },
  "generated_at": "2026-06-17T15:28:00Z",
  "cache_hit": false
}
```

#### `POST /admin/change-password` — 自助修改密码（v4.0 新增）

```
Headers: Authorization: Bearer ***   (主播JWT 或 管理员JWT)

Request:
{
  "old_password": "current_pass",
  "new_password": "new_pass_123"
}

Response 200:
{ "success": true, "message": "密码修改成功" }

Error 400: { "error": "旧密码错误" }
Error 422: { "error": "新密码长度需6-20位" }
```

**后端实现要点**：
```python
@router.post("/admin/change-password")
async def change_password(
    req: ChangePasswordRequest,
    current_user = Depends(get_current_user)  # 主播或管理员
):
    # ① 验证旧密码
    if not bcrypt.verify(req.old_password, current_user.password_hash):
        raise HTTPException(400, "旧密码错误")
    
    # ② 校验新密码规则
    if len(req.new_password) < 6 or len(req.new_password) > 20:
        raise HTTPException(422, "新密码长度需6-20位")
    
    # ③ bcrypt 哈希 + 更新
    new_hash = bcrypt.hash(req.new_password, cost=12)
    table = "admin_accounts" if is_admin(current_user) else "streamer_accounts"
    await db.execute(f"UPDATE {table} SET password_hash = ? WHERE id = ?", 
                     (new_hash, current_user.id))
    
    return {"success": True, "message": "密码修改成功"}
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
| **AI点评**（16维第16项） | 报告解锁时异步逐校调用 | 基于学校+专业+16维数据，生成50-100字口语化点评，不使用"张雪峰"品牌名 | DeepSeek V3 |
| **直播答疑** | 主播在qa.html发送问题 | 10个预设问题模板 + 自由输入，生成200字内口语化直白回答 | DeepSeek V3 |

**异步生成策略**：报告解锁后，前端先渲染15维数据 + 骨架屏占位，后端 Celery 异步队列生成 AI 点评，完成后前端轮询/WebSocket 增量填充。

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
  │补全缺失的  │ │将16维度    │ ├──────┤ │抽样检查    │ │理解主播    │
  │专业/学费/  │ │数据转为    │ │识别   │ │推荐质量    │ │自然语言    │
  │就业数据    │ │口语化解释  │ │倒卖   │ │（同分不同省│ │查询意图    │
  │           │ │           │ │模式   │ │是否差异化）│ │           │
  └──────────┘ └──────────┘ └──────┘ └──────────┘ └──────────┘
```

| Agent | 触发条件 | 能力 | V2计划 |
|-------|----------|------|:---:|
| **数据增强Agent** | 爬虫数据缺失（6类task表pending>0） | 搜索公开信息补全专业名/学费/就业率 | 7月 |
| **推荐解释Agent** | 用户查看报告时 | 将规则引擎输出转为口语化解释 | 8月 |
| **异常检测Agent** | 每次报告生成后 | 检查同主播近N份报告相似度，标记疑似倒卖 | 7月 |
| **质量巡检Agent** | 定时（每日） | 抽样检查推荐结果合理性 | 8月 |
| **用户意图Agent** | V3 SaaS化 | NLU→结构化参数 | 2027 |

---

## 七、技术栈选型

### 7.1 完整技术栈

| 层级 | 技术 | 版本 | 选择原因 |
|------|------|:---:|------|
| **前端** | 原生 HTML/CSS/JS（Bento Grid暗色） | — | 单文件架构，无框架依赖，首屏<2s。v4.0全面采用CSS变量系统 |
| **前端图表** | Canvas API（原生） | — | 饼图+柱状图体积=0KB |
| **PDF生成** | html2canvas(scale:3=300DPI) + jsPDF | 1.4+ / 2.5+ | 前端截图合成；5种水印叠加 |
| **后端框架** | FastAPI (Python) | 0.110+ | 异步原生，自动OpenAPI文档，Pydantic v2验证 |
| **ORM** | SQLAlchemy 2.0 (async) | 2.0+ | 异步操作，事务支持 |
| **数据库驱动** | aiomysql | 0.2+ | FastAPI异步MySQL驱动 |
| **数据库** | MySQL | 8.0 | 现有数据1.17M+，v4.0新增5张数据表 |
| **缓存** | Redis | 7.x | JWT黑名单+分布式锁+L1/L2推荐缓存 |
| **Redis驱动** | redis-py (async) | 5.0+ | 原生async/await |
| **认证** | python-jose (JWT) + bcrypt | 3.3+ / 4.1+ | JWT无状态 + bcrypt cost=12 |
| **LLM客户端** | httpx (直连) | 0.27+ | DeepSeek/Claude API兼容接口 |
| **任务队列** | Celery + Redis (V2) | 5.3+ | 异步AI点评生成、定时巡检（MVP不用） |
| **对象存储** | oss2 (阿里云SDK) | 2.18+ | PDF上云+MySQL备份 |
| **反向代理** | Nginx | 1.24+ | IP直连HTTP(:80)，7个location |
| **进程管理** | systemd | — | gaokao-api.service守护FastAPI |
| **部署** | SCP + Python patch脚本 | — | 避免sed `${}`问题 |

### 7.2 为什么不选其他技术

| 候选 | 不选的原因 |
|------|------|
| **React/Vue** | Bundle size 500KB+ 拖慢首屏；直播投屏不需要SPA的路由/状态管理；单人开发效率不如原生HTML |
| **PostgreSQL** | 现有MySQL存有1.17M数据+20+张表，迁移风险高；MySQL事务+行锁足够 |
| **Node.js** | 旧版已是Python/FastAPI，数据科学操作Python生态更优 |
| **Docker** | MVP阶段单机部署systemd足够，V3 SaaS化时再容器化 |
| **K8s** | 严重过度设计，50并发无需编排 |
| **MongoDB** | 学校/订单/考生数据强关系型，MongoDB增加JOIN复杂度 |

---

## 八、MVP 版本（最小闭环）

### 8.1 MVP 目标

**目标**：主播完成：登录→录入(STEP1)→偏好(STEP2)→分析中→付款墙→解锁→完整报告(16维度)→PDF下载→测下一个。

### 8.2 MVP 功能矩阵

```
P0 (必须):
  ✅ ① 登录 (手机号+密码, JWT)
  ✅ ② 考生信息 (7字段 + 动态选科, 3+3/3+1+2 31省全覆盖)
  ✅ ③ 意向偏好 (4区域输入: 专业/城市/院校搜索/性格)
  ✅ ④ 分析中 (Bento Grid暗色科技风过渡动画 ~1.5s)
  ✅ ⑤ 付款墙 (加密遮蔽 + 剩余次数 + 一键解锁)
  ✅ ⑥ 完整报告 (5大板块, 15校×16维度)
  ✅ ⑦ 报告样板 (静态硬编码演示)
  ✅ ⑧ PDF下载 (html2canvas+jsPDF+5种水印)
  ✅ 管理后台 — 主播CRUD + 充值 + 密码管理(v4.0)
  ✅ 管理后台 — 订单查看

P1 (重要):
  ✅ ⑨ 直播答疑 (10预设问题 + AI回答)
  ✅ 直播模式 (全屏+隐藏导航+大字)
  ✅ 扣费幂等 (idempotency_key)
  ✅ 爬虫数据网关 (crawler_staging 校验)

P2 (不做):
  ❌ 在线支付 (先走线下转账→后台充值)
  ❌ 柱状图/雷达图 (MVP文字展示趋势)
  ❌ 微信小程序 (备案中)
  ❌ Celery异步队列 (同步LLM调用可接受)
  ❌ 专业级数据全量爬取 (渐进式补全)
```

### 8.3 MVP 部署清单

| 项目 | 位置 | 说明 |
|------|------|------|
| 后端代码 | `/root/gaokao-ai/` | FastAPI，systemd守护 |
| 前端主页 | `/www/wwwroot/gaokao.lumenaistudio.co/index.html` | 主播端（Bento Grid暗色） |
| 管理后台 | `/www/wwwroot/gaokao.lumenaistudio.co/admin.html` | 管理员 |
| 直播答疑 | `/www/wwwroot/gaokao.lumenaistudio.co/qa.html` | P1 |
| Nginx配置 | `/etc/nginx/sites-enabled/gaokao-ip` | IP直连HTTP(:80) |
| MySQL | 本地 `gaokao_ai` 库 | 已有数据+v4.0新表 |
| Redis | 本地 :6379 | 缓存+锁 |

---

## 九、V2 扩展方向

### 9.1 扩展路线图

```
MVP (当前)          V2.1 (7月中)            V2.2 (8月)             V3 (2027)
────────           ──────────              ──────────             ─────────
单机部署            Celery 异步队列          在线支付接入            SaaS多租户
同步LLM             AI点评异步预生成          微信/支付宝            独立实例管理
管理员人工充值       Agent数据增强            多主播排行榜           用量计费
线下转账             Agent异常检测            小程序上线             容器化部署
静态报告            Canvas图表(柱状/雷达)     CI/CD                  Agent链+记忆
                    major_similarity完善     城市分析全量爬取
                    6类爬虫任务全量补全        Agent推荐解释
                    PostgreSQL 迁移评估
```

### 9.2 V2 关键架构变化

#### ① Celery 异步任务队列

```
FastAPI                 Celery Worker            Redis (broker)
   │                        │                       │
   ├─ 解锁报告              │                       │
   │  dispatch:             │                       │
   │  celery.send_task(     │                       │
   │    "generate_review",  ├─ consume ────────────►│
   │    args=[order_id]     │                       │
   │  )                     │  ① 查询16维度数据      │
   │                        │  ② 调用LLM生成点评     │
   │                        │  ③ 写入点评缓存       │
   │                        │  ④ WebSocket推送完成  │
   │  ◄── WebSocket通知 ────┤                       │
```

#### ② SaaS 多租户架构（V3）

当前设计对SaaS的兼容性：
- ✅ `streamer_accounts` 已有关联字段，可加 `tenant_id`
- ✅ 扣费系统天然支持按次数计费
- ✅ 管理后台已有充值/订单模型
- ⚠️ 需改造：`tenant_id` 隔离、独立数据库/共享库选型、在线支付网关

---

## 十、部署方案

### 10.1 服务器拓扑（v3.2 — IP 直连 HTTP）

```
┌──────────────────────────────────────────────────────┐
│              生产服务器 121.41.69.234                    │
│  OS: Ubuntu 22.04                                     │
│                                                       │
│  ┌─────────────────┐  ┌─────────────────────────┐    │
│  │ Nginx :80        │  │ FastAPI :8000           │    │
│  │ 反向代理+静态文件  │  │ systemd: gaokao-api     │    │
│  │ IP直连HTTP       │  │ uvicorn workers=4        │    │
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

#### Nginx 配置 (`/etc/nginx/sites-enabled/gaokao-ip`)

```nginx
# IP 直连 HTTP(:80)，无域名，无 SSL
server {
    listen 80;
    server_name 121.41.69.234 localhost 127.0.0.1;

    root /www/wwwroot/gaokao.lumenaistudio.co;
    index index.html;

    # 静态文件
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理
    location /auth/     { proxy_pass http://127.0.0.1:8000/auth/;     proxy_set_header Host $host; proxy_set_header X-Real-IP $remote_addr; }
    location /api/      { proxy_pass http://127.0.0.1:8000/api/;      proxy_set_header Host $host; proxy_set_header X-Real-IP $remote_addr; }
    location /admin/    { proxy_pass http://127.0.0.1:8000/admin/;    proxy_set_header Host $host; proxy_set_header X-Real-IP $remote_addr; }
    location /health    { proxy_pass http://127.0.0.1:8000/health;    proxy_set_header Host $host; }

    # 爬虫数据网关（仅允许爬虫服务器IP访问）
    location /internal/ {
        allow 199.193.126.80;
        deny all;
        proxy_pass http://127.0.0.1:8000/internal/;
        proxy_set_header Host $host;
    }
}
```

### 10.3 部署命令（快速参考）

```bash
# === 后端部署 ===
scp api/services/*.py root@121.41.69.234:/root/gaokao-ai/api/services/
scp api/routers/*.py root@121.41.69.234:/root/gaokao-ai/api/routers/
ssh root@121.41.69.234 "pkill -HUP -f 'uvicorn.*main:app'"
curl -s http://127.0.0.1:8000/health  # → {"status":"ok","mysql":"ok","redis":"ok"}

# === 前端部署 ===
# 备份 → SCP Python patch脚本 → 执行（禁用sed以避免${}问题）
ssh root@121.41.69.234 "cp /www/wwwroot/gaokao.lumenaistudio.co/index.html{,.bak_\$(date +%Y%m%d_%H%M%S)}"
# 执行 Python patch 脚本
ssh root@121.41.69.234 "nginx -t && systemctl reload nginx"

# === 数据库备份 ===
mysqldump gaokao_ai | gzip | ossutil cp - oss://bucket/backup/gaokao_ai_$(date +%Y%m%d).sql.gz
```

### 10.4 监控与告警

| 监控项 | 方式 | 阈值 |
|--------|------|------|
| `/health` 可用性 | cron 每分钟 curl | 连续3次失败→告警 |
| MySQL 连接 | 健康检查内嵌 | 失败→告警 |
| 磁盘使用率 | `df -h` | >80%→告警 |
| 异常扣费 | `SELECT COUNT(*) FROM streamer_accounts WHERE balance < 0` | >0→告警 |
| 爬虫任务堆积 | `SELECT COUNT(*) FROM *_crawl_tasks WHERE status='failed' AND retry_count>=3` | >10→告警 |

---

## 附录 A：v4.0 架构变更对照表

| 变更项 | v1.3 旧版 | v2.0 新版（对齐PRD v4.0） |
|--------|----------|--------------------------|
| 协议 | HTTPS(:443) + Let's Encrypt | HTTP(:80) IP直连 |
| Nginx配置 | `/etc/nginx/sites-enabled/gaokao` | `/etc/nginx/sites-enabled/gaokao-ip` |
| 学校维度 | 14维度 | **16维度**（新增推荐专业详情/学费详情/就业率/薪资/城市5维分析） |
| 数据表 | 11张（无专业明细/学费/就业/薪资/城市/管理员） | **17张**（新增 school_majors, major_similarity, school_tuition, school_employment, school_salary, city_analysis, admin_accounts） |
| 爬虫任务表 | 1张（admission_crawl_tasks） | **6张**（admission/major/tuition/employment/salary/city） |
| 密码管理 | 无 | 主播自助修改 + 管理员重置（v4.0新增） |
| 管理员账号 | 混用streamer表 | 独立 `admin_accounts` 表 |
| PDF水印 | 单一斜纹水印 | **5种水印**（报告编号/防伪声明/斜纹/考生信息卡/二维码） |
| 报告结构 | 3板块 | **5大板块**（封面→核心定位→分层院校→AI建议书→免责声明） |
| 视觉主题 | 浅色 | **Bento Grid 暗色**（Slate 900底色 + Indigo紫） |
| 术语 | 部分"余额" | 全站统一"剩余次数" |
| 点评标签 | 含"张雪峰"品牌 | 统一"💡 点评"（无品牌名） |

## 附录 B：关键技术约束速查表

| 约束 | 要点 |
|------|------|
| **96%学校city为空** | 必须用 `getCityFromSchoolName()` 从校名提取城市，再查城市→省份映射 |
| **山东选科归类** | 阳光高考官方列为3+3，非标杆产品的3+1+2 |
| **上海满分660** | 其余30省750，`SCORE_MAX = { '上海': 660 }` |
| **全站术语** | 统一用"剩余次数"，禁止"余额/金额" |
| **点评标签** | 统一用"💡 点评"，禁止"张雪峰"品牌 |
| **tier分层依据** | `rankProb`（成绩排名推荐率），非 `weightedProb` |
| **低分<400** | 阈值降到5%，意向城市学校加 `_intended_city` 绕过过滤 |
| **★ 特别关注区** | 意向学校独立展示区，不计入15所。0%概率如实标注 |
| **★ 数据差异化** | 不同学校必须显示不同的专业/学费/就业率/薪资/城市分析，禁止全校统一模板 |
| **★ 数据来源标注** | 就业率、薪资须标注数据来源和年份 |
| **★ 专业相似度映射** | 学校无考生意向专业时，通过 `major_similarity` 推荐最相近专业并标注"相近专业" |
| **★ 城市5维分析** | 同城前4维度可缓存复用，第5维度（就业影响）按学校微调 |
| **★ 学费混合策略** | 热门院校全量预爬，冷门院校首次被推荐时异步爬取 |
| **幂等键** | 扣费使用 `crypto.randomUUID()`，同一键重试不重复扣费 |
| **爬虫数据网关** | 爬虫不直连MySQL，必须经 `/internal/crawler/ingest` → staging → 校验 → MERGE |
| **sed/${} 陷阱** | 生产部署禁止用 sed，必用 Python str.replace() |
| **Redis降级** | Redis不可用时扣费降级为纯DB锁，JWT黑名单不检查 |
| **缓存key** | 使用 `hashlib.md5(json.dumps(payload, sort_keys=True))`，禁用Python `hash()` |

---

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-06-16 | 初始架构文档 |
| v1.1 | 2026-06-16 | ★ 推荐引擎重构：前端→后端基于MySQL真实数据 |
| v1.2 | 2026-06-16 | ★ 对齐 PRD v3.1：特别关注区+四层填充+性格经济匹配 |
| v1.3 | 2026-06-17 | ★ ARR硬化的8项修复（幂等/爬虫网关/Redis降级/缓存key/DDL/systemd/监控） |
| **v2.0** | **2026-06-17** | **★ 对齐 PRD v4.0：①16维度学校卡片（新增5张数据表：school_majors/major_similarity/school_tuition/school_employment/school_salary/city_analysis）；②6类爬虫任务表（admission/major/tuition/employment/salary/city）；③管理后台密码管理+admin_accounts独立表；④IP直连HTTP配置（去除SSL/HTTPS）；⑤Bento Grid暗色主题适配；⑥PSF 5种水印；⑦报告5大板块结构；⑧数据真实性治理（差异化呈现+数据来源标注）** |
