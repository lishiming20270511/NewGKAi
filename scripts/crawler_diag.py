"""Diagnose crawler venv, tunnel config, and real connectivity."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("199.193.126.80", username="root", password="SGM7VVPAPfGe", timeout=20)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    out = stdout.read().decode()
    err = stderr.read().decode()
    return out, err

# 1. Find virtualenvs
print("=== Python Virtualenvs ===")
o, e = run("find /root -name 'activate' -path '*/bin/activate' 2>/dev/null; find /root -name 'python' -path '*/bin/python' 2>/dev/null | head -10")
print(o)

# 2. Check .env file
print("\n=== Crawler .env ===")
o, e = run("cat /root/gaokao-crawler/.env 2>/dev/null || echo 'NO .env'; ls -la /root/gaokao-crawler/")
print(o)

# 3. Check all SSH tunnels
print("\n=== All SSH Tunnels ===")
o, e = run("ps aux | grep 'ssh\\|autossh' | grep -v grep")
print(o)

# 4. Check if there's a tunnel to the new server
print("\n=== Tunnel to 121.41.69.234? ===")
o, e = run("ss -tlnp | grep -E '3306|13306|13307|23306'")
print(o)

# 5. Try connecting to new server's MySQL via SSH
print("\n=== Test new server MySQL ===")
o, e = run("timeout 10 ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@121.41.69.234 'mysql -u root -pLz88192603!@# -e \"SELECT COUNT(*) FROM gaokao_ai.admission_history\"' 2>&1 || echo 'CONNECTION_FAILED'")
print(o[:500])

# 6. Check old server connection
print("\n=== Test old server MySQL ===")
o, e = run("timeout 10 ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@114.55.65.71 'mysql -u root -pLz88192603!@# -e \"SELECT COUNT(*) FROM gaokao_ai.admission_history\"' 2>&1 || echo 'CONNECTION_FAILED'")
print(o[:500])

# 7. Check cron jobs
print("\n=== Crontab ===")
o, e = run("crontab -l 2>&1")
print(o)

ssh.close()
