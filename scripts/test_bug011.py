"""Unit tests for BUG-011 fixes in recommendation.py"""
import sys
sys.path.insert(0, 'D:/dev/NewGKAi')

from api.services.recommendation import (
    SchoolRecord, _is_provincial_key, _is_elite, _is_vocational,
    apply_quality_threshold_filter, TIER_SOLID_MIN,
)

def make_school(**kwargs):
    defaults = dict(
        school_id=1, name="测试大学", province="江苏", city="南京",
        level="一本", school_type="公办本科",
        is_985=False, is_211=False, is_double_first=False,
    )
    defaults.update(kwargs)
    return SchoolRecord(**defaults)

# --- _is_provincial_key ---

def test_provincial_key_public_yiben():
    s = make_school(level="一本", school_type="公办本科")
    assert _is_provincial_key(s) is True, "公办一本应为省重点"

def test_provincial_key_zhongdian():
    s = make_school(level="重点本科", school_type="公办")
    assert _is_provincial_key(s) is True, "重点本科应为省重点"

def test_provincial_key_excludes_elite():
    s = make_school(level="一本", school_type="公办本科", is_211=True)
    assert _is_provincial_key(s) is False, "211院校不应计为省重点（已由_is_elite处理）"

def test_provincial_key_excludes_double_first():
    s = make_school(level="一本", school_type="公办本科", is_double_first=True)
    assert _is_provincial_key(s) is False, "双一流不应计为省重点"

def test_provincial_key_excludes_minban():
    s = make_school(level="一本", school_type="民办本科")
    assert _is_provincial_key(s) is False, "民办院校不应计为省重点"

def test_provincial_key_excludes_vocational():
    s = make_school(level="专科", school_type="公办", name="南京技术学院")
    assert _is_provincial_key(s) is False, "职业技术类不应计为省重点"

def test_provincial_key_excludes_erben():
    s = make_school(level="二本", school_type="公办本科")
    assert _is_provincial_key(s) is False, "二本不应计为省重点"

# --- apply_quality_threshold_filter ---

def test_filter_high_tier0_elite_always_pass():
    """精英院校（985/211/双一流）无论来源都通过冲刺过滤。"""
    s = make_school(is_211=True, tier=0, rank_prob=35.0)
    s.is_neighbor_province = False
    result = apply_quality_threshold_filter([s], "high")
    assert len(result) == 1, "精英院校应通过高分段冲刺过滤"

def test_filter_high_tier0_neighbor_provincial_key_pass():
    """邻省省重点公办一本（非精英）在高分段冲刺过滤中通过。"""
    s = make_school(level="一本", school_type="公办本科", tier=0, rank_prob=35.0)
    s.is_neighbor_province = True
    result = apply_quality_threshold_filter([s], "high")
    assert len(result) == 1, "邻省省重点应通过高分段冲刺过滤"

def test_filter_high_tier0_local_non_elite_blocked():
    """意向城市非精英学校（is_neighbor_province=False）在高分段冲刺过滤中被移除。"""
    s = make_school(level="一本", school_type="公办本科", tier=0, rank_prob=35.0)
    s.is_neighbor_province = False
    result = apply_quality_threshold_filter([s], "high")
    assert len(result) == 0, "本地非精英学校不应通过高分段冲刺过滤"

def test_filter_high_tier0_neighbor_minban_blocked():
    """邻省民办院校即使是省重点格式也被过滤。"""
    s = make_school(level="一本", school_type="民办本科", tier=0, rank_prob=35.0)
    s.is_neighbor_province = True
    result = apply_quality_threshold_filter([s], "high")
    assert len(result) == 0, "邻省民办院校不应通过高分段冲刺过滤"

def test_filter_high_tier1_unchanged():
    """稳妥档（tier=1）过滤规则不受本次改动影响。"""
    s = make_school(level="一本", school_type="公办本科", tier=1, rank_prob=60.0)
    s.is_neighbor_province = True
    result = apply_quality_threshold_filter([s], "high")
    assert len(result) == 1, "稳妥档非职业学校应通过高分段稳妥过滤"

# --- sort_and_slice last resort probability cap ---

from api.services.recommendation import sort_and_slice

def _make_tier0_school(sid, prob, elite=True, neighbor=False):
    s = make_school(school_id=sid, name=f"学校{sid}",
                    is_211=elite, is_double_first=False,
                    rank_prob=prob, tier=0, weighted_prob=prob)
    s.is_neighbor_province = neighbor
    s.tier_label = "冲刺"
    return s

def _make_tier1_school(sid, prob):
    s = make_school(school_id=sid, name=f"稳妥校{sid}",
                    rank_prob=prob, tier=1, weighted_prob=prob)
    s.tier_label = "稳妥"
    return s

def test_last_resort_does_not_add_high_prob_schools():
    """last resort 不得将概率 >=55% 的稳妥学校放入冲刺档。"""
    schools = [
        _make_tier0_school(1, 35.0),
        _make_tier0_school(2, 40.0),
        _make_tier1_school(3, 60.0),
        _make_tier1_school(4, 70.0),
        _make_tier1_school(5, 80.0),
        _make_tier1_school(6, 55.0),  # 恰好在上限
        _make_tier1_school(7, 54.9),  # 恰好在上限以下
    ]
    result = sort_and_slice(schools, personality=[], score_segment="high")
    boost = [s for s in result if s.tier == 0]
    high_prob_in_boost = [s for s in boost if (s.rank_prob or 0) >= 55.0]
    assert len(high_prob_in_boost) == 0, (
        f"冲刺档不应含概率≥55%的学校，实际: {[(s.name, s.rank_prob) for s in high_prob_in_boost]}"
    )

def test_last_resort_allows_borderline_schools():
    """last resort 可借用概率 <55% 的学校填充冲刺档；禁止概率 >=55% 的学校。"""
    schools = [
        _make_tier0_school(1, 35.0),
        _make_tier0_school(2, 40.0, elite=True),
        _make_tier0_school(3, 42.0, elite=True),
        _make_tier1_school(4, 54.0),
        _make_tier1_school(5, 53.0),
        _make_tier1_school(6, 55.0),  # 恰好在上限，不应选
        _make_tier1_school(7, 60.0),  # 超出上限，不应选
    ]
    result = sort_and_slice(schools, personality=[], score_segment="high")
    boost = [s for s in result if s.tier == 0]
    # 验证：冲刺档中概率 >=55% 的学校数为 0
    high_prob_in_boost = [s for s in boost if (s.rank_prob or 0) >= 55.0]
    assert len(high_prob_in_boost) == 0, (
        f"冲刺档不应含概率≥55%的学校，实际: {[(s.name, s.rank_prob) for s in high_prob_in_boost]}"
    )

if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
