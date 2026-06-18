"""Set crawler DB password to match new server."""
import paramiko

# Read new server DB password
ssh_prod = paramiko.SSHClient()
ssh_prod.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh_prod.connect("121.41.69.234", username="root", password="Lz88192603!@#", timeout=15)
stdin, stdout, stderr = ssh_prod.exec_command("grep DB_PASSWORD /root/gaokao-ai/.env | cut -d= -f2")
new_db_pass = stdout.read().decode().strip()
print("New server DB_PASSWORD length:", len(new_db_pass))

# Also verify gaokao_user password works locally
stdin, stdout, stderr = ssh_prod.exec_command(
    "mysql -u gaokao_user -p" + new_db_pass + " -h 127.0.0.1 -e 'SELECT 1 as test' 2>&1"
)
print("Local test:", stdout.read().decode().strip())
ssh_prod.close()

# Update crawler .env
ssh_crawl = paramiko.SSHClient()
ssh_crawl.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh_crawl.connect("199.193.126.80", username="root", password="SGM7VVPAPfGe", timeout=15)

# Use Python to update the .env properly (avoid sed escaping issues)
stdin, stdout, stderr = ssh_crawl.exec_command(
    "python3 -c \"\n"
    "lines = open('/root/gaokao-crawler/.env').read().split(chr(10))\n"
    "new_lines = []\n"
    "for line in lines:\n"
    "    if line.startswith('DB_PASSWORD=***        new_lines.append('DB_PASSWORD=*** + '" + new_db_pass + "')\n"
    "    else:\n"
    "        new_lines.append(line)\n"
    "open('/root/gaokao-crawler/.env','w').write(chr(10).join(new_lines))\n"
    "print('OK')\n"
    "\""
)
print("Update result:", stdout.read().decode().strip())

# Verify new password in .env
stdin, stdout, stderr = ssh_crawl.exec_command("grep DB_PASSWORD /root/gaokao-crawler/.env | cut -d= -f2")
crawler_pass = stdout.read().decode().strip()
print("Crawler DB_PASSWORD length:", len(crawler_pass))
print("Passwords match:", new_db_pass == crawler_pass)

# Test connection
print("\n=== Test crawler MySQL ===")
stdin, stdout, stderr = ssh_crawl.exec_command(
    "cd /root/gaokao-crawler && venv/bin/python3 -c \""
    "from db.connection import SessionFactory; "
    "from sqlalchemy import text; "
    "db = SessionFactory(); "
    "r = db.execute(text('SELECT COUNT(*) FROM admission_history')).scalar(); "
    "print('admission_history:', r); "
    "r2 = db.execute(text('SELECT COUNT(*) FROM schools')).scalar(); "
    "print('schools:', r2); "
    "r3 = db.execute(text('SELECT COUNT(*) FROM school_admission_crawl_tasks')).scalar(); "
    "print('crawl_tasks:', r3); "
    "db.close()"
    "\" 2>&1",
    timeout=20
)
print(stdout.read().decode())

ssh_crawl.close()
