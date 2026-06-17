# TODO.md — 高考志愿规划师

**最后更新**：2026-06-15

---

## P0（必须做）

| # | 任务 | 说明 |
|---|------|------|
| 1 | 后端AI接口恢复 | `POST /recommendation/pro` 因Anthropic API调用失败返回503。需排查API Key、Base URL、网络连通性 |

## P1（重要）

| # | 任务 | 说明 |
|---|------|------|
| 2 | PDF报告样式优化 | 概率百分比和学校标签字体偏大，需缩小以保证一行显示不换行 |
| 3 | 前端推荐算法自动化测试 | 当前无pytest/playwright覆盖`generateSchools()`、`renderReport()`、`calcRankProb()`，全部依赖手动浏览器console验证 |
| 4 | `getCityFromSchoolName`词典扩充 | 约4%学校无法提取城市（如"中国科学院大学"），需增加关键词匹配规则 |

## P2（优化）

| # | 任务 | 说明 |
|---|------|------|
| 5 | `PROVINCE_SCHOOL_SCORES`数据加载确认 | 样本页不加载此外部数据，非登录态测试依赖`SCHOOLS`兜底，需确认生产链路完整 |
| 6 | 性能优化 | `SCHOOLS`2673条全量加载，可考虑按省份懒加载；`YIFENYIDANG`30省份可拆分按需加载 |
| 7 | 部署自动化 | 当前SCP+sed手工部署，可引入CI/CD（GitHub Actions→服务器rsync） |
| 8 | 推荐算法增强 | 引入历年录取趋势、大小年分析、专业级录取概率，替代纯位次比值+静态权重 |
