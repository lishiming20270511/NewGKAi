"""Sync DB password via SFTP instead of shell commands."""
import paramiko

# 1. Read new server DB password
ssh_prod = paramiko.SSHClient()
ssh_prod.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh_prod.connect("121.41.69.234", username="root", password="Lz88192603!@#", timeout=15)
stdin, stdout, stderr = ssh_prod.exec_command("grep DB_PASSWORD /root/gaokao-ai/.env | cut -d= -f2")
new_db_pass = stdout.read().decode().strip()
ssh_prod.close()
print("New server DB_PASSWORD length:", len(new_db_pass))

# 2. Read crawler .env via SFTP
ssh_crawl = paramiko.SSHClient()
ssh_crawl.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh_crawl.connect("199.193.126.80", username="root", password="SGM7VVPAPfGe", timeout=15)
sftp = ssh_crawl.open_sftp()
with sftp.open("/root/gaokao-crawler/.env", "r") as f:
    env_content = f.read().decode("utf-8")

# 3. Replace password
env_lines = env_content.split('\n')
new_lines = []
for line in env_lines:
    if line.startswith('DB_PASSWORD=***        new_lines.append('DB_PASSWORD=*** + new_db_pass)
    else:
        new_lines.append(line)
new_env = '\n'.join(new_lines)

# 4. Write back via SFTP
with sftp.open("/root/gaokao-crawler/.env", "w") as f:
    f.write(new_env.encode("utf-8"))
sftp.close()

# 5. Verify
stdin, stdout, stderr = ssh_crawl.exec_command("grep DB_PASSWORD /root/gaokao-crawler/.env | cut -d= -f2")
verify_pass = stdout.read().decode().strip()
print("Crawler password length:", len(verify_pass))
print("Match:", new_db_pass == verify_pass)

# Also update old server reference in fetch_school_facts.py env if needed
# And test connection
if new_db_pass == verify_pass:
    print("\n=== Testing connection ===")
    stdin, stdout, stderr = ssh_crawl.exec_command(
        "cd /root/gaokao-crawler && venv/bin/python3 -c \""
        "from db.connection import SessionFactory; "
        "from sqlalchemy import text; "
        "db = SessionFactory(); "
        "r = db.execute(text('SELECT 1 as test')).scalar(); "
        "print('DB OK, test:', r); "
        "r2 = db.execute(text('SELECT COUNT(*) FROM admission_history')).scalar(); "
        "print('admission_history rows:', r2); "
        "db.close()"
        "\" 2>&1",
        timeout=20
    )
    out = stdout.read().decode()
    err = stderr.read().decode()
    print(out)
    if err:
        print("ERR:", err[:500])

ssh_crawl.close()
print("\nDone")
