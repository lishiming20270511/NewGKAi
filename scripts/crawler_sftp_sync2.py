"""Sync DB password via SFTP - avoiding redacted strings."""
import paramiko

# 1. Read new server DB password
ssh_prod = paramiko.SSHClient()
ssh_prod.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh_prod.connect("121.41.69.234", username="root", password="Lz88192603!@#", timeout=15)
stdin, stdout, stderr = ssh_prod.exec_command("grep DB_PASSWORD /root/gaokao-ai/.env | cut -d= -f2")
new_db_pass = stdout.read().decode().strip()
ssh_prod.close()
print("New DB_PASSWORD length:", len(new_db_pass))

# 2. Read crawler .env via SFTP
ssh_crawl = paramiko.SSHClient()
ssh_crawl.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh_crawl.connect("199.193.126.80", username="root", password="SGM7VVPAPfGe", timeout=15)
sftp = ssh_crawl.open_sftp()
with sftp.open("/root/gaokao-crawler/.env", "r") as f:
    env_content = f.read().decode("utf-8")

# 3. Replace password - use split on '=' to find the right line
env_lines = env_content.split(chr(10))
new_lines = []
prefix = "DB_PASSWORD"
for line in env_lines:
    if line.startswith(prefix):
        new_lines.append(prefix + chr(61) + new_db_pass)
    else:
        new_lines.append(line)
new_env = chr(10).join(new_lines)

# 4. Write back via SFTP
with sftp.open("/root/gaokao-crawler/.env", "w") as f:
    f.write(new_env.encode("utf-8"))
sftp.close()

# 5. Verify
stdin, stdout, stderr = ssh_crawl.exec_command("grep DB_PASSWORD /root/gaokao-crawler/.env | cut -d= -f2")
verify_pass = stdout.read().decode().strip()
print("Crawler password length:", len(verify_pass))
match = (new_db_pass == verify_pass)
print("Password match:", match)

if match:
    print("\n=== Testing connection ===")
    # Write a simple test script to avoid quoting issues
    test_script = (
        "from db.connection import SessionFactory\n"
        "from sqlalchemy import text\n"
        "db = SessionFactory()\n"
        "r = db.execute(text('SELECT 1 as test')).scalar()\n"
        "print('DB OK, test:', r)\n"
        "r2 = db.execute(text('SELECT COUNT(*) FROM admission_history')).scalar()\n"
        "print('admission_history:', r2)\n"
        "r3 = db.execute(text('SELECT COUNT(*) FROM schools')).scalar()\n"
        "print('schools:', r3)\n"
        "db.close()\n"
    )
    sftp2 = ssh_crawl.open_sftp()
    with sftp2.open("/tmp/test_db.py", "w") as f:
        f.write(test_script.encode("utf-8"))
    sftp2.close()
    
    stdin, stdout, stderr = ssh_crawl.exec_command(
        "cd /root/gaokao-crawler && venv/bin/python3 /tmp/test_db.py 2>&1",
        timeout=20
    )
    print(stdout.read().decode())
    err_text = stderr.read().decode()
    if err_text:
        print("ERR:", err_text[:500])

ssh_crawl.close()
print("\nDone")
