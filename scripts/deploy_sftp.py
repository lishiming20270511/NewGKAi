import paramiko, os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("121.41.69.234", username="root", password="Lz88192603!@#", timeout=15)
sftp = ssh.open_sftp()

# Copy the modified recommendation.py
local_rec = "D:/dev/NewGKAi/api/services/recommendation.py"
remote_rec = "/root/gaokao-ai/api/services/recommendation.py"
print(f"Uploading {local_rec}...")
sftp.put(local_rec, remote_rec)
print("uploaded")

# Copy main.py (with Cache-Control fix)
local_main = "D:/dev/NewGKAi/main.py"
remote_main = "/root/gaokao-ai/main.py"
print(f"Uploading {local_main}...")
sftp.put(local_main, remote_main)
print("uploaded")

# Copy index.html (with PDF/disclaimer fixes)
local_idx = "D:/dev/NewGKAi/frontend/index.html"
remote_idx = "/root/gaokao-ai/frontend/index.html"
print(f"Uploading {local_idx}...")
sftp.put(local_idx, remote_idx)
print("uploaded")

sftp.close()

# Clear pyc + Redis + restart
def run(cmd, timeout=10):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode(), stderr.read().decode()

print("\nClear pyc...")
o, e = run("find /root/gaokao-ai -name '*.pyc' -delete 2>/dev/null; find /root/gaokao-ai -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null; echo done")
print(o.strip())

print("Clear Redis...")
o, e = run("redis-cli KEYS 'recommend:*' 2>/dev/null | xargs -r redis-cli DEL 2>/dev/null; echo done")
print(o.strip())

print("Restart service...")
o, e = run("systemctl restart gaokao-api && sleep 2 && systemctl is-active gaokao-api")
print(o.strip())

print("Health check...")
o, e = run("curl -s http://127.0.0.1:8000/health")
print(o.strip())

ssh.close()
print("\nDONE - All files deployed via SFTP")
