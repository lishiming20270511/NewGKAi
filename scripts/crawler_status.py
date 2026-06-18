"""Check production DB crawl task status and test URL change."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("199.193.126.80", username="root", password="SGM7VVPAPfGe", timeout=20)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    out = stdout.read().decode()
    err = stderr.read().decode()
    return out, err

# Check autossh tunnel
print("=== SSH Tunnel Status ===")
o, e = run("ps aux | grep autossh | grep -v grep")
print(o)

# Check crawler DB via the tunnel
print("\n=== Crawl Task Status (via SSH tunnel) ===")
o, e = run("cd /root/gaokao-crawler && python3 -c \"\nfrom db.connection import SessionFactory\nfrom db.models import SchoolAdmissionCrawlTask\nfrom sqlalchemy import func\ndb = SessionFactory()\ntotal = db.query(func.count(SchoolAdmissionCrawlTask.id)).scalar()\npending = db.query(func.count(SchoolAdmissionCrawlTask.id)).filter_by(status='pending').scalar()\nrunning = db.query(func.count(SchoolAdmissionCrawlTask.id)).filter_by(status='running').scalar()\ndone = db.query(func.count(SchoolAdmissionCrawlTask.id)).filter_by(status='done').scalar()\nfailed = db.query(func.count(SchoolAdmissionCrawlTask.id)).filter_by(status='failed').scalar()\nprint(f'Total tasks: {total}')\nprint(f'Pending: {pending}, Running: {running}, Done: {done}, Failed: {failed}')\n# Show some pending tasks\nif pending > 0:\n    tasks = db.query(SchoolAdmissionCrawlTask).filter_by(status='pending').limit(5).all()\n    for t in tasks:\n        print(f'  PENDING: {t.school_name} ({t.school_code}) year={t.year}')\ndb.close()\n\" 2>&1")
print(o)
if e:
    print("ERR:", e[:500])

# Check admission_history data
print("\n=== Admission History Data ===")
o, e = run("cd /root/gaokao-crawler && python3 -c \"\nfrom db.connection import SessionFactory\nfrom db.models import AdmissionHistory\nfrom sqlalchemy import func\ndb = SessionFactory()\ntotal = db.query(func.count(AdmissionHistory.id)).scalar()\nschools = db.query(func.count(func.distinct(AdmissionHistory.school_id))).scalar()\nmajors = db.query(func.count(func.distinct(AdmissionHistory.major_name))).scalar()\nprint(f'Total records: {total}')\nprint(f'Distinct schools: {schools}')\nprint(f'Distinct majors: {majors}')\n# Show sample\nsample = db.query(AdmissionHistory).limit(5).all()\nfor r in sample:\n    print(f'  school_id={r.school_id} major={r.major_name} year={r.year} province={r.province} score={r.min_score} rank={r.min_rank}')\ndb.close()\n\" 2>&1")
print(o)
if e:
    print("ERR:", e[:500])

ssh.close()
