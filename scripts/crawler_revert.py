"""Revert to lq-1 and restart workers. The data was already major-level."""
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("199.193.126.80", username="root", password="SGM7VVPAPfGe", timeout=15)

def run(cmd, timeout=20):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    return out, err

# 1. Revert chsi.py: sp-1 -> lq-1
print("=== Revert sp-1 -> lq-1 ===")
sftp = ssh.open_sftp()
with sftp.open("/root/gaokao-crawler/crawler/parsers/chsi.py", "r") as f:
    content = f.read().decode("utf-8")
content = content.replace("sp-1", "lq-1")
with sftp.open("/root/gaokao-crawler/crawler/parsers/chsi.py", "w") as f:
    f.write(content.encode("utf-8"))
sftp.close()
print("Reverted to lq-1")

# Verify
o, e = run("grep 'lq-1\\|sp-1' /root/gaokao-crawler/crawler/parsers/chsi.py | head -3")
print("Current URL:", o.strip())

# 2. Restart workers
print("\n=== Restart workers ===")
run("pkill -f 'celery.*worker.*crawl' 2>/dev/null")
time.sleep(2)

# Start fresh workers
run("bash /tmp/start_celery.sh 2>/dev/null; echo done" )
time.sleep(3)

# 3. Reset failed tasks back to pending
print("\n=== Reset tasks ===")
o, e = run("cd /root/gaokao-crawler && PYTHONPATH=/root/gaokao-crawler venv/bin/python3 scripts/reset_tasks.py 2>&1")
print(o.strip())

# 4. Dispatch
print("\n=== Dispatch ===")
o, e = run("cd /root/gaokao-crawler && PYTHONPATH=/root/gaokao-crawler venv/bin/python3 dispatch_pending.py 100 2>&1")
print(o.strip())

# 5. Wait and check
time.sleep(10)
print("\n=== Progress ===")
progress = (
    "from db.connection import SessionFactory\n"
    "from db.models import SchoolAdmissionCrawlTask\n"
    "from sqlalchemy import func\n"
    "db = SessionFactory()\n"
    "for status in ['pending', 'running', 'done', 'failed']:\n"
    "    cnt = db.query(func.count(SchoolAdmissionCrawlTask.id)).filter_by(status=status).scalar()\n"
    "    print(f'{status}: {cnt}')\n"
    "db.close()\n"
)
sftp2 = ssh.open_sftp()
with sftp2.open("/tmp/check_progress.py", "w") as f:
    f.write(progress.encode("utf-8"))
sftp2.close()
o, e = run("cd /root/gaokao-crawler && PYTHONPATH=/root/gaokao-crawler venv/bin/python3 /tmp/check_progress.py 2>&1")
print(o)

# 6. Tail log
o, e = run("tail -5 /tmp/celery_v2.log 2>/dev/null | grep -v '^$'")
print("\nLatest log:", o[:300])

ssh.close()
print("\nDone - reverted to lq-1, workers restarted.")
