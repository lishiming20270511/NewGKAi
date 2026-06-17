# BUG_CLOSED.md — 高考志愿规划师

**最后更新**：2026-06-15

---

| Bug编号 | 问题 | 最终解决方案 | 状态 |
|---------|------|-------------|------|
| BUG-001 | 登录报"未找到账号数据" | `doLogin()`从localStorage改为`fetch('/auth/streamer/login')`；nginx变量污染修复 | ✅ |
| BUG-002 | 扣费未同步后端，余额永久不准 | 新增`POST /auth/streamer/deduct`端点，前端乐观更新+API失败回滚 | ✅ |
| BUG-003 | 意向城市学校不出现 | `_city_match`增加城市→省份映射（60+城市）；跨省宽口径查询 | ✅ |
| BUG-004 | 意向学校不出现（被遗漏） | `_merge_must_diag`改为`diag_recs + recs`，不限数量，强制置顶 | ✅ |
| BUG-005 | 意向学校被模糊匹配替代（"广州大学松田学院"→"广州大学"） | 匹配改为纯精确`===`+子串名去重保护 | ✅ |
| BUG-006 | 低概率无效推荐（rankProb<30%仍显示） | 非意向学校rankProb<30%移除；`filtered.sort()`按tier排序 | ✅ |
| BUG-007 | 分数超省份满分仍可保存 | `updateRankEst()`自动钳制输入值到省份满分+提示 | ✅ |
| BUG-008 | 城市标签合并为一个（广州+深圳变"广州深圳"） | 拆分为独立城市芯片 | ✅ |
| BUG-009 | 专业方向太少 | 8大类扩充到26个细分专业 | ✅ |
| BUG-010 | 付费墙着色按位置索引，非实际tier（稳妥→冲刺→稳妥显示错乱） | `i<3?'red':...`改为`s.tier===1?'blue':s.tier===2?'green':'red'` | ✅ |
| BUG-011 | 饼图/报告摘要/PDF分层标签硬编码"5所"，实际数量不匹配 | 预计算`_tierTotals`统计各tier实际数量，全部改为动态拼接 | ✅ |
| BUG-012 | PDF生成挂死（buildPDFWrap引用renderReport局部变量`_tierTotals`） | 在`buildPDFWrap`函数内独立计算`_tierTotals` | ✅ |
| BUG-013 | 低分段（200分）仅返回3所意向学校，城市学校和兜底学校全部被`rp>=30`过滤清空 | 城市池移除概率门槛并标记`_intended_city`强制保留；空池时回退到分数接近度排序；<400分阈值降至5% | ✅ |
| BUG-014 | 同tier内意向学校排在末尾（概率低导致rankProb排序靠后） | 排序增加三级优先级：`_intended(★)`→`_intended_city(●)`→rankProb降序 | ✅ |
| BUG-015 | 96%学校prov字段为空，城市匹配和地域优先级全部失效 | `SCHOOL_POOL`构建时，city为空→`getCityFromSchoolName()`提取；prov为空→`CITY_PROV[city]`映射 | ✅ |
