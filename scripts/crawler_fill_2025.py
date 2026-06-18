"""Batch fill 2025 admission data from gaokao.cn CDN for better recency."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("199.193.126.80", username="root", password="SGM7VVPAPfGe", timeout=15)

# Create a focused 2025 batch filler
script = (
    "#!/usr/bin/env python3\n"
    "\"\"\"Batch fill 2025 admission data from gaokao.cn CDN.\"\"\"\n"
    "import json, time, urllib.request, urllib.error\n"
    "from db.connection import SessionFactory\n"
    "from sqlalchemy import text\n"
    "\n"
    "CDN_BASE = 'https://static-data.gaokao.cn/www/2.0/school'\n"
    "UA = 'Mozilla/5.0 (compatible; gaokao_fill_2025/1.0)'\n"
    "\n"
    "PID_TO_NAME = {\n"
    "    '11':'北京','12':'天津','13':'河北','14':'山西','15':'内蒙古',\n"
    "    '21':'辽宁','22':'吉林','23':'黑龙江','31':'上海','32':'江苏',\n"
    "    '33':'浙江','34':'安徽','35':'福建','36':'江西','37':'山东',\n"
    "    '41':'河南','42':'湖北','43':'湖南','44':'广东','45':'广西',\n"
    "    '46':'海南','50':'重庆','51':'四川','52':'贵州','53':'云南',\n"
    "    '54':'西藏','61':'陕西','62':'甘肃','63':'青海','64':'宁夏','65':'新疆',\n"
    "}\n"
    "\n"
    "def http_get(url):\n"
    "    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': 'https://www.gaokao.cn/'})\n"
    "    try:\n"
    "        with urllib.request.urlopen(req, timeout=10) as r:\n"
    "            return json.loads(r.read().decode('utf-8', errors='ignore'))\n"
    "    except Exception as e:\n"
    "        return None\n"
    "\n"
    "db = SessionFactory()\n"
    "\n"
    "# Get schools with < 5 records for year 2025\n"
    "targets = db.execute(text(\n"
    "    \"SELECT s.school_id, s.name, s.province FROM schools s \"\n"
    "    \"LEFT JOIN (SELECT school_id, COUNT(*) as c2025 FROM admission_history WHERE year=2025 GROUP BY school_id) a \"\n"
    "    \"ON s.school_id = a.school_id \"\n"
    "    \"WHERE (a.c2025 IS NULL OR a.c2025 < 5) AND s.is_985=0 AND s.is_211=0 \"\n"
    "    \"LIMIT 100\"\n"
    ")).all()\n"
    "print(f'Targets (need 2025 data): {len(targets)}')\n"
    "\n"
    "# Load school list for ID lookup\n"
    "print('Loading school list...')\n"
    "sl_data = http_get(f'{CDN_BASE}/list_v2.json')\n"
    "school_list = sl_data if isinstance(sl_data, dict) else {}\n"
    "print(f'CDN schools: {len(school_list)}')\n"
    "\n"
    "saved = 0\n"
    "skipped = 0\n"
    "for s in targets:\n"
    "    sid = str(s.school_id)\n"
    "    if sid not in school_list:\n"
    "        skipped += 1\n"
    "        continue\n"
    "    \n"
    "    # Fetch for school's province (2025 data typically in all provincescore files)\n"
    "    provs_to_try = [s.province] if s.province else ['北京']\n"
    "    \n"
    "    for pname in provs_to_try:\n"
    "        pid = None\n"
    "        for k, v in PID_TO_NAME.items():\n"
    "            if v == pname:\n"
    "                pid = k\n"
    "                break\n"
    "        if not pid:\n"
    "            continue\n"
    "        \n"
    "        data = http_get(f'{CDN_BASE}/{sid}/provincescore/{pid}.json')\n"
    "        if not data or not isinstance(data, dict):\n"
    "            continue\n"
    "        \n"
    "        for year_s, type_map in data.items():\n"
    "            try:\n"
    "                year = int(year_s)\n"
    "            except:\n"
    "                continue\n"
    "            if year != 2025:\n"
    "                continue\n"
    "            if not isinstance(type_map, dict):\n"
    "                continue\n"
    "            \n"
    "            for cat, recs in type_map.items():\n"
    "                if not isinstance(recs, list):\n"
    "                    continue\n"
    "                for rec in recs:\n"
    "                    ms = rec.get('min')\n"
    "                    mr = rec.get('min_section')\n"
    "                    if ms is None and mr is None:\n"
    "                        continue\n"
    "                    \n"
    "                    tn = str(rec.get('type_name', ''))\n"
    "                    if any(x in tn for x in ['理', '物理']): cg = '理科'\n"
    "                    elif any(x in tn for x in ['文', '历史']): cg = '文科'\n"
    "                    else: cg = '综合'\n"
    "                    bt = str(rec.get('batch_name', ''))[:30]\n"
    "                    \n"
    "                    # Check dup\n"
    "                    ex = db.execute(text(\n"
    "                        'SELECT id FROM admission_history WHERE school_id=:sid AND year=2025 AND province=:pv AND category=:cg AND major_name=\\'\\''\n"
    "                    ), {'sid': s.school_id, 'pv': pname, 'cg': cg}).first()\n"
    "                    if ex:\n"
    "                        continue\n"
    "                    \n"
    "                    db.execute(text(\n"
    "                        'INSERT INTO admission_history (school_id, major_name, year, province, category, batch, min_score, min_rank) '\n"
    "                        'VALUES (:sid, \\'\\', 2025, :pv, :cg, :bt, :ms, :mr)'\n"
    "                    ), {'sid': s.school_id, 'pv': pname, 'cg': cg, 'bt': bt, 'ms': ms, 'mr': mr})\n"
    "                    saved += 1\n"
    "        time.sleep(0.2)\n"
    "    \n"
    "    if saved % 50 == 0 and saved > 0:\n"
    "        db.commit()\n"
    "        print(f'  {saved} records...')\n"
    "\n"
    "db.commit()\n"
    "print(f'Done: {saved} saved, {skipped} skipped')\n"
    "db.close()\n"
)

sftp = ssh.open_sftp()
with sftp.open("/root/gaokao-crawler/scripts/fill_2025.py", "w") as f:
    f.write(script.encode("utf-8"))
sftp.close()

print("=== Running 2025 data fill (batch of 100 schools) ===")
stdin, stdout, stderr = ssh.exec_command(
    "cd /root/gaokao-crawler && PYTHONPATH=/root/gaokao-crawler timeout 120 venv/bin/python3 scripts/fill_2025.py 2>&1",
    timeout=130
)
out = stdout.read().decode()
err = stderr.read().decode()
print(out[:1500])
if err:
    print("ERR:", err[:300])

# Check results
print("\n=== Updated totals ===")
stdin, stdout, stderr = ssh.exec_command(
    "cd /root/gaokao-crawler && PYTHONPATH=/root/gaokao-crawler venv/bin/python3 -c \"\nfrom db.connection import SessionFactory\nfrom sqlalchemy import text\ndb = SessionFactory()\nfor y in range(2021, 2026):\n    r = db.execute(text('SELECT COUNT(*) FROM admission_history WHERE year=:y'), {'y': y}).scalar()\n    print(f'Year {y}: {r:,}')\ntotal = db.execute(text('SELECT COUNT(*) FROM admission_history')).scalar()\nprint(f'Total: {total:,}')\ndb.close()\n\" 2>&1",
    timeout=20
)
print(stdout.read().decode())

ssh.close()
