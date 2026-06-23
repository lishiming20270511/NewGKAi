# AI高考志愿规划师 — 开发任务拆分

**生成日期**：2026-06-23  
**基于文档**：PRD_v5.md（v5.5）/ BugReport.md / CURRENT_TASK.md / LOCKED_TASKS.md / Architecture.md / superpowers/specs & plans  
**原则**：每任务 2–4 小时；最小改动；不碰锁定模块（LOCKED_TASKS.md）；涉及 recommendation.py 核心逻辑须先获用户审批。

---

## 优先级说明

| 级别 | 含义 |
|------|------|
| P0 | 生产阻断 / 严重误导，立即修 |
| P1 | 主要功能缺失，本周完成 |
| P2 | 体验优化，下周完成 |

---

## 模块一：Bug 修复

### TASK-01：BUG-011 冲刺档回填概率上限 + 邻省省重点扩展

| 属性 | 内容 |
|------|------|
| **优先级** | P0 |
| **状态** | ✅ 已完成（v5.19 + 测试 14/14 PASS） |
| **预计工时** | 2–3 h |
| **文件** | `api/services/recommendation.py` / `scripts/test_bug011.py` |

**需求来源**：BUG-011（BugReport.md）、设计稿 `docs/superpowers/specs/2026-06-21-bug011-sprint-tier-fix-design.md`、实施计划 `docs/superpowers/plans/2026-06-21-bug011-sprint-tier-fix.md`

**工作内容**（四处聚焦改动，按已批准方案 A 执行）：
1. `SchoolRecord` 新增字段 `is_neighbor_province: bool = False`
2. `build_candidate_pool` L3 段：对每所邻省学校打标 `is_neighbor_province = True`
3. 新增辅助函数 `_is_provincial_key(school)` — 判断省属重点公办一本（排除精英/职业/民办）
4. `apply_quality_threshold_filter` 高分段 tier=0 条件：`_is_elite(s) or (s.is_neighbor_province and _is_provincial_key(s))`
5. `sort_and_slice` globe_candidates 列表推导式加过滤：`(s.rank_prob or 0) < TIER_SOLID_MIN + 5`
6. `sort_and_slice` remaining_asc 列表推导式加相同过滤（last resort）

**验收**：`python scripts/test_bug011.py` 全部 PASS；上海 588 分测试用例冲刺档返回 5 所且概率均 < 55%

> ⚠️ **锁定约束**：不得修改 TIER_BOOST_MIN / 回填顺序 / tier=-1 精英回填策略（L2-01 至 L2-03）

---

### TASK-02：BUG-019 专业意向匹配过滤层（后端）

| 属性 | 内容 |
|------|------|
| **优先级** | P0 |
| **状态** | ✅ 已完成（v5.20，`_SPECIALTY_SCHOOL_MARKERS` + `_MAJOR_EXCLUDED_SPECIALTIES` + `apply_major_type_filter` + `major_match_label` 字段） |
| **预计工时** | 3–4 h |
| **文件** | `api/services/recommendation.py` |

**需求来源**：BUG-019（BugReport.md）、PRD §4.9

**工作内容**：
1. 在文件顶部定义映射常量 `MAJOR_DISCIPLINE_MAP`：26 个考生意向专业标签 → 学科门类 + 允许/排除院校类型（按 PRD §4.9.2 表格实现）
2. 新增函数 `_get_allowed_disciplines(major_prefs)`：将考生意向专业列表解析为允许学科门类集合
3. 新增函数 `apply_major_type_filter(pool, allowed_disciplines, intended_ids, db)`：
   - 查 `school_majors` 表判断每所学校是否开设允许学科门类下的专业
   - 意向院校豁免过滤，但附注 `⚠️ 该校暂无[意向专业]相关专业，请确认报考意向`
   - 无匹配学科门类 → 从推荐池移除；移除后不足 15 所时重新触发四层填充
4. 在 `generate_recommendation` 中，于 Tier 分层之前调用（仅当 `major_preference` 非空时）
5. 学校数据组装新增字段 `major_match_label`（✅/🔶/⚠️ 三种）

**验收**：
- 计算机/理工意向 → 北京舞蹈学院、北京体育大学不出现在推荐池
- 医学意向 → 北外、政法、师范等无医学院的学校不出现
- 意向院校无论专业匹配与否均出现在特别关注区并附加 ⚠️ 说明

> ⚠️ **审批要求**：修改 recommendation.py 核心逻辑前须在对话中获得用户明确同意（LOCKED_TASKS.md §六）

---

### TASK-03：BUG-020 院校地理数据修正（湖北及其他省份）

| 属性 | 内容 |
|------|------|
| **优先级** | P1 |
| **状态** | ✅ 已完成（v5.19，`_SCHOOL_CITY_OVERRIDES` 补录湖北文理学院→襄阳、湖北民族大学→恩施及其他湖北非武汉院校） |
| **预计工时** | 1–2 h |
| **文件** | `api/services/recommendation.py`（`_SCHOOL_CITY_OVERRIDES` 常量） |

**需求来源**：BUG-020（BugReport.md）

**工作内容**：
1. 找到 `CITY_OVERRIDES` 常量（参考 BUG-015 修复方式）
2. 补录两条确认错误：`"湖北文理学院": "襄阳"` / `"湖北民族大学": "恩施"`
3. 核查湖北省全部非武汉城市院校（黄石、荆州、宜昌、十堰、孝感等），逐一补录发现的错误
4. 回归测试：陈彤（595 分，医学意向，意向城市武汉）推荐结果中以上两校城市显示正确

**验收**：湖北文理学院显示"襄阳"，湖北民族大学显示"恩施"；不影响武汉本地院校

---

### TASK-04：BUG-021 专业详情降级展示（前端）

| 属性 | 内容 |
|------|------|
| **优先级** | P1 |
| **状态** | ✅ 已完成（v5.19，index.html 新增 `.data-pending` 样式，推荐专业/就业率/薪资/专业地位字段空值降级显示"暂无数据，持续完善中"） |
| **预计工时** | 1–2 h |
| **文件** | `frontend/index.html` |

**需求来源**：BUG-021（BugReport.md）

**工作内容**：
1. 找到报告渲染函数中学校卡片的专业详情板块（专业介绍、就业前景、学科实力评级、专业地位）
2. 每个字段加空值检测：null / 空字符串 → 显示 `<span class="data-pending">暂无数据，持续完善中</span>` 而非空白
3. 同步修改 PDF 渲染对应函数，保持一致

**验收**：专业详情空白区域全部替换为降级文案；有数据时正常展示；JS 语法验证无报错

---

## 模块二：PC 全宽布局迁移（方案 C）

> **背景**：PRD §6.2（2026-06-23 决策）废弃方案A暗色Bento Grid和375px竖屏手机框，切换为方案C浅色清朗主题+PC全宽布局（max-width: 1280px，内容区 1000px，字号+1档，输入框 44px）。

### TASK-05：PC全宽基础框架 + 方案C主题色迁移

| 属性 | 内容 |
|------|------|
| **优先级** | P1 |
| **状态** | ✅ 已完成（v5.21） |
| **预计工时** | 3–4 h |
| **文件** | `frontend/index.html` |

**工作内容**（仅改 CSS 层，不动业务逻辑）：
1. 将顶层手机框容器（375px×800px，overflow hidden）改为 `max-width: 1280px; margin: 0 auto; overflow: auto`
2. 内容区设 `max-width: 1000px; margin: 0 auto`
3. 将 CSS 变量替换为方案C色值：
   - 页面背景：`#F5F7FA` / 卡片：`#FFFFFF` / 主文字：`#1E293B` / 次级：`#64748B`
   - 边框：`#E2E8F0` / CTA 按钮：`#3B82F6` / 冲刺红：`#EF4444` / 保底绿：`#22C55E`
   - 985标签：`#F59E0B` / 211标签：`#8B5CF6` / 双一流标签：`#06B6D4`
   - 圆角：卡片 `10px` / 小元素 `6px`；阴影：`0 1px 3px rgba(0,0,0,0.08)`
4. 全局字号上调一档：基础正文 16px，次级 14px，表单 Label 15px，卡片标题 18px，页面大标题 24px，最小 13px
5. 顶部导航栏改为水平完整展开（不再挤压在手机框内）

**验收**：页面在 1280px 宽下无横向滚动条；手机框消失；方案C配色生效；JS 语法验证无报错

---

### TASK-06：登录页 + STEP1 考生信息页 PC 适配

| 属性 | 内容 |
|------|------|
| **优先级** | P1 |
| **状态** | ✅ 已完成（v5.22） |
| **预计工时** | 2–3 h |
| **文件** | `frontend/index.html` |

**工作内容**：
1. **登录页**：表单居中最大宽度 480px；输入框高度 44px；主按钮高度 48px；宣传文案 5 条竖排展示在表单下方
2. **STEP1**：7 字段表单双列布局（宽屏左右两列）；省份/分数/位次一行；选科组件全宽展示；标签芯片 padding: 6px 14px；字段间距 24px
3. 所有输入框/下拉框统一高度 44px

**验收**：1280px 下登录表单居中、STEP1 双列布局正常；窄至 1024px 时退化为单列；JS 语法验证无报错

---

### TASK-07：STEP2 意向偏好页 + 付款墙 PC 适配

| 属性 | 内容 |
|------|------|
| **优先级** | P1 |
| **状态** | ✅ 已完成（v5.22） |
| **预计工时** | 2–3 h |
| **文件** | `frontend/index.html` |

**工作内容**：
1. **STEP2**：4 个区域（专业/城市/院校/性格）宽屏下 2×2 网格布局；专业 26 个标签换行展示不溢出；城市预设标签 + 自定义输入框并排
2. **付款墙**：加密遮蔽区域横向拉伸至内容区全宽；院校列表卡片横排；CTA 按钮蓝色 `#3B82F6`，高度 48px；遮罩对比度保证可见

**验收**：STEP2 四区域 2×2 布局；付款墙遮蔽在浅色背景下清晰可见；JS 语法验证无报错

---

### TASK-08：完整报告页 PC 布局优化

| 属性 | 内容 |
|------|------|
| **优先级** | P1 |
| **状态** | ✅ 已完成（v5.22） |
| **预计工时** | 3–4 h |
| **文件** | `frontend/index.html` |

**工作内容**：
1. 封面信息区域横向展开（考生信息 + AI 推理引擎说明并排）
2. 特别关注区（★）置顶独立展示，视觉区分于 15 所推荐
3. 15 所学校卡片改为网格布局（宽屏 2 列）；冲刺/稳妥/保底分组标题方案C色彩（红/蓝/绿）
4. 三档横向对比表全宽展示
5. 板块四（AI 建议书）段落间距放宽，标题 24px
6. 底部按钮区（下载PDF / 测下一个 / 直播答疑）横排展示

> ⚠️ **锁定约束**：不修改 PDF 生成函数（`buildPDFWrap` 及相关 `build*Page` 函数）；不修改 `_tierTotals` 计算逻辑；不修改报告章节顺序（LOCKED_TASKS L3）

**验收**：报告页 1280px 下两列卡片布局正常；分层颜色与方案C一致；PDF 下载功能未受影响

---

### TASK-09：s.html 亮色主题改造（BUG-014-2）

| 属性 | 内容 |
|------|------|
| **优先级** | P2 |
| **状态** | 待开发 |
| **预计工时** | 2–3 h |
| **文件** | `frontend/s.html` |

**需求来源**：BUG-014-2（BugReport.md）

**工作内容**：
1. 页面背景 `#F5F7FA`，卡片 `#FFFFFF`，主文字 `#1E293B`，次级 `#64748B`
2. 表单、按钮、标签芯片样式与 index.html 方案C保持一致（参考 TASK-05）
3. PC端专用提示横幅样式改为方案C警告色，内容保持不变
4. 布局适配 PC 宽屏（参考 index.html STEP1/STEP2 布局）

> ⚠️ **锁定约束**：不修改 `/s/validate` 接口字段（L5-01）；不修改 PDF 生成代码（已锁定）

**验收**：s.html 亮色主题正常；PDF 下载功能未受影响

---

## 模块三：主播助手新功能

> **背景**：PRD v5.4 Page⑧ 将"直播答疑"升级为"主播助手"，双 Tab：Tab A 直播话术（管理员后台维护）+ Tab B AI问答（犀利风格）。后端需要 `broadcast_scripts` 表和 API。

### TASK-10：broadcast_scripts 表 + 话术 CRUD API（后端）

| 属性 | 内容 |
|------|------|
| **优先级** | P1 |
| **状态** | 待开发 |
| **预计工时** | 3–4 h |
| **文件** | `api/routers/admin.py`（或新建 `api/routers/scripts.py`）；数据库 DDL |

**工作内容**：
1. 确认/新建 `broadcast_scripts` 表：
   ```sql
   CREATE TABLE broadcast_scripts (
       id INT AUTO_INCREMENT PRIMARY KEY,
       category VARCHAR(64) NOT NULL COMMENT '分类名',
       title VARCHAR(128) NOT NULL COMMENT '话术标题',
       content TEXT NOT NULL COMMENT '话术正文',
       sort_order INT NOT NULL DEFAULT 0 COMMENT '同分类内排序',
       status ENUM('active','disabled') NOT NULL DEFAULT 'active',
       created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
       updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
       INDEX idx_category (category),
       INDEX idx_sort (category, sort_order)
   ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
   ```
2. 管理员接口（`/admin/scripts/`，Admin JWT）：
   - `GET /admin/scripts` — 分类分组列表
   - `POST /admin/scripts` — 新增话术（category, title, content）
   - `PUT /admin/scripts/{id}` — 编辑话术
   - `DELETE /admin/scripts/{id}` — 删除话术
   - `PUT /admin/scripts/{id}/sort` — 更新排序
   - `GET /admin/scripts/categories` — 获取所有分类名
3. 主播读取接口（`/api/scripts`，主播 JWT）：`GET /api/scripts` — 分类分组列表
4. 预置 5 个默认分类：开播话术 / 产品介绍 / 报告讲解 / 收单话术 / 常见异议处理

**验收**：`GET /api/scripts` 返回正确分类结构；CRUD 幂等正确；Admin JWT 限制生效

---

### TASK-11：主播助手页面 Tab A — 直播话术（前端）

| 属性 | 内容 |
|------|------|
| **优先级** | P1 |
| **状态** | 待开发（依赖 TASK-10） |
| **预计工时** | 3–4 h |
| **文件** | `frontend/index.html` |

**工作内容**：
1. 将 Page⑧（原直播答疑/QA页）改为双 Tab 结构，Tab A "直播话术" + Tab B "AI问答"
2. **Tab A 直播话术**：
   - 页面加载时调用 `GET /api/scripts` 获取话术列表
   - 按分类折叠展开（Accordion），默认全部收起；分类标题带话术数量角标
   - 每条话术卡片：标题 + 正文（超 3 行折叠）+ **一键复制按钮**（Toast 提示"已复制"）
   - 加载中骨架屏；API 失败时提示"话术加载失败，请刷新"

**验收**：Tab A 话术列表加载正常；折叠展开正确；复制功能生效；JS 语法验证无报错

---

### TASK-12：主播助手页面 Tab B — AI 问答（前端）

| 属性 | 内容 |
|------|------|
| **优先级** | P1 |
| **状态** | 待开发（依赖 TASK-11 中双Tab结构） |
| **预计工时** | 2–3 h |
| **文件** | `frontend/index.html` |

**工作内容**（复用现有 QA 模块逻辑，移入 Tab B）：
1. 10 个预设快捷问题按钮（按 PRD §Page⑧ 列表），点击填入输入框
2. 文本输入框（100 字限制，超限提示）+ 提交按钮
3. 调用现有 `POST /api/qa/ask` 接口（Bearer token）
4. AI 回答展示：卡片样式，回答 ≤ 200 字，默认犀利直接风格（无需切换）
5. 本次会话问答历史列表（滚动，最近在上）；"清空历史"按钮；加载中 spinner（防重复提交）

**验收**：预设问题一键填入；AI 回答正常返回；历史清空正常；JS 语法验证无报错

---

### TASK-13：管理后台话术管理模块

| 属性 | 内容 |
|------|------|
| **优先级** | P1 |
| **状态** | 待开发（依赖 TASK-10） |
| **预计工时** | 3–4 h |
| **文件** | `frontend/admin.html` |

**工作内容**：
1. 管理后台顶部标签栏新增"话术管理"Tab
2. **话术列表**：按分类分组展示，每条显示分类/标题/状态；支持按分类筛选
3. **新增话术弹窗**：分类下拉（含"新建分类"选项）+ 标题 + 正文多行文本框 + 保存
4. **编辑话术**：点击编辑弹窗预填旧内容，PUT 接口提交
5. **删除话术**：确认弹窗 → DELETE 接口
6. **分类排序（简化版）**：上移/下移按钮调整同分类内顺序（调用 sort 接口）

**验收**：管理员可完成话术增删改；分类展示正确；操作后列表实时刷新

---

## 模块四：管理后台一次性链接管理

### TASK-14：管理后台一次性链接管理模块

| 属性 | 内容 |
|------|------|
| **优先级** | P1 |
| **状态** | ✅ 已完成（T12.1~T12.3，后端 `api/routers/one_time_links.py` 含生成/列表/详情/作废批次接口；`admin.html` 已有"🔗 一次性链接"Tab） |
| **预计工时** | 3–4 h |
| **文件** | `frontend/admin.html`；`api/routers/one_time_links.py` |

**工作内容**：
1. **核实/补充后端接口**（如缺失则新增）：
   - `POST /admin/links/batch` — 批量生成一次性链接（参数：count 1-100，note 备注）
   - `GET /admin/links/batches` — 批次列表（总数/已使用/未使用/生成时间/备注）
   - `GET /admin/links/batches/{batch_id}` — 批次详情（每条链接状态）
   - `POST /admin/links/batches/{batch_id}/invalidate` — 作废整批未使用链接
2. **管理后台 UI（admin.html 新增 Tab "链接管理"）**：
   - **生成区**：数量输入（1-100）+ 备注文本框 + "生成链接"按钮
   - **生成结果弹窗**：链接列表（每条可独立复制）+ "一键复制全部" + "下载TXT文件"（`链接批次_[备注]_[日期].txt`）
   - **批次看板表格**：批次备注、总数、已使用、未使用、生成时间；"查看详情"/"作废整批"操作

> 链接安全（已实现则复用）：UUID v4 + HMAC 签名、`one_time_links` 行锁防重复消费（L5-01/L5-02 锁定，不可改）

**验收**：管理员可批量生成 10 条链接并复制；批次状态看板数据准确；作废整批后链接不可用

---

## 任务依赖关系

```
TASK-01 (BUG-011)         ── 无依赖，可立即开始
TASK-02 (BUG-019)         ── 无依赖，但需用户审批
TASK-03 (BUG-020)         ── 无依赖，可立即开始
TASK-04 (BUG-021前端)     ── 无依赖，可立即开始

TASK-05 (PC基础框架)      ── 无依赖，可立即开始
TASK-06 (登录+STEP1)      ── TASK-05
TASK-07 (STEP2+付款墙)    ── TASK-05
TASK-08 (完整报告)         ── TASK-05
TASK-09 (s.html亮色)      ── TASK-05（参考方案C变量）

TASK-10 (话术API后端)     ── 无依赖
TASK-11 (Tab A 话术前端)  ── TASK-10 + TASK-05
TASK-12 (Tab B AI问答)    ── TASK-11（共享双Tab结构）
TASK-13 (管理后台话术)    ── TASK-10

TASK-14 (链接管理)        ── 无依赖（后端可能已有）
```

---

## 并行开发建议

| 并行组 | 任务 | 备注 |
|--------|------|------|
| 可立即并行 | TASK-01 + TASK-03 + TASK-05 | Bug修复与PC框架同步推进 |
| 后端先行 | TASK-02（审批后）+ TASK-10 | 后端API先完成，前端依赖 |
| 前端页面适配 | TASK-06 + TASK-07（TASK-05完成后） | 两人可各负责一个STEP |
| 管理后台 | TASK-13 + TASK-14（TASK-10完成后） | 同一文件内不同Tab |

---

## 总工时估算

| 模块 | 任务数 | 估计总工时 |
|------|--------|-----------|
| Bug 修复 | 4 | 9–13 h |
| PC 全宽布局迁移 | 5 | 12–17 h |
| 主播助手功能 | 4 | 11–15 h |
| 链接管理 | 1 | 3–4 h |
| **合计** | **14** | **35–49 h** |

---

*本文档仅为任务拆分，不包含实施步骤。实施前请查阅对应设计文档（superpowers/specs/）和锁定约束（LOCKED_TASKS.md）。*
