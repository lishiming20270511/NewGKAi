"""Restart celery workers and monitor initial crawl results."""
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("199.193.126.80", username="root", password="SGM7VVPAPfGe", timeout=15)

def run(cmd, timeout=20):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if err:
        print("  ERR:", err[:300])
    return out

# 1. Kill and restart celery workers
print("=== Restart Celery workers ===")
o = run("pkill -f 'celery.*worker.*crawl' 2>/dev/null; sleep 2; echo KILLED")
print(o.strip())

# Start new workers in background
o = run("cd /root/gaokao-crawler && nohup venv/bin/python3 -m celery -A celery_app worker --loglevel=info --concurrency=2 --queues=crawl --hostname=crawler-overseas@%h > /tmp/celery_v2.log 2>&1 & echo STARTED")
print(o.strip())

time.sleep(3)

# Check workers running
print("\n=== Worker status ===")
o = run("ps aux | grep 'celery.*worker' | grep -v grep | wc -l")
print("Worker processes:", o.strip())

# 2. Dispatch first batch
print("\n=== Dispatch batch ===")
o = run("cd /root/gaokao-crawler && PYTHONPATH=/root/gaokao-crawler venv/bin/python3 dispatch_pending.py 100 2>&1")
print(o)

# 3. Wait a bit then check progress
print("\n=== Wait 10s for processing ===")
time.sleep(10)

print("\n=== Progress after 10s ===")
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
sftp = ssh.open_sftp()
with sftp.open("/tmp/check_progress.py", "w") as f:
    f.write(progress.encode("utf-8"))
sftp.close()

o = run("cd /root/gaokao-crawler && PYTHONPATH=/root/gaokao-crawler venv/bin/python3 /tmp/check_progress.py 2>&1")
print(o)

# 4. Check new log for errors
print("\n=== Recent celery log ===")
o = run("tail -30 /tmp/celery_v2.log 2>/dev/null")
print(o[:800] if o else "(empty)")

ssh.close()
