"""Check celery status and crawl progress after restart attempt."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("199.193.126.80", username="root", password="SGM7VVPAPfGe", timeout=15)

def run(cmd, timeout=20):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode(), stderr.read().decode()

# 1. Check if celery workers are running
print("=== Celery Workers ===")
o, e = run("ps aux | grep 'celery.*worker' | grep -v grep")
print(o)

# 2. Check progress
print("=== Crawl Progress ===")
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

o, e = run("cd /root/gaokao-crawler && PYTHONPATH=/root/gaokao-crawler venv/bin/python3 /tmp/check_progress.py 2>&1")
print(o)
if e:
    print("ERR:", e[:300])

# 3. Try to start celery if not running
if "celery" not in o.lower() or "0" in o:
    print("\n=== Starting Celery (background script) ===")
    start_script = (
        "#!/bin/bash\n"
        "cd /root/gaokao-crawler\n"
        "PYTHONPATH=/root/gaokao-crawler venv/bin/python3 -m celery -A celery_app worker --loglevel=info --concurrency=2 --queues=crawl --hostname=crawler-v2@%h >> /tmp/celery_v2.log 2>&1 &\n"
        "echo PID=$!\n"
    )
    sftp2 = ssh.open_sftp()
    with sftp2.open("/tmp/start_celery.sh", "w") as f:
        f.write(start_script.encode("utf-8"))
    sftp2.close()
    o, e = run("bash /tmp/start_celery.sh && sleep 3 && ps aux | grep 'celery.*worker' | grep -v grep")
    print(o)

# 4. Dispatch more tasks
print("\n=== Dispatch more tasks ===")
o, e = run("cd /root/gaokao-crawler && PYTHONPATH=/root/gaokao-crawler venv/bin/python3 dispatch_pending.py 50 2>&1")
print(o)

# 5. Check log
print("\n=== Recent log ===")
o, e = run("tail -15 /tmp/celery_v2.log 2>/dev/null || tail -15 /root/gaokao-crawler/celery.log 2>/dev/null || echo 'no log'")
print(o[:600])

ssh.close()
