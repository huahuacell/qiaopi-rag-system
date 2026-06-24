from app.search.semantic_relevance import (
    row_matches_semantic_guard,
    semantic_guard_terms,
)


def test_semantic_guard_terms_for_marriage_query_keep_evidence_terms():
    terms = semantic_guard_terms("成婚")

    assert "完婚" in terms
    assert "婚事" in terms
    assert "迎娶" in terms


def test_semantic_guard_terms_for_study_query_keep_education_terms():
    terms = semantic_guard_terms("读书")

    assert "学业" in terms
    assert "勤学" in terms
    assert "英文" in terms


def test_semantic_guard_terms_for_exact_person_query_keep_name_terms():
    terms = semantic_guard_terms("宋树钊")

    assert "宋树钊" in terms
    assert "叻宋树钊" in terms


def test_semantic_guard_terms_for_mother_query_keep_only_mother_aliases():
    terms = semantic_guard_terms("母亲")

    assert "母亲" in terms
    assert "慈亲" in terms
    assert "家慈" in terms
    assert "岳母" not in terms
    assert "祖母" not in terms


def test_mother_guard_rejects_other_kinship_terms():
    terms = semantic_guard_terms("母亲")

    assert row_matches_semantic_guard(
        {"unit_text": "慈亲大人膝下：儿在外平安，伏祈勿念。"},
        terms,
        query="母亲",
    )
    assert row_matches_semantic_guard(
        {"recipient": "潮安南桂家母亲大人", "unit_text": "敬禀者，兹奉上大洋银伍元。"},
        terms,
        query="母亲",
    )
    assert not row_matches_semantic_guard(
        {"unit_text": "兹者家中，前在岳母大人处，先行调借银项。"},
        terms,
        query="母亲",
    )
    assert not row_matches_semantic_guard(
        {"unit_text": "兹奉上港币四十元，计奉上祖母大人、外祖母大人各伍元。"},
        terms,
        query="母亲",
    )
    assert not row_matches_semantic_guard(
        {"unit_text": "敬禀者，谅大人玉体康健为慰。"},
        terms,
        query="母亲",
    )


def test_semantic_guard_rejects_short_signature_noise():
    terms = semantic_guard_terms("成婚")

    assert row_matches_semantic_guard(
        {"unit_text": "凤光孙儿经于农历十一月廿六日完婚，本次婚事草草而已。"},
        terms,
    )
    assert not row_matches_semantic_guard(
        {"unit_text": "儿成子梅托"},
        terms,
    )


def test_strict_person_guard_rejects_low_information_tail_units():
    terms = semantic_guard_terms("宋树钊")

    assert not row_matches_semantic_guard(
        {
            "unit_type": "closing",
            "unit_text": "男树钊禀",
            "title_reference": "叻宋树钊致父亲侨批",
        },
        terms,
        query="宋树钊",
    )
    assert row_matches_semantic_guard(
        {
            "unit_type": "record_full",
            "unit_text": "叻宋树钊来批，内述家中近况并托人查收银信，信中多处涉及家计安排。",
            "title_reference": "叻宋树钊致父亲侨批",
        },
        terms,
        query="宋树钊",
    )
    assert row_matches_semantic_guard(
        {
            "unit_type": "style_reference",
            "unit_text": "树钊贤侄收知：兹外附去国币伍万元，至祈查收。",
            "title_reference": "八月廿一日（约1949前），叻老婶寄澄邑下蓬宋树钊贤侄",
        },
        terms,
        query="宋树钊",
    )
