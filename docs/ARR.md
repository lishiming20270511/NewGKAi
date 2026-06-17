# Architecture Review Report (ARR) — AI高考志愿规划师 v1.2

| 文档信息 | 内容 |
|---------|------|
| 审查对象 | Architecture.md v1.2 |
| 审查人 | 首席架构师（影子审查） |
| 审查日期 | 2026-06-17 |
| 审查范围 | 高可用/容灾 · 数据一致性 · 性能/扩展性 · 降级/兜底 · 过度设计 · 成本 · 技术选型 |

---

## 总体评分

| 维度 | 评分 | 说明 |
|------|:---:|------|
| 架构清晰度 | ⭐⭐⭐⭐⭐ | 文档结构完整，流程图清晰，决策记录扎实 |
| 高可用 | ⭐⭐ | 单机全栈，无冗余，Redis 强依赖无降级 |
| 数据安全 | ⭐⭐ | 爬虫直写生产库 + 扣费无幂等——两个致命问题 |
| 性能设计 | ⭐⭐⭐⭐ | 批量 SQL + Redis 缓存层设计合理，50 并发目标务实 |
| 成本控制 | ⭐⭐⭐⭐⭐ | MVP 选型极度克制，没碰 Docker/K8s |
| 过度设计控制 | ⭐⭐⭐⭐ | V2/V3 规划偏多但不影响 MVP，SaaS 架构应删除 |

> **总评**：架构设计思路正确（规则引擎 + LLM 辅助的职责分离），选型务实。但 R1（扣费幂等）和 R2（爬虫直写生产库）是上线前必须修的硬伤。R3（Redis 降级）和监控建议在 6·25 上线前一周补齐。

---

## 1. 🔍 核心风险点（Risk Assessment）

### R1 · 【致命】扣费缺少幂等性，高并发下必资损

**位置**：Architecture §3.3 扣费流程

**问题**：`POST /auth/deduct` 设计的双层锁（Redis NX + DB `SELECT FOR UPDATE`）只能防止**并发**重复扣费，不能防止**网络重试**导致的重复扣费。

**攻击路径**：
```
前端 POST /auth/deduct → 后端扣费成功、写订单 → 响应在网络层丢失
前端超时重试 → 后端再次扣费成功、再写一条订单
结果：用户被扣 2 次，订单表出现 2 条兄弟记录
```

文档中 Redis 锁 TTL=5s，但没有任何 `idempotency_key`。`orders` 表也没有任何防重约束。

**后果**：资损。如果你是微信支付/支付宝审计，这是直接挂掉的级别。

---

### R2 · 【致命】爬虫直写生产 MySQL，无隔离、无校验、无回滚

**位置**：Architecture §1.1 架构全景图，"爬虫服务器通过 SSH 隧道写入生产 MySQL"

**问题**：外部 Python 脚本直接 `INSERT` 到核心生产库，无 API 层、无数据校验层。

**风险清单**：
- 爬虫脚本里一个 `DELETE FROM admission_history WHERE 1=1` = 全量数据损失
- 爬虫抓到的错数据（如把「最高分」写入 `min_rank` 列）**不会被任何校验拦截**，直接污染推荐引擎
- 推荐引擎 `calc_rank_prob()` 与 `min_rank` 直接挂钩 → 错数据 = 推荐概率诡异/全部相同

**违反的架构原则**（Architecture §1.3 自述）："数据缺失时自动触发爬虫补全" —— 但爬虫和主系统之间缺少**数据网关（Data Gateway）**。

---

### R3 · 【严重】Redis 宕机 = 系统瘫痪（而非降级）

**位置**：Architecture §4.4 Redis 数据结构

| 职责 | Redis 挂了会怎样 |
|------|:---:|
| JWT 黑名单 | 已注销 Token 仍可用（**安全漏洞**） |
| 扣费分布式锁 `SET NX` | `/auth/deduct` 直接抛 429 → **用户无法解锁报告** |
| 学校搜索缓存 | 退化为 MySQL LIKE（性能劣化，尚可接受） |
| IP 限流 | 限流失效（可接受） |

**最严重的是扣费路径**：`redis.set(lock_key, "1", nx=True, ex=5)` 失败时抛出 `HTTPException(429)`。Redis 宕机 = 所有付费操作全部 429。

文档没有任何 Redis 故障时的降级策略。

---

### R4 · 【严重】全栈单机部署 = 单点故障全集

**位置**：Architecture §10.1 服务器拓扑

**问题**：整个生产拓扑运行在**一台** 114.55.65.71 上：Nginx + FastAPI + MySQL + Redis。任何一个组件故障 → 全局停服。

**业务背景**：高考志愿填报是**季节性峰值业务**（6月25日-7月5日是绝对高峰，错过一天 = 失去全年 30% 收入）。单机在峰值期间没有任何逃生通道。

文档中连 MySQL 自动备份方案都是 `mysqldump | ossutil`，但没有恢复演练、没有 RPO/RTO 指标、没有备机方案。

---

### R5 · 【中等】Redis L3 缓存 key 设计可能导致不同考生命中相同结果

**位置**：Architecture § Redis 缓存策略

```python
L3 Key: recommend:result:{hash(student_params)}
```

`hash()` 没有指明具体算法（Python `hash()` 是不稳定的/跨进程不同的）。更关键的是需要确认 `personality` 和 `economic_level` 都在 hash 输入中，否则两个不同性格的考生可能命中同一份缓存。

---

### R6 · 【低】admission_history DDL 与实际查询不一致

**位置**：Architecture §4.3 DDL vs § MySQL 查询优化

DDL 用 `school_name VARCHAR(128)`，但批量查询用 `ah.school_id IN (...)`。

**待确认**：关联字段到底是 `school_id`（整数）还是 `school_name`（字符串）？如果是字符串，117 万行 IN 匹配会很慢。

---

### R7 · 【低】systemd 以 root 运行

**位置**：Architecture §10.2 systemd 配置

```ini
User=root
```

FastAPI 进程以 root 监听 8000 端口。一个 RCE 漏洞直接拿 root 权限。应该以专用用户运行。

---

### R8 · 【注意】SSH 隧道作为爬虫数据通道的可靠性

**位置**：Architecture §1.1

SSH 隧道不是为持久数据通道设计的——TCP keepalive 不配好会频繁断连。断了以后爬虫写入静默丢数据。文档未提及 `fetch_school_facts.py` 的重试/断线重连机制。

---

## 2. 🚀 架构优化建议（Actionable Recommendations）

### A1 · 立即修复扣费幂等性（补救 R1）

#### 前端改动
```javascript
// 在触发扣费时生成并持有 idempotency_key
const idempotencyKey = crypto.randomUUID();  // 或自生成 UUID v4
// 同一次解锁操作，重试时复用同一个 key
localBalance -= 1;
fetch('/auth/deduct', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
    body: JSON.stringify({ idempotency_key: idempotencyKey })
})
```

#### 后端改动
```python
@router.post("/auth/deduct")
async def deduct(req: DeductRequest, current_streamer=Depends(get_current_streamer)):
    try:
        await redis.set(lock_key, "1", nx=True, ex=5)
    except Exception:
        pass  # Redis 不可用降级

    try:
        async with db.transaction():
            # ① 幂等检查
            existing = await db.fetch_one(
                "SELECT id FROM orders WHERE idempotency_key = :key AND streamer_id = :sid",
                {"key": req.idempotency_key, "sid": current_streamer.id}
            )
            if existing:
                return {"success": True, "already_processed": True, "order_id": existing["id"]}

            # ② SELECT FOR UPDATE + 扣费
            account = await db.fetch_one(
                "SELECT balance, used_total FROM streamer_accounts WHERE id = :id FOR UPDATE",
                {"id": current_streamer.id}
            )
            if account["balance"] < 1:
                raise HTTPException(400, "剩余次数不足")

            await db.execute(
                "UPDATE streamer_accounts SET balance = balance - 1, used_total = used_total + 1 WHERE id = :id",
                {"id": current_streamer.id}
            )

            # ③ 写订单（含幂等key）
            order_id = generate_order_id()
            await db.execute(
                "INSERT INTO orders (id, streamer_id, idempotency_key, ...) VALUES (:id, :sid, :key, ...)",
                {"id": order_id, "sid": current_streamer.id, "key": req.idempotency_key, ...}
            )
    finally:
        try: await redis.delete(lock_key)
        except: pass

    return {"success": True, "balance": account["balance"] - 1, "order_id": order_id}
```

#### 数据库改动
```sql
ALTER TABLE orders ADD COLUMN idempotency_key VARCHAR(36) DEFAULT NULL;
ALTER TABLE orders ADD UNIQUE INDEX uk_idempotency (streamer_id, idempotency_key);
```

**时间窗口**：30 分钟内的重试幂等；超过 30 分钟视为新请求。前端用同一 key 重试。

---

### A2 · 爬虫加数据网关（补救 R2）

```
爬虫服务器(海外)                        生产服务器(国内)
     │                                       │
     │ POST /internal/crawler/ingest         │
     │ { "school_name": "郑州大学",            │
     │   "year": 2025, "min_rank": 22000 }    │
     ├──────────────────────────────────────►│
     │                                       ▼
     │                              FastAPI 内部端点
     │                              (JWT 内部认证)
     │                                       │
     │                                       ▼
     │                              crawler_staging 临时表
     │                                       │
     │                                       ▼
     │                              校验 (check_staging.py, crontab 每5分钟)
     │                              ├─ 字段完整性 (非 NULL)
     │                              ├─ 值域合理性 (min_rank > 0, min_score 0-750)
     │                              ├─ 数据去重 (school_name + province + year)
     │                              └─ 通过 → MERGE INTO admission_history
     │                                 失败 → crawler_error_log
```

**不要从外部服务器直连 MySQL**。加一个内部 API 端点，用 FastAPI 做数据校验。

---

### A3 · 扣费去 Redis 强依赖（补救 R3）

```python
@router.post("/auth/deduct")
async def deduct(...):
    # 尝试获取 Redis 锁（可选优化，非必需）
    lock_acquired = False
    try:
        lock_acquired = await redis.set(lock_key, "1", nx=True, ex=5)
    except Exception:
        pass  # Redis 不可用，降级为仅 DB 锁

    try:
        async with db.transaction():
            account = await db.fetch_one(
                "SELECT balance FROM streamer_accounts WHERE id = :id FOR UPDATE",
                {"id": current_streamer.id}
            )
            if account["balance"] < 1:
                raise HTTPException(400)
            await db.execute("UPDATE streamer_accounts SET balance = balance - 1, ...")
    finally:
        if lock_acquired:
            try: await redis.delete(lock_key)
            except: pass
```

**JWT 黑名单降级**：Redis 不可用时不检查黑名单（MVP 阶段可用性 > 安全性），日志告警。

---

### A4 · 增加最小化监控告警（补救 R4）

| 监控项 | 方式 | 阈值 | 告警方式 |
|--------|------|------|----------|
| `/health` 深度检查 | crontab 每 5 分钟 curl，检查 `{mysql:"ok", redis:"ok"}` | 任一非 ok | 企业微信/钉钉 Webhook |
| MySQL 连接 | `mysqladmin ping` | 失败 | 同上 |
| 磁盘 | `df -h` | >80% | 同上 |
| 异常扣费 | `SELECT COUNT(*) FROM streamer_accounts WHERE balance < 0` | >0 | 同上 |
| SSL 证书 | `openssl x509 -checkend 604800` | 即将过期 | 同上 |
| Redis OOM | `redis-cli INFO memory` | `used_memory > maxmemory * 0.85` | 同上 |

**生产环境硬化工单**：

| 项目 | 当前 | 建议 |
|------|------|------|
| FastAPI 用户 | `User=root` | 建 `gaokao` 用户，`sudo systemd` |
| MySQL 连接池 | 未提及 | `pool_size=20, max_overflow=30` |
| Redis persistence | 未提及 | `save 3600 1` (每1小时至少1次写则 RDB) |
| Redis eviction | 未提及 | `maxmemory-policy allkeys-lru` |
| Nginx worker | 默认 | `worker_connections=4096` |
| /api/recommendation 限流 | 未提及 | 每个主播 2 req/s（Redis 计数器，降级为内存 dict） |

---

### A5 · 缓存 key 显式化（补救 R5）

```python
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

**用 `hashlib.md5` 替代 Python 内建 `hash()`**——后者跨进程不稳定。

---

### A6 · 删除/推迟过度设计

| 项目 | 理由 |
|------|------|
| **V2 "AI Agent 质量巡检"** (§6.3) | MVP 先跑出真实数据再说，Agent 质量巡检现在完全没用 |
| **Redis L3 全量结果缓存** (10min TTL) | 50 并发下收益极小（同一个主播不会 10 分钟内查同一个人两次），增加缓存一致性心智负担。建议 **MVP 去掉** |
| **report_tasks 防倒卖系统** (§4.2) | 几个主播的 MVP 阶段人工看订单表就够了。代码写了但不会有人看。可保留表结构但逻辑标记为 V2 |
| **SaaS 多租户架构** (§9.2 ②) | 2027 年的事，现在画架构图纯属 PPT 工程。建议从 Architecture.md 中删除，另存为 `V3_Plan.md` |

---

## 3. ❓ 追问与澄清（Clarification Questions）

### Q1 · admission_history 表的实际 join key

DDL 写的是 `school_name VARCHAR(128)`，但 §5.2 的批量查询和 API Response 都用 `school_id`。

**请确认**：
- `admission_history` 和 `schools` 的关联字段到底是 `school_id`（整数）还是 `school_name`（字符串）？
- 如果是字符串，`idx_school_prov_year(school_name, province, year)` 索引是否已建？

---

### Q2 · 爬虫数据覆盖矩阵

文档多次提到「数据完整 / 部分缺失 / 无数据」，但没有一张表说明**到底爬了多少省份 × 多少年份**。

**建议补充**：`31省 × 4年(2022-2025) × 文理科` 的覆盖率矩阵。

---

### Q3 · 历史一分一段表

§3.2 PHASE 0 位次估算只查 `year=2025`。如果 2025 年数据还没爬进来（6月25日前），**没有任何位次数据**。

**是否存储 2022/2023/2024 年历史一分一段表作为回退？** 如果没有，是直接抛错还是降级估算？

---

### Q4 · 前端乐观扣减的边界

```
localBalance -= 1  →  POST /auth/deduct  →  失败 → localBalance += 1
```

用户在 POST 返回之前关闭了浏览器 tab → `localBalance += 1` 不执行 → 前端余额永久 -1（实际余额未扣）。确认是否为已知/可接受的 trade-off？

---

### Q5 · Redis 部署配置

文档未提 Redis 的 `maxmemory`、淘汰策略、持久化配置。

**建议**：在 Architecture §4.4 补充 Redis 生产配置（至少 `maxmemory-policy allkeys-lru` 和 `save 3600 1`），避免 OOM kill。

---

## 附录：修复优先级

| 优先级 | 项目 | 预计工时 | 截止日期 |
|:---:|------|:---:|------|
| **P0** | R1: 扣费幂等性 | 2h 后端 + 1h 数据库 | 上线前 |
| **P0** | R2: 爬虫数据网关 | 4h 后端 + 2h 爬虫改造 | 上线前 |
| **P1** | R3: Redis 降级 | 1h 后端 | 上线前1周 |
| **P1** | A4: 基础监控告警 | 2h 运维 | 上线前1周 |
| **P2** | R6: admission_history 字段确认 | 30min | 本周 |
| **P2** | A5: 缓存 key 显式化 | 30min | 本周 |
| **P3** | R7: systemd 用户降权 | 30min | 上线后 |
| **P3** | A6: 删除过度设计 | 1h 文档整理 | 上线后 |

---

> **核心结论**：架构设计思路正确（规则引擎 + LLM 辅助的职责分离），选型务实。R1（扣费幂等）和 R2（爬虫直写生产库）是上线前必须修的两个硬伤。R3（Redis 降级）和 A4（基础监控）建议在 6·25 上线前一周补齐。
