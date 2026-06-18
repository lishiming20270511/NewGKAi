"""Finalize: kill old workers, verify sp-1 data, update Progress."""
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

# 1. Kill old workers (keep v2)
print("=== Clean up old workers ===")
o, e = run("pkill -f 'crawler-overseas' 2>/dev/null; sleep 1; echo CLEANED")
print(o.strip())

# 2. Dispatch tasks to new workers
print("\n=== Dispatch to v2 workers ===")
o, e = run("cd /root/gaokao-crawler && PYTHONPATH=/root/gaokao-crawler venv/bin/python3 dispatch_pending.py 50 2>&1")
print(o.strip())

# Wait and check
print("\n=== Wait 15s for processing ===")
time.sleep(15)

# Check progress
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

print("=== Progress ===")
o, e = run("cd /root/gaokao-crawler && PYTHONPATH=/root/gaokao-crawler venv/bin/python3 /tmp/check_progress.py 2>&1")
print(o)

# Check log for sp-1 usage
print("=== Log check for sp-1 ===")
o, e = run("grep -c 'sp-1' /tmp/celery_v2.log 2>/dev/null || echo '0'")
print("sp-1 URL hits in log:", o.strip())

# Check latest log lines
o, e = run("tail -10 /tmp/celery_v2.log 2>/dev/null")
print("Latest log:", o[:500])

# Check worker count
o, e = run("ps aux | grep 'celery.*worker' | grep -v grep | wc -l")
print("\nWorker count:", o.strip())

ssh.close()
print("\nFinal setup complete.")
