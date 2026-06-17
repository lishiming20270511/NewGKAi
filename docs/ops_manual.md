# 运维手册 — 高考AI志愿规划师

> 服务器：121.41.69.234  
> 项目路径：/root/gaokao-ai/  
> 域名：gaokao.lumenaistudio.co  
> 技术栈：FastAPI + MySQL + Redis + uvicorn(4 workers) + Nginx

---

## 1. 服务启停

### systemd 服务管理

```bash
# 启动服务
systemctl start gaokao-api

# 停止服务
systemctl stop gaokao-api

# 重启服务
systemctl restart gaokao-api

# 查看状态
systemctl status gaokao-api
```

### 查看日志

```bash
# 实时查看最近100条日志
journalctl -u gaokao-api -n 100 --no-pager

# 实时滚动日志（Ctrl+C 退出）
journalctl -u gaokao-api -f

# 查看今天的日志
journalctl -u gaokao-api --since today
```

### Nginx 操作

```bash
# 测试配置文件语法
nginx -t

# 重载配置（不中断连接）
systemctl reload nginx

# 重启 nginx
systemctl restart nginx

# 查看 nginx 状态
systemctl status nginx
```

---

## 2. 常见问题处理

### API 返回 500 错误

1. 查看 uvicorn 日志定位具体报错：
   ```bash
   journalctl -u gaokao-api -n 200 --no-pager | grep -i error
   ```
2. 确认是代码异常还是依赖服务故障（数据库/Redis）
3. 修复后执行 `systemctl restart gaokao-api`

### 数据库连接失败

```bash
# 检查 MySQL 运行状态
systemctl status mysql

# 启动 MySQL（如已停止）
systemctl start mysql

# 验证连接
mysql -u gaokao_user -p'GKai@2026#Prod' gaokao_ai -e "SELECT 1;"
```

常见原因：MySQL 进程挂起、磁盘空间不足（`df -h` 检查）、连接池耗尽。

### Redis 不可用

Redis 为可选依赖，不可用时系统自动降级到数据库锁，**业务不中断**。

```bash
# 检查 Redis 状态
systemctl status redis

# 启动 Redis
systemctl start redis

# 验证连接
redis-cli ping
# 期望返回：PONG
```

### 内存不足

```bash
# 查看内存占用
free -h

# 查看 uvicorn 进程内存
ps aux | grep uvicorn

# 临时释放：重启服务（会短暂中断）
systemctl restart gaokao-api
```

如长期内存紧张，可在 `/etc/systemd/system/gaokao-api.service` 中将 `--workers 4` 改为 `--workers 2`，改后执行：

```bash
systemctl daemon-reload
systemctl restart gaokao-api
```

---

## 3. 日志位置

| 日志类型 | 位置 / 命令 |
|---|---|
| systemd 应用日志 | `journalctl -u gaokao-api -n 100 --no-pager` |
| nginx 访问日志 | `/var/log/nginx/gaokao_access.log` |
| nginx 错误日志 | `/var/log/nginx/gaokao_error.log` |
| 爬虫 staging 日志 | `/tmp/check_staging.log` |

```bash
# 实时监控 nginx 访问
tail -f /var/log/nginx/gaokao_access.log

# 实时监控 nginx 错误
tail -f /var/log/nginx/gaokao_error.log
```

---

## 4. 部署更新流程

### 步骤说明

**第一步：在开发机打包代码**

```bash
# 在本地开发目录执行
cd D:\DEV\NewGKAi
tar -czf gaokao-update.tar.gz app/ frontend/ requirements.txt
```

**第二步：上传到服务器**

```bash
scp gaokao-update.tar.gz root@121.41.69.234:/root/
```

**第三步：服务器端部署**

```bash
# SSH 登录
ssh root@121.41.69.234

# 备份当前版本（可选但推荐）
cp -r /root/gaokao-ai /root/gaokao-ai.bak.$(date +%Y%m%d)

# 解压新版本
cd /root/gaokao-ai
tar -xzf /root/gaokao-update.tar.gz --strip-components=0

# 安装新依赖（如有）
pip install -r requirements.txt

# 重启服务
systemctl restart gaokao-api
```

**第四步：验证部署**

```bash
# 健康检查
curl http://127.0.0.1:8000/health

# 期望返回：{"status":"ok"} 或类似成功响应
```

---

## 5. 数据库备份

### 手动备份

```bash
# 备份整个数据库（推荐）
mysqldump -u gaokao_user -p'GKai@2026#Prod' gaokao_ai \
  > /root/backup/gaokao_ai_$(date +%Y%m%d_%H%M%S).sql

# 确保备份目录存在
mkdir -p /root/backup
```

### 查看备份文件

```bash
# 列出所有备份文件（按时间排序）
ls -lht /root/backup/gaokao_ai_*.sql

# 查看最新备份文件大小
ls -lh /root/backup/gaokao_ai_*.sql | tail -1
```

### 从备份恢复

```bash
# 恢复指定备份（谨慎操作，会覆盖当前数据）
mysql -u gaokao_user -p'GKai@2026#Prod' gaokao_ai \
  < /root/backup/gaokao_ai_YYYYMMDD_HHMMSS.sql
```

---

## 6. 健康检查

### 标准验证命令序列

```bash
# 1. 检查服务进程状态
systemctl status gaokao-api

# 2. 应用层健康检查
curl http://127.0.0.1:8000/health

# 3. 外网访问验证（通过域名）
curl https://gaokao.lumenaistudio.co/health

# 4. 检查 nginx 是否正常代理
curl -I http://121.41.69.234/health

# 5. 检查数据库连接
mysql -u gaokao_user -p'GKai@2026#Prod' gaokao_ai -e "SELECT COUNT(*) FROM streamer_accounts;"

# 6. 检查 Redis
redis-cli ping
```

所有命令均无报错且 `/health` 返回成功，则系统状态正常。

---

*最后更新：2026-06-17*
