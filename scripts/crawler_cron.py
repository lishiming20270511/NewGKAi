"""Set up cron job for continuous crawl dispatch + verify progress."""
import paramiko

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

# 1. Add crontab entry for dispatch every 10 minutes
print("=== Setting up cron ===")
cron_line = "*/10 * * * * cd /root/gaokao-crawler && PYTHONPATH=/root/gaokao-crawler venv/bin/python3 dispatch_pending.py 100 >> /tmp/dispatch.log 2>&1"
# Check existing crontab
existing = run("crontab -l 2>&1")
if "no crontab" in existing.lower():
    new_cron = cron_line + "\n"
else:
    if "dispatch_pending" not in existing:
        new_cron = existing.strip() + "\n" + cron_line + "\n"
    else:
        new_cron = existing
        print("Cron already has dispatch entry")

# Write new crontab
sftp = ssh.open_sftp()
with sftp.open("/tmp/new_crontab.txt", "w") as f:
    f.write(new_cron.encode("utf-8"))
sftp.close()
run("crontab /tmp/new_crontab.txt && echo CRON_OK")
print("Cron set:", run("crontab -l").strip()[:200])

# 2. Check current crawl progress
print("\n=== Current crawl progress ===")
progress_script = (
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
    f.write(progress_script.encode("utf-8"))
sftp2.close()

o = run("cd /root/gaokao-crawler && PYTHONPATH=/root/gaokao-crawler venv/bin/python3 /tmp/check_progress.py 2>&1")
print(o)

# 3. Check celery worker logs for any errors
print("\n=== Recent celery errors ===")
o = run("tail -20 /root/gaokao-crawler/celery.log 2>/dev/null || echo 'no log file'")
print(o[:500])

# 4. Verify the sp-1 URL is being used
print("\n=== Verify sp-1 URL ===")
o = run("grep 'sp-1' /root/gaokao-crawler/crawler/parsers/chsi.py")
print(o.strip() if o.strip() else "sp-1 NOT FOUND in chsi.py")

ssh.close()
print("\nDone.")
