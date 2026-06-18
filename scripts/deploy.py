import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("121.41.69.234", username="root", password="Lz88192603!@#", timeout=15)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    out = stdout.read().decode()
    err = stderr.read().decode()
    return out, err

print("1. fetch+reset")
o, e = run("cd /root/gaokao-ai && git -c http.proxy= -c https.proxy= fetch origin main && git -c http.proxy= -c https.proxy= reset --hard origin/main")
print(o[:300])
if e: print("ERR:", e[:200])

print("2. clear pyc")
o, e = run("find /root/gaokao-ai -name '*.pyc' -delete 2>/dev/null; find /root/gaokao-ai -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null; echo done")
print(o.strip())

print("3. clear redis")
o, e = run("redis-cli KEYS 'recommend:*' 2>/dev/null | xargs -r redis-cli DEL 2>/dev/null; echo done")
print(o.strip())

print("4. restart")
o, e = run("systemctl restart gaokao-api && sleep 2 && systemctl is-active gaokao-api")
print(o.strip())
if e: print("ERR:", e[:200])

print("5. health")
o, e = run("curl -s http://127.0.0.1:8000/health")
print(o.strip())

ssh.close()
print("\nDONE")
