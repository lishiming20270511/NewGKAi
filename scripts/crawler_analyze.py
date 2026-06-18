"""Check data quality and prepare major-level crawl upgrade."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("199.193.126.80", username="root", password="SGM7VVPAPfGe", timeout=15)

# Write analysis script
analysis = (
    "from db.connection import SessionFactory\n"
    "from db.models import AdmissionHistory, SchoolAdmissionCrawlTask\n"
    "from sqlalchemy import text, func, distinct\n"
    "db = SessionFactory()\n"
    "\n"
    "# 1. Data distribution\n"
    "r = db.execute(text(\"SELECT COUNT(DISTINCT major_name) FROM admission_history\")).scalar()\n"
    "print('Distinct majors:', r)\n"
    "\n"
    "r = db.execute(text(\"SELECT COUNT(DISTINCT school_id) FROM admission_history\")).scalar()\n"
    "print('Schools with data:', r)\n"
    "\n"
    "# 2. How many records are school-level vs major-level?\n"
    "r = db.execute(text(\"SELECT COUNT(*) FROM admission_history WHERE major_name=''\")).scalar()\n"
    "print('Empty major_name:', r)\n"
    "\n"
    "r = db.execute(text(\"SELECT COUNT(*) FROM admission_history WHERE major_name='不限专业'\")).scalar()\n"
    "print('unlimited major:', r)\n"
    "\n"
    "# 3. Year distribution\n"
    "rows = db.execute(text(\"SELECT year, COUNT(*) as cnt FROM admission_history GROUP BY year ORDER BY year\")).all()\n"
    "for row in rows:\n"
    "    print(f'Year {row[0]}: {row[1]} records')\n"
    "\n"
    "# 4. Sample of real major names\n"
    "rows = db.execute(text(\"SELECT DISTINCT major_name FROM admission_history WHERE major_name NOT IN ('','null','不限专业') LIMIT 15\")).all()\n"
    "print('Sample majors:', [r[0][:30] for r in rows])\n"
    "\n"
    "# 5. Crawl task status\n"
    "from db.models import SchoolAdmissionCrawlTask\n"
    "total = db.query(func.count(SchoolAdmissionCrawlTask.id)).scalar()\n"
    "pending = db.query(func.count(SchoolAdmissionCrawlTask.id)).filter_by(status='pending').scalar()\n"
    "done = db.query(func.count(SchoolAdmissionCrawlTask.id)).filter_by(status='done').scalar()\n"
    "print(f'Crawl tasks: total={total}, pending={pending}, done={done}')\n"
    "\n"
    "db.close()\n"
)

sftp = ssh.open_sftp()
with sftp.open("/tmp/analyze_data.py", "w") as f:
    f.write(analysis.encode("utf-8"))
sftp.close()

stdin, stdout, stderr = ssh.exec_command(
    "cd /root/gaokao-crawler && PYTHONPATH=/root/gaokao-crawler venv/bin/python3 /tmp/analyze_data.py 2>&1",
    timeout=30
)
print(stdout.read().decode())

ssh.close()
