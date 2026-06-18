"""Test algorithm with multiple scenarios"""
import urllib.request, json

def test(province, score, intended, label):
    data = json.dumps({"phone":"13800138000","password":"test123"}).encode()
    req = urllib.request.Request("http://121.41.69.234/auth/login", data=data, headers={"Content-Type":"application/json"})
    resp = urllib.request.urlopen(req, timeout=10)
    token = json.loads(resp.read())["token"]

    params = {
        "province": province, "score": score, "subject_category": "物理",
        "city_preference": [], "intended_schools": intended,
        "major_preference": [], "personality": [], "economic_level": "一般"
    }
    rec_data = json.dumps(params).encode()
    rec_req = urllib.request.Request("http://121.41.69.234/api/recommendation/generate", data=rec_data, headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {token}"
    })
    rec = json.loads(urllib.request.urlopen(rec_req, timeout=30).read())

    print(f"\n{'='*50}")
    print(f"TEST: {label} | {province} {score}分 | 意向: {', '.join(intended)}")
    print(f"位次: {rec.get('student_rank')}")
    
    # Special attention
    for s in rec.get("special_attention", []):
        tags = '985' if s.get('is_985') else ('211' if s.get('is_211') else '')
        print(f"  ★ 意向: {s['name']} [{tags}] rankProb={s.get('rank_prob')}%")
    
    # Top 8 schools
    print(f"  Top 8:")
    for s in rec.get("schools", [])[:8]:
        tags = '985' if s.get('is_985') else ('211' if s.get('is_211') else '')
        print(f"    [{s.get('tier_label','?')}] {s['name'][:12]:12s} [{tags:3s}] {s.get('rank_prob'):.1f}%")

# Test scenarios
test("山东", 555, ["德州学院"], "555分山东 意向德州学院")
test("河南", 555, ["郑州大学"], "555分河南 意向郑州大学(211)")
test("四川", 520, ["四川大学"], "520分四川 意向四川大学(985)")
