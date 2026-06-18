"""Quick verification of is_985 flags"""
import urllib.request, json

data = json.dumps({"phone":"13800138000","password":"test123"}).encode()
req = urllib.request.Request("http://121.41.69.234/auth/login", data=data, headers={"Content-Type":"application/json"})
resp = urllib.request.urlopen(req, timeout=10)
token = json.loads(resp.read())["token"]

params = {"province": "山东", "score": 555, "subject_category": "物理",
    "city_preference": [], "intended_schools": ["德州学院"], "major_preference": [], "personality": [], "economic_level": "一般"}
rec_req = urllib.request.Request("http://121.41.69.234/api/recommendation/generate", data=json.dumps(params).encode(),
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
rec = json.loads(urllib.request.urlopen(rec_req, timeout=30).read())

for s in rec["schools"][:6]:
    tags = s.get('tags', [])
    print(f"{s['name']:20s} tags={tags} rankProb={s.get('rank_prob')}%")
