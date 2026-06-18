import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("121.41.69.234", username="root", password="Lz88192603!@#", timeout=15)

def run(cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    return out, err

print("1. git fetch+reset...")
o, e = run("cd /root/gaokao-ai && git -c http.proxy= -c https.proxy= fetch origin main 2>&1", timeout=120)
print("fetch:", o[:200])
if e: print("fetch_err:", e[:200])

o, e = run("cd /root/gaokao-ai && git -c http.proxy= -c https.proxy= reset --hard origin/main 2>&1", timeout=30)
print("reset:", o[:200])

o, e = run("cd /root/gaokao-ai && git log --oneline -1")
print("HEAD:", o.strip())

print("\n2. clear pyc + redis...")
o, e = run("find /root/gaokao-ai -name '*.pyc' -delete 2>/dev/null; find /root/gaokao-ai -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null; echo pyc_done")
print(o.strip())
o, e = run("redis-cli KEYS 'recommend:*' 2>/dev/null | xargs -r redis-cli DEL 2>/dev/null; echo redis_done")
print(o.strip())

print("\n3. restart service...")
o, e = run("systemctl restart gaokao-api && sleep 2 && systemctl is-active gaokao-api")
print(o.strip())

print("\n4. health check...")
o, e = run("curl -s http://127.0.0.1:8000/health")
print(o.strip())

ssh.close()
print("\nDONE")
