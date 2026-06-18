"""Smart batch crawl: use gaokao.cn CDN to fill sparse admission data."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("199.193.126.80", username="root", password="SGM7VVPAPfGe", timeout=15)

# 1. First check: what schools NEED data? Which have sparse admission_history?
print("=== Schools with sparse data ===")
check_script = (
    "from db.connection import SessionFactory\n"
    "from sqlalchemy import text\n"
    "db = SessionFactory()\n"
    "rows = db.execute(text(\n"
    "    'SELECT s.school_id, s.name, s.province, s.is_985, s.is_211, '\n"
    "    'COUNT(ah.id) as cnt '\n"
    "    'FROM schools s LEFT JOIN admission_history ah ON s.school_id = ah.school_id '\n"
    "    'WHERE s.is_985=1 OR s.is_211=1 '\n"
    "    'GROUP BY s.school_id HAVING cnt < 50 ORDER BY cnt LIMIT 20'\n"
    ")).all()\n"
    "for r in rows:\n"
    "    print(f'  id={r[0]} name={r[1]} prov={r[2]} 985={r[3]} 211={r[4]} cnt={r[5]}')\n"
    "db.close()\n"
)
sftp = ssh.open_sftp()
with sftp.open("/tmp/check_sparse.py", "w") as f:
    f.write(check_script.encode("utf-8"))
sftp.close()

stdin, stdout, stderr = ssh.exec_command(
    "cd /root/gaokao-crawler && PYTHONPATH=/root/gaokao-crawler venv/bin/python3 /tmp/check_sparse.py 2>&1",
    timeout=20
)
print(stdout.read().decode())

# 2. Create a focused CDN crawler for priority schools (985/211 with < 50 records)
crawler_script = (
    "#!/usr/bin/env python3\n"
    "\"\"\"Focused CDN crawler: fill admission data for priority schools.\"\"\"\n"
    "import sys, json, time, urllib.request, urllib.error\n"
    "sys.path.insert(0, '/root')\n"
    "from db.connection import SessionFactory\n"
    "from db.models import AdmissionHistory\n"
    "from sqlalchemy import text\n"
    "\n"
    "# gaokao.cn CDN API\n"
    "CDN_BASE = 'https://static-data.gaokao.cn/www/2.0/school'\n"
    "UA = 'Mozilla/5.0 (compatible; batch_crawler/1.0)'\n"
    "\n"
    "PROVINCE_NAME_TO_ID = {\n"
    "    '北京':'11','天津':'12','河北':'13','山西':'14','内蒙古':'15',\n"
    "    '辽宁':'21','吉林':'22','黑龙江':'23','上海':'31','江苏':'32',\n"
    "    '浙江':'33','安徽':'34','福建':'35','江西':'36','山东':'37',\n"
    "    '河南':'41','湖北':'42','湖南':'43','广东':'44','广西':'45',\n"
    "    '海南':'46','重庆':'50','四川':'51','贵州':'52','云南':'53',\n"
    "    '西藏':'54','陕西':'61','甘肃':'62','青海':'63','宁夏':'64','新疆':'65',\n"
    "}\n"
    "\n"
    "def http_get_json(url):\n"
    "    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': 'https://www.gaokao.cn/'})\n"
    "    with urllib.request.urlopen(req, timeout=15) as resp:\n"
    "        raw = resp.read().decode('utf-8', errors='ignore')\n"
    "    data = json.loads(raw)\n"
    "    if isinstance(data, dict) and data.get('code') == '0000':\n"
    "        return data.get('data')\n"
    "    return data\n"
    "\n"
    "# Load school list\n"
    "print('Loading school list...')\n"
    "school_list = http_get_json(f'{CDN_BASE}/list_v2.json')\n"
    "print(f'Loaded {len(school_list)} schools')\n"
    "\n"
    "db = SessionFactory()\n"
    "\n"
    "# Get priority schools (985/211 with < 50 admission records)\n"
    "targets = db.execute(text(\n"
    "    \"SELECT s.school_id, s.name, s.province \"\n"
    "    \"FROM schools s LEFT JOIN admission_history ah ON s.school_id = ah.school_id \"\n"
    "    \"WHERE s.is_985=1 OR s.is_211=1 \"\n"
    "    \"GROUP BY s.school_id HAVING COUNT(ah.id) < 50 LIMIT 30\"\n"
    ")).all()\n"
    "print(f'Target schools: {len(targets)}')\n"
    "\n"
    "saved = 0\n"
    "for s in targets:\n"
    "    # Match school ID in CDN list\n"
    "    sid = str(s.school_id)\n"
    "    if sid not in school_list:\n"
    "        # Try name match\n"
    "        matched = None\n"
    "        for k, v in school_list.items():\n"
    "            if v.get('name', '') == s.name:\n"
    "                matched = k\n"
    "                break\n"
    "        if not matched:\n"
    "            print(f'  SKIP {s.name}: not in CDN list')\n"
    "            continue\n"
    "        sid = matched\n"
    "    \n"
    "    # Fetch for school's own province + key provinces\n"
    "    target_provs = [s.province] if s.province else ['北京', '上海', '广东']\n"
    "    for pname in target_provs:\n"
    "        pid = PROVINCE_NAME_TO_ID.get(pname)\n"
    "        if not pid:\n"
    "            continue\n"
    "        try:\n"
    "            url = f'{CDN_BASE}/{sid}/provincescore/{pid}.json'\n"
    "            data = http_get_json(url)\n"
    "        except Exception as e:\n"
    "            continue\n"
    "        \n"
    "        if not isinstance(data, dict):\n"
    "            continue\n"
    "        \n"
    "        for year_s, type_map in data.items():\n"
    "            try:\n"
    "                year = int(year_s)\n"
    "            except:\n"
    "                continue\n"
    "            if year < 2021 or year > 2025:\n"
    "                continue\n"
    "            if not isinstance(type_map, dict):\n"
    "                continue\n"
    "            for cat, recs in type_map.items():\n"
    "                if not isinstance(recs, list):\n"
    "                    continue\n"
    "                for rec in recs:\n"
    "                    ms = rec.get('min')\n"
    "                    mr = rec.get('min_section')\n"
    "                    batch = str(rec.get('batch_name', ''))[:30]\n"
    "                    # Normalize category\n"
    "                    tn = str(rec.get('type_name', ''))\n"
    "                    if any(x in tn for x in ['理', '物理']): cat_norm = '理科'\n"
    "                    elif any(x in tn for x in ['文', '历史']): cat_norm = '文科'\n"
    "                    else: cat_norm = '综合'\n"
    "                    \n"
    "                    if ms is None and mr is None:\n"
    "                        continue\n"
    "                    \n"
    "                    # Check existing\n"
    "                    exist = db.execute(text(\n"
    "                        'SELECT id FROM admission_history WHERE school_id=:sid AND year=:yr AND province=:pv AND category=:cg AND major_name=\\\'\\''\n"
    "                    ), {'sid': s.school_id, 'yr': year, 'pv': pname, 'cg': cat_norm}).first()\n"
    "                    if exist:\n"
    "                        continue\n"
    "                    \n"
    "                    db.execute(text(\n"
    "                        'INSERT INTO admission_history (school_id, major_name, year, province, category, batch, min_score, min_rank) '\n"
    "                        'VALUES (:sid, \\'\\', :yr, :pv, :cg, :bt, :ms, :mr)'\n"
    "                    ), {'sid': s.school_id, 'yr': year, 'pv': pname, 'cg': cat_norm, 'bt': batch, 'ms': ms, 'mr': mr})\n"
    "                    saved += 1\n"
    "        time.sleep(0.3)  # Rate limit\n"
    "    \n"
    "    if saved % 20 == 0 and saved > 0:\n"
    "        db.commit()\n"
    "        print(f'  Progress: {saved} records...')\n"
    "\n"
    "db.commit()\n"
    "print(f'Done! Saved {saved} new records')\n"
    "db.close()\n"
)

sftp2 = ssh.open_sftp()
with sftp2.open("/root/gaokao-crawler/scripts/cdn_fill.py", "w") as f:
    f.write(crawler_script.encode("utf-8"))
sftp2.close()

# 3. Run the crawler (limited batch first)
print("\n=== Running CDN fill (first 10 schools) ===")
stdin, stdout, stderr = ssh.exec_command(
    "cd /root/gaokao-crawler && PYTHONPATH=/root/gaokao-crawler timeout 120 venv/bin/python3 scripts/cdn_fill.py 2>&1",
    timeout=130
)
out = stdout.read().decode()
err = stderr.read().decode()
print(out[:2000])
if err:
    print("ERR:", err[:500])

# 4. Check results
print("\n=== Results ===")
stdin, stdout, stderr = ssh.exec_command(
    "cd /root/gaokao-crawler && PYTHONPATH=/root/gaokao-crawler venv/bin/python3 -c \"\nfrom db.connection import SessionFactory\nfrom sqlalchemy import text\ndb = SessionFactory()\nr = db.execute(text('SELECT COUNT(*) FROM admission_history')).scalar()\nprint(f'admission_history: {r:,} total records')\nr = db.execute(text('SELECT COUNT(DISTINCT school_id) FROM admission_history')).scalar()\nprint(f'Schools with data: {r}')\ndb.close()\n\" 2>&1",
    timeout=20
)
print(stdout.read().decode())

ssh.close()
