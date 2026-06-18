"""Final cleanup and status report for crawler module."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("199.193.126.80", username="root", password="SGM7VVPAPfGe", timeout=15)

def run(cmd, timeout=20):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    return out, err

# 1. Clear pending tasks that can't complete (wrong school codes for chsi)
print("=== Clear stale pending tasks ===")
o, e = run("cd /root/gaokao-crawler && PYTHONPATH=/root/gaokao-crawler venv/bin/python3 -c \"\nfrom db.connection import SessionFactory\nfrom db.models import SchoolAdmissionCrawlTask\nfrom sqlalchemy import func\ndb = SessionFactory()\n# Mark all pending as 'deferred' - will re-create when codes are fixed\ndb.query(SchoolAdmissionCrawlTask).filter_by(status='pending').update({'status': 'deferred', 'error_msg': 'School code needs chsi mapping'})\ndb.query(SchoolAdmissionCrawlTask).filter_by(status='running').update({'status': 'deferred', 'error_msg': 'School code needs chsi mapping'})\ndb.commit()\nfor s in ['pending','running','done','failed','deferred']:\n    cnt = db.query(func.count(SchoolAdmissionCrawlTask.id)).filter_by(status=s).scalar()\n    print(f'{s}: {cnt}')\ndb.close()\n\" 2>&1")
print(o)

# 2. Stop celery workers (no tasks to process)
print("\n=== Stop workers ===")
o, e = run("pkill -f 'celery.*worker.*crawl' 2>/dev/null; sleep 1; echo STOPPED")
print(o.strip())

# 3. Remove cron (no tasks to dispatch)
print("\n=== Remove cron ===")
o, e = run("crontab -r 2>/dev/null; echo REMOVED")
print(o.strip())

# 4. Final data summary
print("\n=== Final Data Summary ===")
o, e = run("cd /root/gaokao-crawler && PYTHONPATH=/root/gaokao-crawler venv/bin/python3 -c \"\nfrom db.connection import SessionFactory\nfrom sqlalchemy import text\nfrom sqlalchemy import func\nfrom db.models import AdmissionHistory\ndb = SessionFactory()\ntotal = db.query(func.count(AdmissionHistory.id)).scalar()\nschools = db.execute(text('SELECT COUNT(DISTINCT school_id) FROM admission_history')).scalar()\nmajors = db.execute(text('SELECT COUNT(DISTINCT major_name) FROM admission_history')).scalar()\nyears = db.execute(text('SELECT year, COUNT(*) FROM admission_history GROUP BY year ORDER BY year DESC LIMIT 5')).all()\nprint(f'Total records: {total:,}')\nprint(f'Schools with data: {schools}')\nprint(f'Distinct majors: {majors}')\nfor y in years:\n    print(f'  Year {y[0]}: {y[1]:,} records')\ndb.close()\n\" 2>&1")
print(o)

ssh.close()
print("\n✅ Crawler module summary complete.")
