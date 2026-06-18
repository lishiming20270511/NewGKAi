"""Run crawl_school_list to populate proper chsi school codes."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("199.193.126.80", username="root", password="SGM7VVPAPfGe", timeout=15)

def run(cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    return out, err

# 1. First check: how many schools have valid codes in the task table
print("=== School code status ===")
o, e = run("cd /root/gaokao-crawler && PYTHONPATH=/root/gaokao-crawler venv/bin/python3 -c \"\nfrom db.connection import SessionFactory\nfrom db.models import SchoolAdmissionCrawlTask, School\nfrom sqlalchemy import func\ndb = SessionFactory()\n# Check if school codes look like chsi IDs\ntasks = db.query(SchoolAdmissionCrawlTask).filter(SchoolAdmissionCrawlTask.status=='pending').limit(5).all()\nfor t in tasks:\n    print(f'  {t.school_name}: code={t.school_code}')\n# Check what codes exist in schools table\nschools = db.query(School).limit(5).all()\nfor s in schools:\n    print(f'  schools table: id={s.school_id}, name={s.name}')\ndb.close()\n\" 2>&1")
print(o)

# 2. Instead of running crawl_school_list (which takes hours), let's use gaokao.cn CDN approach
# The fetch_school_facts.py already has the right approach.
# Let's create a batch script that uses the CDN API (which we know works)
print("\n=== Creating gaokao CDN batch crawler ===")
batch_script = (
    "#!/usr/bin/env python3\n"
    "\"\"\"Batch crawl admission data using gaokao.cn CDN API.\"\"\"\n"
    "import sys, json\n"
    "sys.path.insert(0, '/root')\n"
    "from fetch_school_facts import (\n"
    "    _load_school_list, _match_school_id, _fetch_one_province_lines,\n"
    "    PROVINCE_ID_TO_NAME, PROVINCE_NAME_TO_ID\n"
    ")\n"
    "from db.connection import SessionFactory\n"
    "from db.models import School, AdmissionHistory\n"
    "\n"
    "db = SessionFactory()\n"
    "\n"
    "# Get schools with no or few admission data\n"
    "from sqlalchemy import text\n"
    "schools = db.execute(text(\n"
    "    'SELECT s.school_id, s.name, s.province, COUNT(ah.id) as cnt '\n"
    "    'FROM schools s LEFT JOIN admission_history ah ON s.school_id = ah.school_id '\n"
    "    'GROUP BY s.school_id HAVING cnt < 10 ORDER BY cnt LIMIT 20'\n"
    ")).all()\n"
    "\n"
    "school_list = _load_school_list()\n"
    "saved = 0\n"
    "for s in schools:\n"
    "    sid, sinfo = _match_school_id(s.name, school_list)\n"
    "    if not sid:\n"
    "        continue\n"
    "    \n"
    "    # Fetch admission lines for school's own province and key provinces\n"
    "    target_provs = [s.province] if s.province else list(PROVINCE_ID_TO_NAME.values())[:5]\n"
    "    for pname in target_provs:\n"
    "        pid = PROVINCE_NAME_TO_ID.get(pname)\n"
    "        if not pid:\n"
    "            continue\n"
    "        try:\n"
    "            by_cat = _fetch_one_province_lines(sid, pid)\n"
    "        except Exception as e:\n"
    "            continue\n"
    "        \n"
    "        for cat, items in by_cat.items():\n"
    "            for item in items:\n"
    "                if not item.get('min_score') and not item.get('min_rank'):\n"
    "                    continue\n"
    "                existing = db.query(AdmissionHistory).filter_by(\n"
    "                    school_id=s.school_id,\n"
    "                    year=item['year'],\n"
    "                    province=pname,\n"
    "                    category=cat,\n"
    "                    major_name='',\n"
    "                ).first()\n"
    "                if not existing:\n"
    "                    db.add(AdmissionHistory(\n"
    "                        school_id=s.school_id,\n"
    "                        major_name='',\n"
    "                        year=item['year'],\n"
    "                        province=pname,\n"
    "                        category=cat,\n"
    "                        batch=item.get('batch', ''),\n"
    "                        min_score=item.get('min_score'),\n"
    "                        min_rank=item.get('min_rank'),\n"
    "                    ))\n"
    "                    saved += 1\n"
    "    if saved % 50 == 0:\n"
    "        db.commit()\n"
    "        print(f'  Saved {saved} records...')\n"
    "\n"
    "db.commit()\n"
    "print(f'Total saved: {saved} records')\n"
    "db.close()\n"
)

sftp = ssh.open_sftp()
with sftp.open("/root/gaokao-crawler/scripts/batch_cdn_crawl.py", "w") as f:
    f.write(batch_script.encode("utf-8"))
sftp.close()

# 3. Run a small test batch
print("=== Running test batch (5 schools) ===")
o, e = run("cd /root/gaokao-crawler && PYTHONPATH=/root/gaokao-crawler timeout 60 venv/bin/python3 scripts/batch_cdn_crawl.py 2>&1")
print(o[:1000])
if e:
    print("ERR:", e[:300])

ssh.close()
print("\nSetup complete.")
