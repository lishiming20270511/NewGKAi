# 管理员操作指南 — 高考AI志愿规划师

> 适用人员：系统管理员  
> 后台地址：http://gaokao.lumenaistudio.co  
> 管理账号：admin / lz88192603

---

## 1. 访问管理后台

1. 使用 **PC 端浏览器**访问 `http://gaokao.lumenaistudio.co`
2. 点击导航栏中的 **"管理后台"** 入口
3. 输入账号密码登录：
   - 账号：`admin`
   - 密码：`lz88192603`

> 管理后台仅支持 PC 端访问，移动端布局不完整。

---

## 2. 主播管理

### 新增主播

1. 进入 **主播管理** 页面
2. 点击 **"新增主播"**
3. 填写以下信息：

| 字段 | 说明 |
|---|---|
| 手机号 | 作为登录账号，不可重复 |
| 密码 | 建议至少 8 位，含字母和数字 |
| 姓名 | 主播真实姓名或昵称 |
| 余额 | 新增时填 0，后续通过充值操作增加 |

4. 点击 **"确认"** 保存

### 编辑主播信息

1. 在主播列表找到对应主播
2. 点击 **"编辑"**
3. 可修改：手机号、密码、姓名
4. 点击 **"保存"**

### 禁用 / 启用主播

- 点击主播行右侧的 **"禁用"** 按钮：该主播立即无法登录，已解锁的报告不受影响
- 点击 **"启用"** 恢复账号访问权限

---

## 3. 充值操作

1. 在主播列表中找到需要充值的主播
2. 点击该行的 **"充值"** 按钮
3. 在弹窗中输入充值次数（参考定价：**10 次 = 299 元**）
4. 点击 **"确认充值"**
5. 充值**立即生效**，主播刷新页面后即可使用新余额

> 充值记录会自动记录在订单日志中，便于后续对账。

---

## 4. 查看订单

### 订单列表字段说明

| 字段 | 说明 |
|---|---|
| 订单号 | 系统自动生成的唯一标识 |
| 主播 | 操作该订单的主播姓名/手机号 |
| 考生 | 填写的考生昵称/姓名 |
| 省份 | 考生所在省份 |
| 分数 | 考生高考总分 |
| 时间 | 订单生成时间 |

### 筛选订单

- **日期筛选**：选择开始日期和结束日期，查看指定时段订单
- **主播筛选**：从下拉列表选择特定主播，查看其所有订单

---

## 5. 系统配置

### 概率阈值设置

控制院校分类逻辑（冲刺/稳妥/保底的判断标准）：

| 配置项 | 说明 | 默认值 |
|---|---|---|
| 冲刺阈值 | 录取概率低于此值归入"冲刺" | 40% |
| 稳妥阈值 | 录取概率在冲刺至此值之间为"稳妥" | 70% |
| 保底阈值 | 录取概率高于此值归入"保底" | 70% |

### 分数上限配置

| 省份 | 满分 |
|---|---|
| 上海 | 660 |
| 其他省份 | 750 |

修改后**立即生效**，影响后续所有分析请求。

### 定价配置

配置充值次数与金额的对应关系，便于主播充值时参考展示。

---

## 6. 数据库直查（高级操作）

适用于后台界面无法覆盖的查询需求。操作前请确认命令无误，**误操作可能导致数据损坏**。

### SSH 登录服务器

```bash
ssh root@121.41.69.234
# 密码：Lz88192603!@#
```

### 常用查询命令

```bash
# 查看所有主播的余额和使用情况
mysql -u gaokao_user -p'GKai@2026#Prod' gaokao_ai \
  -e "SELECT phone, name, balance, used_total FROM streamer_accounts;"

# 查看指定主播的订单数量
mysql -u gaokao_user -p'GKai@2026#Prod' gaokao_ai \
  -e "SELECT phone, name, COUNT(*) AS orders FROM streamer_accounts sa
      JOIN orders o ON sa.id = o.streamer_id
      GROUP BY sa.id;"

# 查看今日订单数
mysql -u gaokao_user -p'GKai@2026#Prod' gaokao_ai \
  -e "SELECT COUNT(*) AS today_orders FROM orders WHERE DATE(created_at) = CURDATE();"

# 查看某主播所有订单
mysql -u gaokao_user -p'GKai@2026#Prod' gaokao_ai \
  -e "SELECT o.id, sa.name, o.student_name, o.province, o.score, o.created_at
      FROM orders o
      JOIN streamer_accounts sa ON o.streamer_id = sa.id
      WHERE sa.phone = '13800138000'
      ORDER BY o.created_at DESC LIMIT 20;"

# 手动调整主播余额（谨慎操作）
mysql -u gaokao_user -p'GKai@2026#Prod' gaokao_ai \
  -e "UPDATE streamer_accounts SET balance = balance + 10 WHERE phone = '13800138000';"
```

### 测试账号（仅限测试）

- 手机号：`13800138000`
- 密码：`test123`

---

## 7. 紧急联系与升级

| 情况 | 处理方式 |
|---|---|
| 服务宕机 | 参考运维手册 ops_manual.md，执行重启流程 |
| 数据异常 | 停止操作，联系技术负责人，不要自行修复 |
| 账号被盗 | 立即登录后台禁用该账号，修改 admin 密码 |

---

*最后更新：2026-06-17*
