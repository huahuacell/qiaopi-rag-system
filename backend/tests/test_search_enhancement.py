from app.search.query_expansion import expand_query


def test_query_expansion_maps_modern_terms_to_qiaopi_terms():
    mother = expand_query("母亲")
    remittance = expand_query("寄款")

    assert "慈亲" in mother.expansion_terms or "膝下" in mother.expansion_terms
    assert "批款" in remittance.expansion_terms or "寄上" in remittance.expansion_terms
    assert mother.original_terms == ["母亲"]
    assert mother.strong_expansion_terms
    assert mother.medium_expansion_terms
    assert mother.original_query == "母亲"
    assert mother.normalized_query == "母亲"
    assert "母亲" in mother.expanded_query


def test_study_query_expansion_uses_weighted_precision_groups():
    expanded = expand_query("读书 勤俭")

    assert expanded.original_terms == ["读书", "勤俭"]
    assert {"勤读", "勤学", "学业", "节俭"}.issubset(set(expanded.strong_expansion_terms))
    assert {"书馆", "课程", "成绩", "温习", "持家", "省用"}.issubset(
        set(expanded.medium_expansion_terms)
    )
    assert {"教训", "务望"}.issubset(set(expanded.weak_expansion_terms))


def test_query_normalization_removes_unsafe_punctuation():
    expanded = expand_query(" 母亲??? 寄款* 查收 ")

    assert expanded.normalized_query == "母亲 寄款 查收"
    assert "?" not in expanded.expanded_query
    assert "*" not in expanded.expanded_query
