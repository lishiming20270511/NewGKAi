"""Test algorithm: 555 score + 德州学院 + 中国海洋大学"""
import urllib.request, json

try:
    # Login
    data = json.dumps({"phone":"13800138000","password":"test123"}).encode()
    req = urllib.request.Request("http://121.41.69.234/auth/login", data=data, headers={"Content-Type":"application/json"})
    resp = urllib.request.urlopen(req, timeout=10)
    d = json.loads(resp.read())
    token = d["token"]

    # Test recommendation
    params = {
        "province": "山东", "score": 555, "subject_category": "物理",
        "city_preference": [], "intended_schools": ["德州学院"],
        "major_preference": [], "personality": [], "economic_level": "一般"
    }
    rec_data = json.dumps(params).encode()
    rec_req = urllib.request.Request("http://121.41.69.234/api/recommendation/generate", data=rec_data, headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {token}"
    })
    rec_resp = urllib.request.urlopen(rec_req, timeout=30)
    rec = json.loads(rec_resp.read())

    print(f"Student rank: {rec.get('student_rank')}")
    
    print(f"\n=== 意向学校 ===")
    for s in rec.get("special_attention", []):
        print(f"  {s['name']}: rankProb={s.get('rank_prob')}% quality={s.get('data_quality')}")

    print(f"\n=== Top 10 ===")
    for s in rec.get("schools", [])[:10]:
        tags = []
        if s.get('is_985'): tags.append('985')
        if s.get('is_211'): tags.append('211')
        print(f"  [{s.get('tier_label','?')}] {s['name']}: {s.get('rank_prob')}% {'/'.join(tags)}")

    print(f"\n=== 中国海洋大学 ===")
    for s in rec.get("schools", []):
        if "中国海洋" in s.get("name", ""):
            print(f"  rankProb={s.get('rank_prob')}% tier={s.get('tier_label')}")

    # Also query specific schools
    print(f"\n=== DB data check ===")
    # Get school info
    for name in ["中国海洋大学", "德州学院"]:
        search_data = json.dumps({"query": name}).encode()
        search_req = urllib.request.Request(f"http://121.41.69.234/api/schools/search?q={urllib.parse.quote(name)}&limit=3", 
            headers={"Authorization": f"Bearer {token}"})
        try:
            search_resp = urllib.request.urlopen(search_req, timeout=10)
            schools = json.loads(search_resp.read())
            for s in schools[:1]:
                print(f"  {s['name']}: id={s.get('school_id')} 985={s.get('is_985')} 211={s.get('is_211')} type={s.get('school_type')}")
        except Exception as e:
            print(f"  {name}: search error - {e}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
