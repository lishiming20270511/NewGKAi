"""Fix MySQL access on new server for crawler."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("121.41.69.234", username="root", password="Lz88192603!@#", timeout=15)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=20)
    out = stdout.read().decode()
    err = stderr.read().decode()
    return out, err

# Check MySQL users
print("=== MySQL Users ===")
o, e = run("mysql -u root -pLz88192603!@# -e \"SELECT user, host FROM mysql.user WHERE user IN ('gaokao_user', 'root')\" 2>&1")
print(o)

# Check bind address
print("\n=== MySQL Bind ===")
o, e = run("grep bind /etc/mysql/mysql.conf.d/mysqld.cnf 2>/dev/null || grep bind /etc/my.cnf 2>/dev/null || echo 'no bind found'")
print(o)

# Check if port 3306 is listening
print("\n=== Port 3306 ===")
o, e = run("ss -tlnp | grep 3306")
print(o)

# Grant access for gaokao_user from localhost (tunnel)
print("\n=== Grant crawler access ===")
o, e = run("mysql -u root -pLz88192603!@# -e \"GRANT ALL PRIVILEGES ON gaokao_ai.* TO 'gaokao_user'@'127.0.0.1' IDENTIFIED BY 'Lz88192603!@#'; FLUSH PRIVILEGES;\" 2>&1")
print(o)

# Test connection from server itself
print("\n=== Test local connection ===")
o, e = run("mysql -u gaokao_user -pLz88192603!@# -h 127.0.0.1 -e \"SELECT COUNT(*) as cnt FROM gaokao_ai.admission_history\" 2>&1")
print(o)

# Check .env on production for comparison
print("\n=== Production .env DB settings ===")
o, e = run("grep -E 'DB_|DATABASE' /root/gaokao-ai/.env 2>/dev/null")
print(o)

ssh.close()
