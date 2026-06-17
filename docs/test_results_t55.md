# T5.5 Nginx 配置加固 - 测试报告

**执行时间**: 2026-06-17  
**执行人**: Claude (运维工程师)  
**服务器**: 121.41.69.234 (root)  
**任务状态**: 全部完成

---

## 1. 配置变更说明

### 变更内容对比

| 项目 | 旧配置 | 新配置 |
|------|--------|--------|
| listen | 80 default_server | 80 (HTTP) + 443 ssl (HTTPS) |
| server_name | `_` | `gaokao.lumenaistudio.co _` |
| gzip | 未配置 | on, types: text/plain/json/js/css, min 1024B |
| access_log | 使用默认 | /var/log/nginx/gaokao_access.log |
| error_log | 使用默认 | /var/log/nginx/gaokao_error.log |
| X-Frame-Options | 无 | SAMEORIGIN |
| X-Content-Type-Options | 无 | nosniff |
| 静态文件缓存 | 无 | Cache-Control: public, max-age=3600 |
| 推荐API缓存控制 | 无 | Cache-Control: no-store, no-cache |
| upstream超时 | proxy_read_timeout 60s (仅) | connect 10s + read 60s |
| /internal/ 访问控制 | 仅允许 199.193.126.80 | 增加 127.0.0.1 |
| HTTPS | 无 | 自签名证书，TLS 1.2/1.3 |

### location 路由顺序（已优化优先级）
1. `/internal/` — IP白名单限制（精确前缀，最高优先）
2. `/api/recommendation/` — 推荐API，禁止缓存
3. `~* \.(html|js|css|png|jpg|ico|woff2)$` — 静态文件，有缓存
4. `/` — 兜底，所有其他请求

### 配置文件位置
- 主配置: `/etc/nginx/sites-available/gaokao`（软链接到 sites-enabled）
- 备份位置: `/tmp/gaokao.bak`（原始备份）
- SSL证书: `/etc/nginx/ssl/gaokao.crt`
- SSL私钥: `/etc/nginx/ssl/gaokao.key`

---

## 2. nginx -t 语法检查结果

```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

**结论**: 语法检查 0 错误，0 警告，完全通过。

> 注：原始写入时出现两个 warning，原因是 sites-enabled 目录中有 `gaokao.bak` 文件（含旧的 `server_name _`）被 nginx 加载导致冲突。已将备份移至 `/tmp/gaokao.bak`，重新测试后无任何警告。

---

## 3. curl 验证结果

### 3.1 HTTP /health 端点
```
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/health
→ 200
```
服务正常响应。

### 3.2 安全响应头验证（GET /）
```
HTTP/1.1 200 OK
Server: nginx/1.18.0 (Ubuntu)
Content-Type: text/html; charset=utf-8
Content-Length: 95888
X-Frame-Options: SAMEORIGIN        ← 已配置
X-Content-Type-Options: nosniff   ← 已配置
```

### 3.3 推荐API Cache-Control（no-store 验证）
```
curl -sI http://127.0.0.1/api/recommendation/
→ Cache-Control: no-store, no-cache   ← 正确
```

### 3.4 gzip 压缩验证
```
curl -s -H "Accept-Encoding: gzip" -I http://127.0.0.1/ -X GET
→ Content-Encoding: gzip   ← gzip 生效
```

### 3.5 HTTPS（自签名证书）
```
curl -sk -o /dev/null -w "%{http_code}" https://127.0.0.1/health
→ 200
```
HTTPS 443 端口正常响应，自签名证书工作正常。

HTTPS 响应头确认安全头也在 HTTPS 上生效：
```
HTTP/1.1 200 OK
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
```

### 3.6 端口监听状态
```
0.0.0.0:80   → nginx (active)
0.0.0.0:443  → nginx (active)
[::]:80      → nginx (active)
[::]:443     → nginx (active)
```

---

## 4. SSL 状态说明

### 当前状态: 自签名证书（内部测试）

```
subject=CN = gaokao.lumenaistudio.co, O = LumenAI
notBefore=Jun 17 09:03:48 2026 GMT
notAfter=Jun 17 09:03:48 2027 GMT
```

- 证书有效期: 2026-06-17 至 2027-06-17（365天）
- 加密套件: TLS 1.2 / TLS 1.3，HIGH:!aNULL:!MD5
- 浏览器访问会显示"不安全"警告（自签名证书预期行为）

### 为何不能使用 Let's Encrypt

DNS 当前指向旧服务器 114.55.65.71，而新生产服务器 IP 为 121.41.69.234。Let's Encrypt 的 HTTP-01 验证要求 DNS 解析必须指向本机，因此在 DNS 更新之前无法颁发免费受信任证书。

### 升级至受信任 HTTPS 的步骤（待 DNS 更新后）

```bash
# 1. 将 DNS A 记录: gaokao.lumenaistudio.co → 121.41.69.234
# 2. 等待 DNS 传播（通常 10-30 分钟）
# 3. 安装 certbot
apt install certbot python3-certbot-nginx -y

# 4. 申请证书（自动修改 nginx 配置）
certbot --nginx -d gaokao.lumenaistudio.co

# 5. 验证自动续期
certbot renew --dry-run
```

---

## 5. 日志文件验证

```
/var/log/nginx/gaokao_access.log  — 已创建，正在记录请求
/var/log/nginx/gaokao_error.log   — 已创建，目前无错误（0字节）
```

---

## 6. 最终配置文件

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name gaokao.lumenaistudio.co _;

    client_max_body_size 10m;

    gzip on;
    gzip_types text/plain application/json application/javascript text/css;
    gzip_min_length 1024;

    access_log /var/log/nginx/gaokao_access.log;
    error_log /var/log/nginx/gaokao_error.log;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    location /internal/ {
        allow 199.193.126.80;
        allow 127.0.0.1;
        deny all;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/recommendation/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_connect_timeout 10s;
        proxy_read_timeout 60s;
        add_header Cache-Control "no-store, no-cache" always;
    }

    location ~* \.(html|js|css|png|jpg|ico|woff2)$ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        add_header Cache-Control "public, max-age=3600";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_connect_timeout 10s;
        proxy_read_timeout 60s;
    }
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name gaokao.lumenaistudio.co;

    ssl_certificate /etc/nginx/ssl/gaokao.crt;
    ssl_certificate_key /etc/nginx/ssl/gaokao.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 10m;
    gzip on;
    gzip_types text/plain application/json application/javascript text/css;
    gzip_min_length 1024;

    access_log /var/log/nginx/gaokao_access.log;
    error_log /var/log/nginx/gaokao_error.log;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # (同 HTTP 的 location 配置)
    location /internal/ { ... }
    location /api/recommendation/ { ... }
    location ~* \.(html|js|css|...)$ { ... }
    location / { ... }
}
```

---

## 7. 任务验收总结

| 检查项 | 状态 | 备注 |
|--------|------|------|
| 配置备份 | PASS | /tmp/gaokao.bak |
| server_name 设置 | PASS | gaokao.lumenaistudio.co _ |
| 静态文件缓存 | PASS | Cache-Control: public, max-age=3600 |
| API 禁止缓存 | PASS | /api/recommendation/ → no-store, no-cache |
| X-Frame-Options | PASS | SAMEORIGIN |
| X-Content-Type-Options | PASS | nosniff |
| gzip 压缩 | PASS | Content-Encoding: gzip 已验证 |
| upstream 超时 | PASS | connect 10s, read 60s |
| 日志分离 | PASS | gaokao_access.log / gaokao_error.log |
| /internal/ IP 限制 | PASS | 仅 199.193.126.80 + 127.0.0.1 |
| nginx -t 语法检查 | PASS | 0 错误 0 警告 |
| systemctl reload | PASS | nginx active, 平滑重载成功 |
| HTTP /health 200 | PASS | curl 验证 |
| HTTPS 自签名证书 | PASS | 443 端口监听，curl -sk 返回 200 |
| Let's Encrypt | 待做 | 需要先更新 DNS 到 121.41.69.234 |

**T5.5 Nginx 配置加固: 全部完成**
