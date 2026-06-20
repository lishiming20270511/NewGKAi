# SESSION.md — 项目状态交接文档

**生成日期**：2026-06-20  
**版本**：v5.13（最终状态）  
**用途**：新会话开始时快速了解项目全貌，避免重复分析

---

## I. 项目基本信息

| 项目 | 内容 |
|------|------|
| 项目名称 | AI高考志愿规划师 · 直播辅助工具 |
| 生产地址 | `http://121.41.69.234` / `https://gaokao.lumenaistudio.co/` |
| 备用服务器 | `65.49.201.187` |
| 爬虫服务器 | `199.193.126.80` |
| 代码路径（服务器） | `/root/gaokao-ai/` |
| 静态文件路径 | `/www/wwwroot/gaokao.lumenaistudio.co/` |
| 本地代码路径 | `D:\dev\NewGKAi\` |
| API端口 | `8000`（uvicorn 4 workers，systemd管理） |
| 数据库 | MySQL 8.0 `gaokao_ai` + Redis 7 |
| 当前进度 | **75/75 任务全部完成（100%）** |

---

## II. 已完成功能清单

### A. 前端（index.html）
| 功能模块 | 描述 |
|----------|------|
| 登录页 | JWT登录，Bearer token，24h有效期 |
| 考生信息页 | 省份/分数/科目，分数上限自动钳制 |
| 意向偏好页 | 城市多选（60+城市映射）、学校精确搜索、26个专业方向 |
| 分析过渡页 | 45s最低动画，6步骤进度条 |
| 付费墙预览 | 15所学校，按实际tier着色（非位置索引） |
| 完整报告页 | 18维度数据、特别关注区、专业分析、就业数据 |
| PDF下载 | html2canvas(scale:3) + jsPDF，5重防伪水印 |

### B. 推荐引擎（前端generateSchools()，5阶段流水线）
| 阶段 | 描述 |
|------|------|
| 位次估算 | 一分一段表映射，支持降级估算 |
| 候选池（4层填充） | 意向学校→意向城市→本省/邻省/沿海→全国兜底 |
| 概率计算 | 6档离散rankProb + 6维度weightedProb（35%录取+20%专业+15%就业+10%城市+10%性格+10%经济） |
| Tier分层 | 冲刺 30–50% / 稳妥 50–85% / 保底 ≥85%（以rankProb为准，v5.10修正） |
| 数据组装 | 18维度输出：录取/专业/就业/城市/性格/经济 |

**关键算法约束**（已锁定）：
- `calcRankProb` 6档离散：差值>5000→95%，2000-5000→80%，0-2000→65%，-2000-0→45%，-5000- -2000→25%，<-5000→8%
- Tier阈值：冲刺[30,50) / 稳妥[50,85) / 保底[85,100]
- 低分段（<400分）概率门槛降至5%，纳入专科/民办
- `_is_vocational` 职业院校检测含"技术学院"关键词，精英院校豁免

### C. 后端API（FastAPI）
| 端点 | 功能 |
|------|------|
| `POST /auth/streamer/login` | 主播登录，返回JWT |
| `POST /auth/deduct` | 原子扣费（SELECT FOR UPDATE + 幂等key + Redis分布式锁+DB降级） |
| `GET /auth/streamer/profile` | 主播信息（余额/用量） |
| `POST /api/recommendation/generate` | 推荐引擎（Redis L1 1h / L2 24h缓存，冷启动105ms，缓存5ms） |
| `POST /api/chat` | 直播答疑（LLM调用） |
| `GET /api/schools/search` | 学校搜索（本地缓存+三级查询，前缀→FULLTEXT→全匹配） |
| `GET /api/health` | 健康检查（MySQL/Redis状态） |
| `POST /internal/crawler/ingest` | 爬虫数据入库（内部JWT+Nginx IP白名单） |
| `GET /api/one-time-links/validate/{token}` | 一次性链接验证（返回"valid"字段） |
| `POST /admin/...` | 管理后台CRUD |

### D. 管理后台（admin.html，Vue3 SPA）
| Tab | 功能 |
|-----|------|
| 主播管理 | CRUD + 充值 + 禁用/启用 |
| 订单查看 | 订单列表+状态 |
| 系统配置 | KV配置管理 |
| 一次性链接 | 批次创建/管理/查看 |
| 直播话术 | broadcast_scripts CRUD（主播只读） |
| 爬虫状态 | crawl_tasks 监控 |

### E. 学生自助页（s.html）
- 一次性链接验证（HMAC-SHA256 token，行锁原子消费）
- 成绩查看+结果展示

### F. AI聊天（chat.html）
- 独立页面（v5.11从index.html Tab B拆出）
- 直播答疑，LLM接入

### G. 爬虫网关
- 内部JWT认证 + Nginx IP白名单（199.193.126.80 + 127.0.0.1）
- staging→validate→MERGE模式
- 6类数据：录取/专业/学费/就业/薪资/城市
- Pydantic双层校验（Field约束 + field_validator）

### H. 基础设施
| 组件 | 状态 |
|------|------|
| Nginx | gzip + 安全headers + API no-cache + 分离日志 |
| SSL | 自签名证书已部署，Let's Encrypt待DNS备案 |
| Redis | 分布式锁 + JWT黑名单 + 推荐缓存，宕机降级DB |
| systemd | uvicorn 4 workers 自动重启 |

---

## III. 当前遗留问题

### A. 外部依赖（非代码问题）
| 优先级 | 事项 | 说明 |
|--------|------|------|
| P0 🔴 | chsi编码映射 | 需运行`crawl_school_list()`获取阳光高考学校编码 |
| P1 🟡 | qswl.tech DNS+ICP+SSL | 域名备案后配置 |
| P2 🟢 | 小程序BASE_URL | 备案通过后更新 |
| P2 🟢 | gaokao.cn CDN API | `list_v2.json`疑似变更，调查中 |

### B. 测试行为偏差（T5.2，非Bug，系统有防护）
| 编号 | 描述 | 影响 |
|------|------|------|
| B-01 | score=800传入返回422拒绝（非截断至750继续处理） | API直连方感知，前端已有前置校验 |
| B-02 | min_score=999坏数据在Pydantic层422拦截，未写crawler_error_log | error_log仅记录DB层异常，schema层无日志 |
| B-03 | TC-02北大rank_prob=1.0语义不直观（实为"排名第1才能录取"） | 可能误导用户，建议语义标注 |

### C. 待观察事项
- R-02: crawler_staging中存有school_id=99999无效记录（无FK约束），5分钟cron校验后进入rejected
- R-03: 西藏+拉萨场景estimated_count=12/15，数据质量偏低

---

## IV. 性能测试结果（T5.3，全部通过）

| 指标 | 目标 | 实测 | 结果 |
|------|------|------|------|
| 推荐API响应（冷） | <500ms | 105ms | ✅ |
| 推荐API响应（缓存） | <50ms | 5ms | ✅ |
| 10并发P99 | <1000ms | 161ms | ✅ |
| 扣费接口响应 | <200ms | 实测通过 | ✅ |
| 学校搜索响应 | <100ms | 实测通过 | ✅ |
| Redis宕机降级 | 扣费仍成功 | 200 OK | ✅ |

---

## V. 已修复关键Bug（禁止回退）

| 版本 | Bug | 修复摘要 |
|------|-----|---------|
| BUG-001 | 登录"未找到账号数据" | doLogin()改为fetch API + nginx变量污染修复 |
| BUG-005 | 意向学校模糊匹配 | 纯精确===匹配+子串名去重保护 |
| BUG-010 | 付费墙着色错位 | 按s.tier着色，非位置索引i<3 |
| BUG-012 | PDF生成挂死 | buildPDFWrap独立计算_tierTotals |
| BUG-014 | 意向学校排序靠后 | ★→●→rankProb三级优先级 |
| BUG-015 | 96%学校prov字段丢失 | getCityFromSchoolName()+CITY_PROV双重回退 |
| v5.10 | Tier阈值错误 | 冲刺上界60%→50%，<30%不纳入 |
| v5.12 | 高分考生冲刺0所 | prior过高/L4门槛/globe_expanded/segment兜底四层修复 |
| v5.13 | backfill tier归属错误 | backfill后更新s.tier，计数器正确 |
| v5.13 | 职业院校漏检 | _is_vocational加"技术学院"+精英院校豁免 |
| v5.13 | 一次性链接无效 | validate返回"active"→前端期望"valid"，映射修复 |

---

## VI. 下一步优先行动

| 优先级 | 行动 | 说明 |
|--------|------|------|
| P0 | chsi编码映射 | 运行`crawl_school_list()`，补充学校编码 |
| P1 | DNS/ICP备案 | qswl.tech备案后配置Let's Encrypt SSL |
| P2 | B-01评估 | 评估score超限是否改为截断策略（当前严格拒绝422） |
| P2 | B-02增强 | 考虑在schema层validator异常时也写crawler_error_log |
| P3 | 自动化测试 | 为generateSchools()/calcRankProb()编写pytest/playwright覆盖 |

---

*本文档由 Claude Code 于 2026-06-20 基于11份项目文档自动生成。如有修改，请同步更新。*
