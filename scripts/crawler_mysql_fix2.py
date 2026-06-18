"""Fix MySQL access for crawler user on new server."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("121.41.69.234", username="root", password="Lz88192603!@#", timeout=15)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=20)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if err:
        print("  ERR:", err[:200])
    return out

# Read the actual .env to get gaokao_user password
print("=== Actual .env DB_PASSWORD ===")
o = run("grep DB_PASSWORD /root/gaokao-ai/.env | sed 's/^DB_PASSWORD=//'")
db_pass = o.strip()
print("Password length:", len(db_pass), "starts with:", db_pass[:3] if len(db_pass) > 3 else "???")

# Create gaokao_user@127.0.0.1 with same password
print("\n=== Grant gaokao_user@127.0.0.1 ===")
o = run("mysql -u root -pLz88192603!@# -e \"CREATE USER IF NOT EXISTS 'gaokao_user'@'127.0.0.1' IDENTIFIED BY '" + db_pass + "'; GRANT ALL PRIVILEGES ON gaokao_ai.* TO 'gaokao_user'@'127.0.0.1'; FLUSH PRIVILEGES;\" 2>&1")
print(o.strip())

# Verify
print("\n=== Verify grants ===")
o = run("mysql -u root -pLz88192603!@# -e \"SELECT user, host FROM mysql.user WHERE user='gaokao_user'\" 2>&1")
print(o)

# Also update crawler .env password to match
print("\n=== Update crawler DB_PASSWORD ===")
ssh2 = paramiko.SSHClient()
ssh2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh2.connect("199.193.126.80", username="root", password="SGM7VVPAPfGe", timeout=15)
stdin, stdout, stderr = ssh2.exec_command(
    "sed -i 's/^DB_PASSWORD=.*/D...' /root/gaokao-crawler/.env && echo DONE"
)
print(stdout.read().decode().strip())

# Test connection via tunnel
print("\n=== Test crawler MySQL via tunnel ===")
stdin, stdout, stderr = ssh2.exec_command(
    "cd /root/gaokao-crawler && venv/bin/python3 -c \""
    "from db.connection import SessionFactory; "
    "from sqlalchemy import text; "
    "db = SessionFactory(); "
    "r = db.execute(text('SELECT COUNT(*) FROM admission_history')).scalar(); "
    "print('admission_history rows:', r); "
    "r2 = db.execute(text('SELECT COUNT(*) FROM schools')).scalar(); "
    "print('schools rows:', r2); "
    "db.close()"
    "\" 2>&1",
    timeout=20
)
print(stdout.read().decode())

ssh2.close()
ssh.close()
