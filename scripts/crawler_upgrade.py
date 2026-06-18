"""Upgrade crawler: lq-1 -> sp-1 for major-level data + re-crawl."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("199.193.126.80", username="root", password="SGM7VVPAPfGe", timeout=15)

# 1. Read current chsi.py
sftp = ssh.open_sftp()
with sftp.open("/root/gaokao-crawler/crawler/parsers/chsi.py", "r") as f:
    chsi_content = f.read().decode("utf-8")

# 2. Patch: lq-1 -> sp-1
if "lq-1" in chsi_content:
    chsi_new = chsi_content.replace("lq-1", "sp-1")
    with sftp.open("/root/gaokao-crawler/crawler/parsers/chsi.py", "w") as f:
        f.write(chsi_new.encode("utf-8"))
    print("Updated chsi.py: lq-1 -> sp-1")
else:
    print("lq-1 not found in chsi.py - may already be updated")

sftp.close()

# 3. Create re-crawl script
recrawl = (
    "#!/usr/bin/env python3\n"
    "\"\"\"Re-crawl all pending schools with major-level data.\"\"\"\n"
    "import sys\n"
    "from db.connection import SessionFactory\n"
    "from db.models import SchoolAdmissionCrawlTask\n"
    "from sqlalchemy import func\n"
    "\n"
    "db = SessionFactory()\n"
    "\n"
    "# Reset all failed/done tasks to pending for re-crawl\n"
    "reset_done = db.query(SchoolAdmissionCrawlTask).filter(\n"
    "    SchoolAdmissionCrawlTask.status.in_(['done', 'failed'])\n"
    ").update({'status': 'pending', 'retry_count': 0, 'error_msg': None}, synchronize_session=False)\n"
    "db.commit()\n"
    "print(f'Reset {reset_done} tasks to pending')\n"
    "\n"
    "# Count by status\n"
    "pending = db.query(func.count(SchoolAdmissionCrawlTask.id)).filter_by(status='pending').scalar()\n"
    "done = db.query(func.count(SchoolAdmissionCrawlTask.id)).filter_by(status='done').scalar()\n"
    "print(f'Tasks: pending={pending}, done={done}')\n"
    "\n"
    "db.close()\n"
)

sftp2 = ssh.open_sftp()
with sftp2.open("/root/gaokao-crawler/scripts/reset_tasks.py", "w") as f:
    f.write(recrawl.encode("utf-8"))
sftp2.close()

# 4. Run reset
print("\n=== Reset crawl tasks ===")
stdin, stdout, stderr = ssh.exec_command(
    "cd /root/gaokao-crawler && PYTHONPATH=/root/gaokao-crawler venv/bin/python3 scripts/reset_tasks.py 2>&1",
    timeout=20
)
print(stdout.read().decode())

# 5. Check celery status
print("\n=== Celery Status ===")
stdin, stdout, stderr = ssh.exec_command(
    "cd /root/gaokao-crawler && ps aux | grep -E 'celery|worker' | grep -v grep",
    timeout=10
)
print(stdout.read().decode() or "(no celery workers running)")

# 6. Start crawl dispatch
print("\n=== Dispatch crawl tasks ===")
stdin, stdout, stderr = ssh.exec_command(
    "cd /root/gaokao-crawler && PYTHONPATH=/root/gaokao-crawler venv/bin/python3 dispatch_pending.py 50 2>&1",
    timeout=20
)
print(stdout.read().decode())

ssh.close()
print("\nDone. Crawler upgraded to sp-1 (major-level) and re-crawl initiated.")
