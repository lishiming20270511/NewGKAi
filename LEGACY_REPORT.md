# LEGACY_REPORT.md — 高考志愿规划师 交接报告

**生成日期**：2026-06-15  
**代码来源**：`https://gaokao.lumenaistudio.co/index.html`（414KB单文件）

---

## 一、当前功能列表

| 模块 | 功能 | 状态 |
|------|------|------|
| 主播登录 | 手机号+密码 → JWT token → 余额查询 | ✅ |
| 考生信息 | 省份、分数、选科、排名估算 | ✅ |
| 意向偏好 | 城市（多选）、学校（最多3所）、专业（26个）、性格、经济状况 | ✅ |
| 推荐算法 | 三池机制 + 双推荐率 + tier分层 + 地域优先级 | ✅ |
| 付费墙 | 15所学校预览，按tier着色，余额扣费 | ✅ |
| 完整报告 | 饼图 + 院校卡片(985/211标签/概率/专业/就业/城市分析/AI点评) | ✅ |
| PDF下载 | html2canvas + jsPDF，含封面+院校列表+汇总表 | ✅ |
| 报告样板 | 硬编码560分河南示例，独立于算法 | ✅ |
| 直播答疑 | QA预设问题 + AI回答 | ✅ |
| 直播模式 | 全屏展示适配 | ✅ |
| 管理后台 | Vue3 SPA（admin.html），主播CRUD + 充值 + 订单查看 | ✅ |
| 爬虫 | 独立服务器199.193.126.80，fetch_school_facts.py | ✅ |
| 后端API | FastAPI + Celery，15个路由模块 | ✅ |

---

## 二、已知Bug列表（未修复）

| # | Bug | 影响范围 | 优先级 |
|---|-----|---------|--------|
| 1 | PDF概率百分比和学校标签字体偏大，一行显示不下 | 报告 | P1 |
| 2 | `POST /recommendation/pro` 503，Anthropic API调用失败 | 后端AI | P0 |
| 3 | `getCityFromSchoolName`约4%学校无法提取城市（如"中国科学院大学"） | 推荐算法 | P1 |
| 4 | 前端推荐算法无自动化测试，全部依赖手动验证 | 质量保障 | P1 |
| 5 | `PROVINCE_SCHOOL_SCORES`样本页不加载，非登录态无法测试 | 测试环境 | P2 |
| 6 | `SCHOOLS`2673条全量加载，`YIFENYIDANG`30省份全量加载 | 性能 | P2 |
| 7 | 部署依赖手工SCP+sed/Python脚本，无CI/CD | 运维 | P2 |

---

## 三、哪些模块最混乱

### 🔴 混乱度：高

**1. `generateSchools()`（约400行，前端核心算法）**
- 问题：单一函数包含三池填充、概率计算、tier重分配、过滤、补位、排序六阶段逻辑，无分层抽象
- 两套SCHOOL_POOL构建路径（PROVINCE_SCHOOL_SCORES vs SCHOOLS），数据结构不一致
- tier先按位置分配，再按rankProb重算，两步赋值逻辑互相覆盖
- calcRankProb内置`Math.random()`，同一学校多次调用结果不同，不可复现
- 城市池、兜底池、补位池三处过滤条件各异，修改一处容易影响其他

**2. `index.html`（414KB单文件）**
- 问题：HTML/CSS/JS全部内联，无模块拆分
- 全局变量污染：`student`、`SCHOOLS`、`YIFENYIDANG`等全部挂在window
- CSS内联样式+类样式混用，选择器优先级混乱
- 与6个外部JS文件（school_data.js等）通过`<script>`标签耦合，无模块加载机制

**3. SCHOOLS数据（2673条）**
- 问题：96%条目city字段为空，prov字段依赖CITY_PROV从city派生，间接丢失
- 数据来源不明（可能是爬虫或手工整理），无数据字典文档
- 与PROVINCE_SCHOOL_SCORES数据结构不完全兼容（后者有v[3]省份字段，前者无）

### 🟡 混乱度：中

**4. `renderReport()` + `buildPDFWrap()` 双份渲染**
- 问题：完整报告和PDF各有一套DOM构建代码，修改样式需同步两处
- `_tierTotals`需在两处独立定义（已修复挂死，但结构脆弱）
- PDF封面、院校卡片、汇总表等子模块未抽离为独立函数

**5. 概率计算系统**
- 问题：`calcRankProb()`纯位次比值+随机扰动，无统计模型
- `calcWeightedProb()`六维度固定权重（35/20/15/10/10/10），无数据驱动校准
- 两套概率（成绩排名推荐率 vs 加权综合推荐率）概念相近，用户容易混淆

**6. 付费/认证系统**
- 问题：`doDirectUnlock()`乐观更新+setTimeout 800ms异步渲染，时序脆弱
- streamerToken存window全局变量，无过期刷新机制
- nginx变量污染历史问题（`$host`等被PowerShell替换），排查困难

### 🟢 混乱度：低

**7. 后端API** — FastAPI分层清晰（routers/services/schemas/utils），Celery任务独立文件
**8. 管理后台** — Vue3 SPA，单文件admin.html，相对独立
**9. 数据库** — schema清晰，15张表职责明确

---

## 四、数据结构现状

### 前端核心数据结构

```
student = {
  score, province, rank,      // 基本信息
  majors[],                    // 意向专业（多选）
  cityPreference[],            // 意向城市（如["厦门","杭州"]）
  intendedSchools[],           // 意向学校（如[{name:"北京大学",major:"计算机"}], 最多3所）
  personality[],               // 性格标签（如["外向","钻研"]）
  economy,                     // 经济状况：'良好'/'一般'/'困难'
  nick, adjust, subjects[]     // 辅助字段
}
```

```
推荐结果项 = {
  name, score985, tags[],      // 学校基础信息
  city, prov,                  // 城市+省份（96%需getCityFromSchoolName回退）
  major,                       // 推荐专业
  tier,                        // 0冲刺/1稳妥/2保底
  rankProb,                    // 成绩排名推荐率（0-99）
  weightedProb,                // 加权综合推荐率（0-99，六维度）
  _intended,                   // 标记：意向学校，强制置顶
  _intended_city               // 标记：意向城市学校，强制保留
}
```

### 数据库核心表（15张）

| 表 | 记录数（估算） | 数据来源 |
|----|--------------|---------|
| yifenyidang | 30省×4年×约300分数点≈36K | 爬虫 |
| schools | 约3K | 爬虫+手工 |
| admission_history | 学校×省份×年份 ≈ 50K+ | 爬虫 |
| employment_data | 110条 | 麦可思报告 |
| streamer_accounts | <10 | 后台手工创建 |
| 其余表 | <1K | 业务产生 |

### 前端外部数据文件

| 文件 | 大小 | 内容 |
|------|------|------|
| school_data.js | 2.1MB | `SCHOOLS`数组，2673条 |
| yfd_data.js | 102KB | `YIFENYIDANG`对象，30省份×4年 |
| employment_data.js | 11KB | 就业数据 |
| school_major_ranks.js | 313KB | 专业排名数据 |
