# AI高考志愿规划师 — 开发任务拆分 v3.0

| 文档信息 | 内容 |
|---------|------|
| 产品名称 | AI高考志愿规划师 · 直播辅助工具 |
| 上级文档 | [PRD_v5.md](./PRD_v5.md) v5.4 · [Architecture.md](./Architecture.md) v2.1 |
| 创建日期 | 2026-06-19 |
| 覆盖版本 | PRD v5.3 算法升级 + PRD v5.4 新功能 + 遗留Bug |
| 前置状态 | Phase 1-10（v5.10）全部完成，本文档仅列**剩余未完成任务** |

---

## 一、架构评估与调整说明

### 现状
Architecture.md 当前版本 v2.1，对齐 PRD v5.2。核心架构（FastAPI + MySQL + Redis + Nginx + 单文件前端）**无需大改**，可满足所有新需求。

### 需要调整的内容

| 变更类型 | 具体内容 | 影响范围 |
|---------|---------|---------|
| **新增数据表（4张）** | `province_cutoffs`、`province_cutoff_crawl_tasks`、`one_time_links`、`broadcast_scripts` | MySQL DDL |
| **新增后端模块** | 一次性链接（admin生成/学生校验）、话术管理（admin CRUD/streamer只读） | FastAPI routers |
| **新增前端页面** | Page⑧ 升级为主播助手（双Tab）、Page⑨ 学生自助报告页（`/s.html` 独立页） | index.html / s.html |
| **推荐引擎算法扩展** | §4.7 成绩段位前置判断、§4.8 院校质量底线、§4.1.2 三档统一地域扩展 | recommendation.py |
| **Nginx 新增路由** | `/s` → `s.html` 静态页 | nginx 配置 |

### 不需要调整的内容
- 扣费系统（原子事务 + 幂等）保持不变
- JWT 认证体系保持不变
- 爬虫数据网关保持不变
- Redis 缓存策略保持不变
- Celery 保持 P2 暂不引入

---

## 二、任务总览

```
Phase 11: 算法升级（PRD v5.3 §4.7/4.8/4.1.2）  3个任务，~10h
Phase 12: 一次性链接系统（PRD v5.4）             3个任务，~12h
Phase 13: 主播助手页面（PRD v5.4 Page⑧升级）     3个任务，~10h
Phase 14: 遗留Bug + 细节完善                      2个任务，~ 4h
Phase 15: 集成验证与生产部署                       2个任务，~ 6h
                                            ─────────────────────
                                            13个任务，约 42h
```

---

## Phase 11：算法升级（PRD v5.3）

> **背景**：PRD v5.3 新增成绩段位判断（§4.7）和院校质量底线（§4.8），用于修复 Bug #8（高分冲刺档为空）和 Bug #9（高分保底出现职业技术学校）。同时升级三档地域扩展规则（§4.1.2）。

---

### T11.1 · province_cutoffs 数据表 + 种子数据

| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T1.2（基础DB已就绪） |
| **负责人** | 后端/数据 |
| **解决问题** | 为 §4.7 成绩段位判断提供数据基础 |

**为什么需要**：PRD §4.7 要求在推荐引擎执行前查询 `province_cutoffs` 表判断考生处于高分段/中分段/低分段，进而应用不同的院校质量底线规则。

**任务清单**：

- [ ] **建表**：在 MySQL `gaokao_ai` 库中创建 `province_cutoffs` 表：
  ```sql
  CREATE TABLE province_cutoffs (
      id           INT AUTO_INCREMENT PRIMARY KEY,
      province     VARCHAR(32) NOT NULL COMMENT '省份',
      subject_category VARCHAR(16) NOT NULL COMMENT '科类（物理/历史/综合）',
      year         INT NOT NULL COMMENT '年份',
      cutoff_yiben INT DEFAULT NULL COMMENT '一本/本科最低控制线',
      cutoff_zhuanke INT DEFAULT NULL COMMENT '专科最低控制线',
      created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      UNIQUE KEY uk_prov_sub_year (province, subject_category, year),
      INDEX idx_province (province)
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='省份录取控制线（一本线/专科线）';
  ```

- [ ] **建表**：创建 `province_cutoff_crawl_tasks` 爬虫任务表（同6类爬虫任务表结构，`city_name` 改为 `province + subject_category`）：
  ```sql
  CREATE TABLE province_cutoff_crawl_tasks (
      id              INT AUTO_INCREMENT PRIMARY KEY,
      province        VARCHAR(32) NOT NULL,
      subject_category VARCHAR(16) NOT NULL,
      year            INT NOT NULL,
      status          ENUM('pending','running','done','failed') NOT NULL DEFAULT 'pending',
      retry_count     INT NOT NULL DEFAULT 0,
      error_msg       TEXT DEFAULT NULL,
      created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      INDEX idx_status (status),
      INDEX idx_province (province)
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='省份控制线爬虫任务表';
  ```

- [ ] **种子数据**：编写 `scripts/seed_province_cutoffs.py`，写入 2025 年 31 省×科类 的一本线/专科线（约 60 条）：
  - 数据参考各省2025年高考成绩公布后公告的录取控制分数线
  - 3+1+2省份科类字段分别写"物理"和"历史"
  - 3+3省份写"综合"
  - `ON DUPLICATE KEY UPDATE` 幂等写入

- [ ] **爬虫网关**：更新 `POST /internal/crawler/ingest` 支持 `data_type="province_cutoff"`，写入 `province_cutoffs` 表

**验收标准**：
```sql
SELECT COUNT(*) FROM province_cutoffs WHERE year=2025;  -- >= 50条
-- 示例：河南物理2025年一本线约519，专科线约150
SELECT * FROM province_cutoffs WHERE province='河南' AND subject_category='物理' AND year=2025;
```

---

### T11.2 · 成绩段位前置判断 + 院校质量底线规则

| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | T11.1（province_cutoffs数据已就绪） |
| **负责人** | 后端 ★ 核心算法 |
| **解决Bug** | Bug #8（高分冲刺档为空）、Bug #9（高分保底出现职业技术学校） |

**为什么需要**：当前推荐引擎不区分考生分数段，导致666分考生保底推荐出现专科/职业技术学校（Bug #9），以及高分考生意向城市学校全被超越后冲刺档为空（Bug #8）。

**任务清单**：

- [ ] **新增** `classify_score_segment()` 函数（`api/services/recommendation.py`）：
  ```python
  async def classify_score_segment(province: str, subject_category: str, score: int, db) -> str:
      """
      查询 province_cutoffs 判断段位
      返回: 'high'（≥一本线）/ 'mid'（专科线≤x<一本线）/ 'low'（<专科线）/ 'unknown'（无数据）
      """
      cutoff = await db.fetch_one(
          "SELECT cutoff_yiben, cutoff_zhuanke FROM province_cutoffs "
          "WHERE province=:p AND subject_category=:s AND year=2025",
          {"p": province, "s": subject_category}
      )
      if not cutoff:
          return "unknown"
      if cutoff["cutoff_yiben"] and score >= cutoff["cutoff_yiben"]:
          return "high"
      if cutoff["cutoff_zhuanke"] and score >= cutoff["cutoff_zhuanke"]:
          return "mid"
      return "low"
  ```

- [ ] **新增** `apply_quality_threshold_filter()` 函数：按 PRD §4.8 规则过滤不符合质量底线的学校：
  ```
  高分段 保底档: 剔除专科/职业技术学校；最低为有国家级/省级一流专业的公办二本
  高分段 冲刺档: 仅985/211/双一流
  高分段 稳妥档: 公办一本
  中分段: 冲刺=公办一本，稳妥=公办二本，保底=二本为主
  低分段: 保底可纳入专科/职业技术
  ```
  - 质量判断依据：`schools.tags`（985/211/双一流）+ `school_majors.major_level`（国家级/省级一流）
  - 保留 `_intended_city` 标记学校不受底线过滤（意向城市强制展示）
  - 保留特别关注区学校不受过滤

- [ ] 在 `generate_recommendation()` 主流程中，Phase 0 之后插入段位判断，Phase 3 Tier分层后插入质量底线过滤：
  ```python
  # Phase 0.5: 成绩段位前置判断
  score_segment = await classify_score_segment(province, subject_category, score, db)
  
  # Phase 3之后: 应用质量底线
  filtered_schools = apply_quality_threshold_filter(tier_schools, score_segment, db)
  ```

- [ ] **处理 Bug #8**：当高分考生意向城市学校全部被超越（冲刺档空）时，L4 全国名校扩展不再仅限 L4 兜底，而是补充至冲刺档5所（附 🌐 说明文字："您的成绩已超出意向城市所有院校录取线，以下为全国匹配高校"）

**验收标准**：
- 666分河南考生（高分段）：保底档无专科/职业技术学校（Bug #9 修复）
- 666分河南考生：冲刺档显示985/211学校，不为空（Bug #8 修复）
- 350分考生（低分段）：保底档可出现专科（正常行为，无回归）
- `score_segment` 字段返回到 API response 供前端可选展示

---

### T11.3 · 地域扩展规则重构（三档统一）

| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T2.4（候选池构建已有基础） |
| **负责人** | 后端 |

**为什么需要**：PRD §4.1.2 升级后三个档位（冲/稳/保）凑不够5所时统一按"意向城市→周边城市按经济等级降序→本省→全国名校（仅冲刺）"扩展，不再仅限冲刺档使用全国兜底。

**任务清单**：

- [ ] **新增** `CITY_ECONOMIC_LEVEL` 映射字典：城市→经济等级（一线/新一线/二线/三线），用于周边城市扩展时按等级降序排列：
  ```python
  CITY_ECONOMIC_LEVEL = {
      "北京": 1, "上海": 1, "广州": 1, "深圳": 1,
      "成都": 2, "杭州": 2, "武汉": 2, "重庆": 2, "西安": 2,
      "南京": 2, "郑州": 2, "长沙": 2, "天津": 2, ...
  }
  ```

- [ ] **新增** `CITY_NEARBY_BY_LEVEL` 映射：每个城市 → 按经济等级降序排列的周边城市列表：
  ```python
  # 示例
  CITY_NEARBY_BY_LEVEL = {
      "杭州": ["上海", "南京", "苏州", "宁波", "金华"],  # 一线优先，再新一线
      "西安": ["北京", "上海", "郑州", "成都", "武汉"],
      ...
  }
  ```

- [ ] **重构** `build_candidate_pool_four_tiers()` 中各档位填充逻辑：
  - 旧逻辑：L1意向城市 → L2本省 → L3周边 → L4全国（仅冲刺）
  - 新逻辑（三档统一）：
    ```
    对每个Tier档位（冲/稳/保）:
      Step1: 意向城市学校（L1）
      Step2: 不足5所 → 意向城市周边，按经济等级降序扩展
      Step3: 仍不足 → 考生所在省（L2）
      Step4（仅冲刺档）: 仍不足 → 全国985/211/双一流，附🌐说明文字
    ```

- [ ] 确保 `_intended_city` 标记学校在任意档位均优先排序（不设概率门槛）

- [ ] 前端 `renderSchoolCard()` 中：当学校有 `globe_expanded=True` 标记时，在学校卡片顶部显示 `🌐 全国扩展推荐：您的成绩已超出意向城市所有院校录取线`

**验收标准**：
- 场景：河南350分，意向城市上海 → 推荐池: L1上海学校 → L2河南本省 → L3上海周边（江苏/浙江），L4不展示（非冲刺档）
- 场景：666分，意向城市郑州 → 冲刺档无本省普通院校，扩展至全国985/211，附🌐说明文字
- 地域扩展周边城市按经济等级降序（一线优先）

---

## Phase 12：一次性链接系统（PRD v5.4）

> **背景**：管理员可批量生成一次性链接，发给团体付费学生，学生无需登录直接完成填表→报告→PDF全流程，跳过付款墙。链接使用后立即失效，UUID v4 + HMAC 防伪造。

---

### T12.1 · `one_time_links` 数据表 + 后端API

| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | T1.2（基础DB）、T4.1（Admin认证） |
| **负责人** | 后端 |

**为什么需要**：学生自助报告页需要后端存储一次性链接状态（有效/已使用/失效），并提供管理员生成接口和学生校验接口。

**任务清单**：

- [ ] **建表**：
  ```sql
  CREATE TABLE one_time_links (
      id           INT AUTO_INCREMENT PRIMARY KEY,
      token        VARCHAR(128) NOT NULL COMMENT 'UUID4.HMAC签名，唯一令牌',
      batch_id     INT NOT NULL COMMENT '批次ID',
      batch_note   VARCHAR(128) DEFAULT NULL COMMENT '批次备注',
      status       ENUM('active','used','revoked') NOT NULL DEFAULT 'active',
      used_at      DATETIME DEFAULT NULL COMMENT '使用时间',
      used_ip      VARCHAR(45) DEFAULT NULL,
      created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      UNIQUE KEY uk_token (token),
      INDEX idx_batch (batch_id),
      INDEX idx_status (status)
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='一次性报告链接';
  
  CREATE TABLE one_time_link_batches (
      id           INT AUTO_INCREMENT PRIMARY KEY,
      note         VARCHAR(128) DEFAULT NULL COMMENT '批次备注',
      total_count  INT NOT NULL DEFAULT 0,
      created_by   INT NOT NULL COMMENT '管理员ID',
      created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='链接批次';
  ```

- [ ] **生成API** `POST /admin/one-time-links/generate`（Admin JWT）：
  ```
  Request: { "note": "6月19日10人团购", "count": 10 }
  处理:
    ① 创建 one_time_link_batches 记录，获取 batch_id
    ② 循环 count 次：uuid4() → HMAC(uuid4, SECRET_KEY, sha256) → token = "{uuid4}.{hmac[:12]}"
    ③ 批量插入 one_time_links
  Response: { "batch_id": 1, "links": ["http://121.41.69.234/s?t=xxx", ...] }
  ```

- [ ] **查询API** `GET /admin/one-time-links?batch_id=&page=&per_page=`（Admin JWT）：返回批次列表（含总数/已用/未用统计）

- [ ] **作废API** `POST /admin/one-time-links/revoke-batch`（Admin JWT）：`{ "batch_id": 1 }` → 将该批次所有 `status='active'` 改为 `'revoked'`

- [ ] **校验API** `GET /s/validate?t=<token>`（无需Auth）：
  ```
  ① 分割 token → uuid4 部分 + hmac 部分
  ② HMAC 签名校验（防伪造）
  ③ 查询 DB：
    - 不存在 → 404 {"status": "invalid"}
    - status='used' → 200 {"status": "used"}
    - status='revoked' → 200 {"status": "revoked"}
    - status='active' → 200 {"status": "valid"}
  ```

- [ ] **消费API** `POST /s/consume`（无需Auth）：
  ```
  Request: { "token": "xxx" }
  处理: BEGIN TRANSACTION
    SELECT id, status FROM one_time_links WHERE token=? FOR UPDATE
    IF status != 'active' → ROLLBACK → 409 { "error": "链接已使用" }
    UPDATE status='used', used_at=NOW(), used_ip=client_ip
    COMMIT
  Response: { "success": true }
  ```
  - **并发保证**：行锁确保同一链接只能被使用一次

**验收标准**：
```bash
# 生成5个链接
curl -X POST /admin/one-time-links/generate -H "Authorization: Bearer <admin>" \
  -d '{"note":"test","count":5}'
# → {"batch_id":1, "links":["http://121.41.69.234/s?t=...×5"]}

# 校验有效链接
curl /s/validate?t=<token>  # → {"status":"valid"}

# 消费一次
curl -X POST /s/consume -d '{"token":"<token>"}' # → {"success":true}

# 再次校验→已使用
curl /s/validate?t=<token>  # → {"status":"used"}

# 并发双消费（同一token）→只有一次成功
```

---

### T12.2 · 学生自助报告页⑨（前端）

| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | T12.1（后端API已就绪）、T3.5（报告渲染组件复用） |
| **负责人** | 前端 |

**为什么需要**：学生通过一次性链接访问，无需登录，自助完成填表→报告→PDF，跳过付款墙，是独立于主播端的全新入口。

**任务清单**：

- [ ] **新建文件** `frontend/s.html`（独立页，约600行）：
  - 路由：`/s?t=<token>` → Nginx 返回 `s.html`，前端 JS 读取 `URLSearchParams('t')`
  
- [ ] **链接校验流程（页面加载时）**：
  ```javascript
  const token = new URLSearchParams(location.search).get('t');
  const res = await fetch(`/s/validate?t=${token}`);
  const { status } = await res.json();
  if (status === 'used')    showPage('used');     // "此链接已被使用"
  if (status === 'invalid') showPage('invalid');  // "无效链接"
  if (status === 'revoked') showPage('revoked');  // "链接已作废"
  if (status === 'valid')   showPage('form');     // 进入填表流程
  ```

- [ ] **PC端专用强制横幅**（不可关闭，始终固定在顶部）：
  ```html
  <div class="pc-only-banner">
    ⚠️ 请在电脑端浏览器中使用本页面
    手机端打开将无法正常下载PDF报告，且操作界面不适配手机屏幕。
    建议使用 Chrome / Edge / Firefox 浏览器在电脑上打开。
  </div>
  ```

- [ ] **复用主播端表单**（从 `index.html` 复制 STEP1 + STEP2 逻辑）：
  - 相同的7字段考生信息 + 动态选科 + 4区域意向偏好
  - 删除登录态相关检查（此页面无需JWT）

- [ ] **推荐生成**（无需扣费，直接调用推荐接口）：
  - 使用公开推荐接口或在 `/api/recommendation/generate` 新增 `mode=student_link` 跳过JWT验证（设 `allow_unauthenticated_student_link=True` 参数）
  - 链接消费时机：推荐生成**成功后** `POST /s/consume` 标记已使用（不是点击链接时）

- [ ] **报告页**：直接展示完整报告（复用 `renderReport()` + `renderSchoolCard()`），无付款墙

- [ ] **底部操作**：仅显示 `📥 下载PDF`，无"测下一个"、无"直播答疑"

- [ ] **Nginx 新增路由**：
  ```nginx
  location = /s {
      try_files /s.html =404;
  }
  location /s/ {
      try_files $uri /s.html;
  }
  ```

**验收标准**：
- 有效链接 → PC横幅 → 填表 → 直接完整报告（无付款墙）→ 下载PDF
- 下载PDF后刷新 → 显示"此链接已被使用"
- 手机端打开 → 顶部横幅始终可见且不可关闭
- 无效token → 显示错误提示页，不崩溃

---

### T12.3 · 管理后台：一次性链接管理 Tab

| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | T12.1（后端API）、T4.1（Admin后台框架） |
| **负责人** | 前端 |

**为什么需要**：管理员需要在后台批量生成链接、查看使用状态、复制/下载链接列表、作废整批。

**任务清单**：

- [ ] `admin.html` 新增第5个Tab："🔗 一次性链接"

- [ ] **生成区域**（Tab顶部）：
  ```
  表单：批次备注（选填，最多50字）+ 生成数量（1-100）+ "✨ 立即生成" 按钮
  ```

- [ ] **生成后展示**（生成完成后在模态框或内联展示）：
  - 标题："已生成 N 个链接"
  - 按钮组：`一键复制全部` / `下载TXT文件`
    - `一键复制全部`：`navigator.clipboard.writeText(links.join('\n'))`
    - `下载TXT文件`：命名 `链接批次_[备注]_[日期].txt`
  - 链接列表（每行一个链接 + 独立复制按钮）

- [ ] **批次状态看板**（Tab中部表格）：
  ```
  列：批次ID | 备注 | 生成时间 | 总数 | 已用 | 未用 | 操作
  操作：[查看详情] [作废整批]
  ```
  - 查看详情：弹窗显示该批次每条链接状态（token前8位、状态、使用时间）
  - 作废整批：确认弹窗 → `POST /admin/one-time-links/revoke-batch`

- [ ] 分页加载（每页20批次）

**验收标准**：
- 生成10条 → 显示链接列表 → "一键复制全部"复制到剪贴板 → "下载TXT"下载文件
- 批次看板显示正确的已用/未用计数
- 作废整批 → 该批次未用链接状态变为"已作废"
- 查看详情 → 每条链接状态可追溯

---

## Phase 13：主播助手（PRD v5.4 Page⑧升级）

> **背景**：原Page⑧ "直播答疑"升级为"主播助手"，合并固定话术脚本（Tab A）和AI问答（Tab B）于同一页面。管理员在后台维护话术脚本库。

---

### T13.1 · `broadcast_scripts` 数据表 + 后端API

| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T1.2（基础DB）、T4.1（Admin认证）、T2.1（主播认证） |
| **负责人** | 后端 |

**为什么需要**：话术内容由管理员在后台维护，主播端实时读取，需要持久化存储和CRUD接口。

**任务清单**：

- [ ] **建表**：
  ```sql
  CREATE TABLE broadcast_scripts (
      id           INT AUTO_INCREMENT PRIMARY KEY,
      category     VARCHAR(64) NOT NULL COMMENT '话术分类',
      title        VARCHAR(128) NOT NULL COMMENT '话术标题',
      content      TEXT NOT NULL COMMENT '话术正文',
      sort_order   INT NOT NULL DEFAULT 0 COMMENT '同分类内排序（越小越靠前）',
      is_active    TINYINT NOT NULL DEFAULT 1 COMMENT '是否启用',
      created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      INDEX idx_category (category),
      INDEX idx_sort (category, sort_order)
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='直播话术脚本库';
  ```

- [ ] **预置默认分类话术**：编写 `scripts/seed_broadcast_scripts.py`，写入5个默认分类各2-3条示例话术：
  - 开播话术 / 产品介绍 / 报告讲解 / 收单话术 / 常见异议处理

- [ ] **主播只读接口** `GET /api/scripts`（Streamer JWT）：
  ```
  Response: {
    "categories": ["开播话术", "产品介绍", ...],
    "scripts": {
      "开播话术": [{ "id": 1, "title": "xx", "content": "xx" }, ...],
      ...
    }
  }
  ```
  - 仅返回 `is_active=1` 的话术，按 `sort_order` 升序

- [ ] **管理员CRUD** `GET/POST /admin/scripts`、`PUT/DELETE /admin/scripts/{id}`（Admin JWT）

- [ ] **分类管理** `GET /admin/script-categories`（读）、`POST /admin/script-categories`（新增）、`DELETE /admin/script-categories/{name}`（删除整个分类的话术）

- [ ] **排序更新** `PUT /admin/scripts/{id}/sort`：`{ "sort_order": 5 }` → 更新排序

**验收标准**：
```bash
# 主播读取话术
curl /api/scripts -H "Authorization: Bearer <streamer_token>"
# → {"categories":["开播话术",...], "scripts":{"开播话术":[{...}],...}}

# 管理员新增话术
curl -X POST /admin/scripts -H "Authorization: Bearer <admin_token>" \
  -d '{"category":"开播话术","title":"开场白","content":"大家好，欢迎来到..."}'
# → {"id": 6, "success": true}
```

---

### T13.2 · 主播助手页⑧前端（双Tab）

| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | T13.1（后端API已就绪）、T3.7（原直播答疑组件复用） |
| **负责人** | 前端 |

**为什么需要**：原 `#qa` 页面仅有AI问答，PRD v5.4 要求升级为主播助手，新增固定话术Tab，保留AI问答Tab。

**任务清单**：

- [ ] **页面重命名**：`#qa` → `#assistant`，导航栏"直播答疑" → "🎙️ 主播助手"

- [ ] **Tab导航**（两个Tab，固定在页面顶部）：
  ```
  [📋 直播话术] | [🤖 AI问答]
  ```

- [ ] **Tab A：直播话术**：
  - 加载时调用 `GET /api/scripts`，按分类展示
  - 分类折叠展开（默认第一个分类展开）：
    ```html
    <div class="category-header" onclick="toggleCategory('开播话术')">
      开播话术 (3条) ▼
    </div>
    <div class="category-body">
      <div class="script-card">
        <div class="script-title">开场白</div>
        <div class="script-content">大家好...</div>
        <button class="copy-btn" onclick="copyScript('大家好...')">📋 复制</button>
      </div>
    </div>
    ```
  - 复制按钮：`navigator.clipboard.writeText(content)` + Toast "已复制"
  - 数据库无话术时显示"暂无话术，请联系管理员配置"

- [ ] **Tab B：AI问答**（从原 `#qa` 页面完整迁移，代码复用）：
  - 10个预设快捷问题按钮（PRD §Page⑧ Tab B 10题）
  - 自由输入框（限100字）
  - AI回答气泡 + 对话历史
  - 清空历史按钮

- [ ] Tab切换时滚动位置重置到顶部

- [ ] 从报告页"🤖 直播答疑"按钮跳转到 `#assistant`（默认展示Tab B AI问答）

**验收标准**：
- 进入主播助手 → Tab A 显示分类话术 → 点击话术 → 复制按钮复制内容
- 切换Tab B → 10预设题+输入框正常工作
- 从报告页"直播答疑"按钮跳转后默认Tab B
- 管理员新增话术后，主播端刷新可见新内容

---

### T13.3 · 管理后台：话术管理 Tab

| 属性 | 内容 |
|------|------|
| **工时** | 3h |
| **前置** | T13.1（后端API）、T4.1（Admin后台框架） |
| **负责人** | 前端 |

**为什么需要**：管理员需要通过可视化界面维护话术脚本，包括分类管理、内容编辑、排序调整。

**任务清单**：

- [ ] `admin.html` 新增第6个Tab："📝 话术管理"

- [ ] **分类管理区**（Tab顶部）：
  - 显示当前所有分类 + "新增分类"按钮
  - 删除分类：确认弹窗（"删除将同时删除该分类下所有话术"）

- [ ] **话术列表区**（按分类分组显示）：
  ```
  分类：开播话术 [新增话术]
  ┌─────────────────────────────────────────┐
  │ # | 标题      | 内容预览   | 操作         │
  │ 1 | 开场白    | 大家好...  | [编辑][删除][↑][↓] │
  │ 2 | 产品介绍  | 我们是...  | [编辑][删除][↑][↓] │
  └─────────────────────────────────────────┘
  ```

- [ ] **新增/编辑弹窗**：
  ```
  分类选择（下拉，可选已有分类或输入新分类名）
  标题（必填，最多50字）
  内容（必填，Textarea，最多500字）
  [保存] [取消]
  ```

- [ ] **排序**：`[↑][↓]` 按钮调用 `PUT /admin/scripts/{id}/sort` 更新 `sort_order`，操作后刷新列表（保持当前分类展开状态）

- [ ] **启用/禁用**：每条话术有"启用/禁用"Toggle，禁用后主播端不可见

**验收标准**：
- 新增话术 → 主播端刷新后可见
- 调整排序（↑/↓）→ 主播端刷新后顺序变化
- 禁用话术 → 主播端不可见
- 删除分类 → 该分类所有话术消失

---

## Phase 14：遗留Bug + 细节完善

---

### T14.1 · Bug #7 /gk-admin 路径修复 + 其他小Bug

| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | 无 |
| **负责人** | 后端+运维 |
| **解决Bug** | Bug #7（/gk-admin 404） |

**任务清单**：

- [ ] **Bug #7 根因排查**：
  - SSH 登录 `121.41.69.234`，查 Nginx 配置是否有 `/gk-admin` 路由
  - 查 FastAPI 路由是否有 `/gk-admin`：`grep -r "gk-admin" /root/gaokao-ai/`
  - **修复方案A**（推荐）：在 Nginx 添加 301 重定向：`location = /gk-admin { return 301 /admin.html; }`
  - **修复方案B**：在 `main.py` 添加 `@app.get("/gk-admin")` → `RedirectResponse("/admin.html")`

- [ ] **验收**：
  ```bash
  curl -I http://121.41.69.234/gk-admin  # → HTTP/1.1 301, Location: /admin.html
  ```

- [ ] **dim17 空数据前端渲染**：当 API 返回 `risk_diff=null`、`risk_level=null`、`adjustment_advice=null` 时，前端 `renderSchoolCard()` 中报考风险区块整体不渲染（避免显示空框或"undefined"）

- [ ] **dim18 空数据前端渲染**：当 `enrollment_trend=null` 时，招生规模趋势区块不渲染

- [ ] **招生规模数据接口扩展**：在 `aggregate_school_dimensions()` 新增对 `dim18` 的占位组装（从 `admission_history` 的 `plan_count`/`actual_count` 字段查询，若字段不存在则返回 `null`），为后续爬虫补全留桩

**验收标准**：
- `/gk-admin` → 301 跳转到 `/admin.html`
- 报告中无 "undefined"、"null" 等不友好文字（无数据的维度整体隐藏）

---

### T14.2 · 三档对比表 + 整体梯度总结渲染

| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | T3.5（报告渲染基础） |
| **负责人** | 前端 |

**为什么需要**：PRD v5.1 板块三末尾新增"三档院校综合横向对比表"，板块四末尾新增"整体梯度搭配策略总结"，当前代码未实现。

**任务清单**：

- [ ] **三档横向对比表**（板块三末尾，所有学校卡片之后）：
  ```javascript
  function buildComparisonTable(schools) {
    // schools 按 tier 分组 (0=冲刺/1=稳妥/2=保底)
    // 按 PRD §板块三-补充 生成HTML表格
    // 列：院校名称 | 层次 | 近年录取分 | 录取概率 | 就业率 | 均薪(月) | 年学费 | 风险等级
    // 数据从 school.dimensions 中提取
    // 按冲刺/稳妥/保底分组，组间加分组标题行
  }
  ```

- [ ] **整体梯度搭配策略总结**（板块四末尾新增第7节）：
  ```javascript
  function buildGradientSummary(schools, tierCounts) {
    // 基于实际推荐的冲/稳/保数量给出建议文字
    // "综合推荐：冲刺X所（建议报2-3）+ 稳妥X所（建议报3-5）+ 保底X所（建议报2-3）"
    // 调剂风险提示 + 注意事项（固定文本）
  }
  ```

- [ ] 对比表和梯度总结均计入PDF导出（`downloadPDF()` 的内容捕获范围包含新区块）

**验收标准**：
- 报告板块三末尾出现横向对比表（含冲/稳/保分组）
- 报告板块四末尾出现梯度搭配策略总结
- PDF下载包含以上内容

---

## Phase 15：集成验证与生产部署

---

### T15.1 · 数据库迁移 + 生产部署

| 属性 | 内容 |
|------|------|
| **工时** | 2h |
| **前置** | Phase 11-14 全部完成 |
| **负责人** | 后端/运维 |

**任务清单**：

- [ ] **编写迁移SQL文件** `scripts/migrate_v5_new_features.sql`：
  ```sql
  -- 建表：province_cutoffs, province_cutoff_crawl_tasks
  -- 建表：one_time_links, one_time_link_batches
  -- 建表：broadcast_scripts
  ```

- [ ] **生产执行顺序**：
  ```bash
  # 1. 备份当前DB
  mysqldump gaokao_ai | gzip > /tmp/backup_before_v5_$(date +%Y%m%d).sql.gz
  
  # 2. 执行DDL迁移
  mysql -u root -p gaokao_ai < scripts/migrate_v5_new_features.sql
  
  # 3. 写入种子数据
  python scripts/seed_province_cutoffs.py
  python scripts/seed_broadcast_scripts.py
  
  # 4. 部署后端代码
  cd /root/gaokao-ai && git pull origin main
  systemctl restart gaokao-api.service
  
  # 5. 部署前端文件
  cp frontend/index.html /www/wwwroot/gaokao.lumenaistudio.co/index.html
  cp frontend/admin.html /www/wwwroot/gaokao.lumenaistudio.co/admin.html
  cp frontend/s.html     /www/wwwroot/gaokao.lumenaistudio.co/s.html
  
  # 6. 更新Nginx配置（新增/s路由）并重载
  nginx -t && systemctl reload nginx
  
  # 7. 健康验证
  curl http://121.41.69.234/health
  ```

**验收标准**：
```bash
curl http://121.41.69.234/health  # → {"status":"ok","mysql":"ok","redis":"ok"}
SELECT COUNT(*) FROM province_cutoffs;         # → >= 50
SELECT COUNT(*) FROM broadcast_scripts;        # → >= 5（种子话术）
curl http://121.41.69.234/s.html               # → 200 OK（学生自助报告页）
curl -I http://121.41.69.234/gk-admin          # → 301
```

---

### T15.2 · PRD v5.x 验收场景测试

| 属性 | 内容 |
|------|------|
| **工时** | 4h |
| **前置** | T15.1（生产部署完成） |
| **负责人** | 全员 |

**依据**：PRD v5.2 §十 验收标准（4个场景）+ 新功能验收

**场景1：端对端标准查询（PRD §十 场景1）**

```
输入：河南 + 物理+化学+政治 + 540分 + 位次约35000 + 意向郑州大学(计算机) + 意向城市郑州
预期验证：
  ✓ 郑州大学出现在"📌 特别关注"区（不计入15所）
  ✓ 推荐概率显示具体百分比（非"暂无"）
  ✓ 分数线趋势展示≤5年，逐年可见
  ✓ 就业率/薪资标注真实数据来源及年份，不同学校差异化
  ✓ 推荐池15所按四层填充，郑州学校置顶
```

**场景2：算法边界与数据缺失（PRD §十 场景4）**

```
预期验证：
  ✓ rankProb < 30% 的非意向学校不进推荐池
  ✓ 仅1年历史数据时：100%权重并在卡片注明"仅有1年历史数据，参考价值有限"
  ✓ 无录取数据时：前端显示"暂无录取数据"
  ✓ dim17/dim18 无数据时：整块不渲染（无空框）
```

**场景3：高分考生边界（Bug #8、#9 验证）**

```
输入：河南 + 660分（高分段）
预期验证：
  ✓ 冲刺档：显示985/211学校（不为空，Bug #8修复）
  ✓ 保底档：无专科/职业技术学校（Bug #9修复）
  ✓ 推荐包含🌐全国扩展推荐说明文字
```

**场景4：低分考生+跨省（PRD §十 场景3）**

```
输入：河南350分 + 意向城市上海 + 意向学校北京大学+河南科技大学+洛阳师范学院
预期验证：
  ✓ 特别关注区3所（北京大学标"录取概率0%·成绩未达录取线"）
  ✓ 推荐池：L1上海学校→L2河南本省→L3上海周边（江苏/浙江）
  ✓ 低分段专科纳入推荐范围
```

**场景5：新功能验收**

```
一次性链接：
  ✓ 管理员生成10条链接 → 下载TXT → 复制全部
  ✓ 学生打开链接 → PC横幅显示 → 填表 → 完整报告 → PDF
  ✓ 再次访问 → "此链接已被使用"

主播助手：
  ✓ 主播端进入主播助手 → Tab A显示管理员配置的话术 → 点复制
  ✓ Tab B AI问答正常（10预设题+自由输入）
  ✓ 管理员后台新增话术 → 主播端刷新可见

管理后台：
  ✓ 话术管理Tab：增删改查、排序
  ✓ 一次性链接Tab：生成、状态追踪、作废批次
```

**验收标准**：5个场景全部通过 → 可通知主播开始使用新功能

---

## 任务依赖图

```
Phase 11（算法升级）
  T11.1 ──────────────────────► T11.2
  T11.3（独立，可与T11.2并行）

Phase 12（一次性链接）
  T12.1 ──► T12.2
        └─► T12.3（可与T12.2并行）

Phase 13（主播助手）
  T13.1 ──► T13.2
        └─► T13.3（可与T13.2并行）

Phase 14（Bug修复）
  T14.1（独立）
  T14.2（独立）

Phase 15（集成部署）
  Phase11~14全部完成 ──► T15.1 ──► T15.2
```

**并行策略**：
- Phase 11 / Phase 12 / Phase 13 / Phase 14 可四线并行开发
- T12.2（学生前端）和 T12.3（管理后台）可在 T12.1 完成后并行
- T13.2（主播助手前端）和 T13.3（管理后台话术）可在 T13.1 完成后并行
- Phase 15 必须在前四个Phase全部完成后串行执行

---

## 工时汇总

| Phase | 任务数 | 工时 | 说明 |
|-------|:---:|:---:|------|
| Phase 11: 算法升级 | 3 | 10h | Bug #8/#9 + §4.7/4.8/4.1.2 |
| Phase 12: 一次性链接系统 | 3 | 12h | 含后端API + 前端学生页 + 管理后台 |
| Phase 13: 主播助手 | 3 | 10h | 含后端API + 前端双Tab + 管理后台 |
| Phase 14: 遗留Bug修复 | 2 | 4h | Bug #7 + 对比表渲染 |
| Phase 15: 集成验证部署 | 2 | 6h | DB迁移 + 5场景验收 |
| **合计** | **13** | **~42h** | 约5.25人天 |

> **关键路径**（最短时间）：并行执行 Phase11+12+13+14（约12h）→ T15.1迁移（2h）→ T15.2验收（4h）= **约18h（约2.25人天）**

---

## Architecture.md 更新清单

本次任务完成后，Architecture.md 需同步以下变更（文档更新随代码提交一并完成）：

| 章节 | 更新内容 |
|------|---------|
| §4.1 表结构总览 | 新增 province_cutoffs, province_cutoff_crawl_tasks, one_time_links, one_time_link_batches, broadcast_scripts |
| §4.2 DDL | 新增5张表完整DDL |
| §4.5 爬虫任务表 | 新增 province_cutoff_crawl_tasks |
| §5.1 接口总览 | 新增12个接口（一次性链接管理/学生校验/话术CRUD） |
| §2.2 前端模块 | 新增 Page⑧主播助手双Tab / Page⑨学生自助报告页 |
| §2.3 后端模块 | 新增 OneTimeLinks 模块 / BroadcastScripts 模块 |
| §3.2 推荐引擎流程 | Phase 0.5 成绩段位判断 / Phase 3之后质量底线过滤 |
| §10.2 Nginx 配置 | 新增 `/s` location |
| 附录B 约束速查 | 新增省份控制线查询 / 质量底线规则 / 链接防伪造 |

---

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-06-16 | 初始任务拆分（Phase 1-6） |
| v2.0 | 2026-06-17 | 新增 Phase 7-10（v4.0升级） |
| v2.1 | 2026-06-17 | 新增 Phase 10（数据丰富） |
| **v3.0** | **2026-06-19** | **重写：Phase 1-10已全部完成；新增 Phase 11-15 覆盖 PRD v5.3（算法升级）+ PRD v5.4（一次性链接/主播助手）+ 遗留Bug修复，共13任务约42h** |
