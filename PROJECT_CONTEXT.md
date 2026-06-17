# PROJECT_CONTEXT.md — 高考志愿规划师

**最后更新**：2026-06-15  
**生产环境**：`121.41.69.234` / `https://gaokao.lumenaistudio.co/`
**本地备份**：`D:\Dev\GaoKaoAi\`

---

## 1. 项目目标

为高考志愿填报主播提供直播辅助工具。主播登录后输入考生信息（省份、分数、意向城市/学校/专业），系统基于位次数据、录取历史、就业数据生成15所院校推荐报告，支持付费解锁完整报告和PDF下载。

---

## 2. 系统架构

| 层 | 技术栈 | 路径 |
|---|---|---|
| 前端 | 原生 HTML/JS 单页应用 | 服务器 `/www/wwwroot/gaokao.lumenaistudio.co/index.html` |
| JS数据 | 学校库/一分一段/就业/专业排名 | 同目录 `school_data.js` / `yfd_data.js` / `employment_data.js` / `school_major_ranks.js` |
| 后端 API | FastAPI + SQLAlchemy | `/root/gaokao-ai/api/` 端口8000 |
| 异步任务 | Celery + Redis | `/root/gaokao-ai/tasks/` |
| 数据库 | MySQL 8.0 | `127.0.0.1:3306` / `gaokao_ai` |
| 反向代理 | Nginx HTTPS→静态+API | `/etc/nginx/sites-enabled/gaokao` |
| 管理后台 | Vue3 SPA (admin.html) | 同域名 `/admin.html` |
| 爬虫 | 独立服务器 | `199.193.126.80` `/root/fetch_school_facts.py` |

**核心流程**：主播登录（`POST /auth/streamer/login` DB验证）→ 填写学生信息 → 前端 `generateSchools()` 纯JS生成15所推荐 → `renderReport()` 渲染 → 扣费（`POST /auth/streamer/deduct` 原子扣减balance+递增used_total）。

---

## 3. 数据库结构（15张表）

| 表名 | 用途 | 关键字段 |
|------|------|----------|
| `yifenyidang` | 一分一段（分数→位次映射） | province, year, score, cumulative_count |
| `schools` | 学校基础信息 | name, province, level, is_985, is_211 |
| `majors` | 专业目录 | name, category, parent_category |
| `admission_history` | 历年录取数据 | school_id, province, year, min_score, min_rank |
| `employment_data` | 专业就业数据 | major_name, employment_rate, avg_salary |
| `crawl_tasks` | 爬虫任务调度 | task_type, province, year, status |
| `school_admission_crawl_tasks` | 学校录取爬虫 | school_name, year, status |
| `streamer_accounts` | 主播账号 | phone, password_hash, balance, used_total |
| `streamer_recharge_logs` | 主播充值记录 | streamer_id, reset_count, operator |
| `system_config` | 系统配置KV | key_, value_ |
| `users` | C端用户 | phone_encrypted, wx_openid, basic_use_count |
| `orders` | 订单 | user_id, product_type, pay_status, report_status |
| `report_tasks` | 报告生成任务 | order_id, status, priority |
| `promo_codes` | 优惠码 | code, discount_type, max_uses |
| `score_alerts` | 成绩提醒订阅 | user_id, province |

---

## 4. 已完成功能

### 推荐算法（前端 `generateSchools()`）
- **三池机制**：MUST_DIAGNOSE（意向学校）→ TARGET_CITY_POOL（意向城市）→ BACKUP_POOL（本省→邻省→沿海→全国）
- **双推荐率**：成绩排名推荐率（`calcRankProb` 位次比值）+ 加权综合推荐率（35%录取+20%专业+15%就业+10%城市+10%性格+10%经济）
- **Tier分层**：冲刺30-60% / 稳妥60-85% / 保底≥85%，以成绩排名推荐率为准
- **排序优先级**：意向学校(★) → 意向城市学校(●) → rankProb降序
- **城市→省份映射**：60+城市映射表，支持"意向杭州→查浙江学校"
- **低分段适配**：<400分阈值降至5%，纳入专科/民办，兜底池回退分数接近度
- **city字段回退**：96%学校city为空时，通过`getCityFromSchoolName()`从校名提取

### 主播系统
- 登录（`/auth/streamer/login` DB验证 + JWT token）
- 余额显示 + 扣费同步（`POST /auth/streamer/deduct` 原子操作）
- 前端乐观更新 + API失败回滚

### 报告系统
- 付费墙预览（15所学校按tier着色）
- 完整报告（含饼图/院校详情/专业分析/就业数据/AI建议）
- PDF下载（html2canvas + jsPDF）
- 报告编号 + 防伪标识

### 管理后台
- Vue3 SPA (`admin.html`)
- 主播管理（CRUD + 充值 + 状态切换）
- 订单/报告查看

---

## 5. 已修复Bug（禁止再次修改）

| Bug | 修复方式 | 不可回退原因 |
|-----|----------|-------------|
| 登录报"未找到账号数据" | `doLogin()` 从localStorage改为`fetch('/auth/streamer/login')`；nginx变量污染修复 | 核心登录链路 |
| 扣费未同步后端 | 新增`/auth/streamer/deduct`端点 + 前端乐观更新+回滚 | 余额永久不准 |
| 意向城市学校不出现 | `_city_match` 增加城市→省份映射；跨省宽口径查询 | 核心推荐逻辑 |
| 意向学校不出现 | `_merge_must_diag` 改为`diag_recs + recs`（不限数量，置顶） | 用户明确要求 |
| 意向学校被模糊匹配替代 | 纯精确匹配 `===` + 去重保护（子串名跳过） | 防"广州大学松田学院"→"广州大学" |
| 低概率无效推荐 | 成绩排名推荐率<30%移除 + `filtered.sort()`按tier排序 | 用户明确要求 |
| 分数超上限可保存 | `updateRankEst()`自动钳制+提示 | 数据质量 |
| 城市标签合并 | 拆分为独立城市芯片 | UI需求 |
| 专业太少 | 扩充到26个细分专业 | UI需求 |
| 付费墙着色错位 | 按实际tier替代位置索引 | 06-15修复 |
| 饼图/报告/PDF硬编码"5所" | 预计算`_tierTotals`动态显示 | 06-15修复 |
| PDF生成挂死 | `buildPDFWrap`补充`_tierTotals`局部计算 | 06-15修复 |
| 低分段城市学校全被过滤 | 城市池移除`rp>=30`门槛，标记`_intended_city` | 06-15修复 |
| 低分段兜底池全空 | 空池回退到分数接近度排序 | 06-15修复 |
| 过滤阈值对低分过严 | <400分阈值5%，纳入专科/民办 | 06-15修复 |
| 意向学校未置顶（同tier） | 排序加三级优先级：★→●→rankProb | 06-15修复 |
| 96%学校prov字段丢失 | `getCityFromSchoolName()`+`CITY_PROV`双重回退 | 06-15修复 |

---

## 6. 已废弃方案（禁止再次引用）

- **旧版localStorage登录**：已替换为fetch API + Bearer token
- **模糊城市匹配（in/contains）**：已替换为标准化后严格等值
- **位置索引着色（`i<3 ? red`）**：已替换为实际tier着色
- **前台扣费不调后端**：已新增同步扣费端点
- **推荐列表忽略意向学校**：已改为强制纳入+置顶
- **整文件重写部署方式**：已改为服务器端最小片段替换

---

## 7. 当前待办任务

| # | 任务 | 优先级 |
|---|------|--------|
| 1 | PDF报告样式优化：概率百分比和学校标签字体缩小，确保一行显示 | 中 |
| 2 | 后端AI接口恢复：`POST /recommendation/pro` Anthropic API调用失败返回503，需检查API Key/Base URL | 高 |
| 3 | `getCityFromSchoolName`词典扩充：约4%学校（如"中国科学院大学"）无法提取城市，需增加关键词 | 低 |
| 4 | 自动化测试：当前无pytest/playwright覆盖前端推荐算法，全部依赖手动验证 | 中 |
| 5 | `PROVINCE_SCHOOL_SCORES`数据加载链路确认：样本页不加载此数据，影响非登录态测试 | 低 |

---

## 8. 下一步开发计划

1. **后端AI接口恢复**：排查Anthropic API连通性，确认环境变量`ANTHROPIC_BASE_URL`和API Key配置正确
2. **算法增强**：当前推荐仅依赖位次比值和静态权重，可引入历年录取趋势、大小年分析、专业级录取概率
3. **前端测试覆盖**：为`generateSchools()`、`renderReport()`、`calcRankProb()`编写puppeteer测试
4. **性能优化**：`SCHOOLS` 2673条全量加载，考虑按省份懒加载；`YIFENYIDANG` 30省份可拆分
5. **部署自动化**：当前靠SCP+sed手工部署，可引入CI/CD（GitHub Actions→服务器rsync）
