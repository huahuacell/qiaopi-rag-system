import pytest

from app.graph.normalizers import (
    KINSHIP_TERM,
    NAMED_PERSON,
    NO_KINSHIP_TYPE,
    normalize_kinship_people,
    normalize_kinship_person,
)


@pytest.mark.parametrize(
    ("label", "standard_label", "kinship_type"),
    (
        ("黄氏吾妻", "妻子", "wife"),
        ("鳌头乡黄氏吾妻", "妻子", "wife"),
        ("荆妻李氏", "妻子", "wife"),
        ("祖母", "祖母", "grandmother"),
        ("潮汕祖母大人", "祖母", "grandmother"),
        ("祖慈", "祖母", "grandmother"),
        ("祖父", "祖父", "grandfather"),
        ("外祖母", "外祖母", "maternal_grandmother"),
        ("外祖父", "外祖父", "maternal_grandfather"),
        ("岳母", "岳母", "mother_in_law"),
        ("潮汕岳母大人", "岳母", "mother_in_law"),
        ("澄属南砂乡林宅岳母", "岳母", "mother_in_law"),
        ("岳慈亲", "岳母", "mother_in_law"),
        ("岳父", "岳父", "father_in_law"),
        ("岳祖母", "岳祖母", "grandmother_in_law"),
        ("岳祖父", "岳祖父", "grandfather_in_law"),
        ("胞兄", "兄长", "elder_brother"),
        ("吾兄", "兄长", "elder_brother"),
        ("表兄", "兄长", "elder_brother"),
        ("兄台", "兄长", "elder_brother"),
        ("鹤巢乡李再赐胞兄", "兄长", "elder_brother"),
        ("胞弟", "弟弟", "younger_brother"),
        ("英弟", "弟弟", "younger_brother"),
        ("下蓬英弟", "弟弟", "younger_brother"),
        ("逞大弟", "弟弟", "younger_brother"),
        ("姻弟", "弟弟", "younger_brother"),
        ("吾姊", "姐姐", "elder_sister"),
        ("姻姊", "姐姐", "elder_sister"),
        ("妹", "妹妹", "younger_sister"),
        ("嫂嫂", "嫂子", "sister_in_law"),
        ("表嫂", "嫂子", "sister_in_law"),
        ("隆都潘舜良女儿", "女儿", "daughter"),
        ("儿", "儿子", "son"),
        ("孩儿", "儿子", "son"),
        ("双亲", "双亲", "parents"),
        ("慈亲", "母亲", "mother"),
    ),
)
def test_embedded_kinship_terms_normalize(label, standard_label, kinship_type):
    result = normalize_kinship_person(label)

    assert result.standard_label == standard_label
    assert result.person_kind == KINSHIP_TERM
    assert result.kinship_type == kinship_type
    assert result.raw_label == label
    assert label in result.raw_labels
    assert result.detected_terms


def test_parents_do_not_collapse_to_mother():
    result = normalize_kinship_person("双亲")

    assert result.standard_label == "双亲"
    assert result.kinship_type == "parents"
    assert result.standard_label != "母亲"
    assert result.is_collective_kinship is True
    assert result.member_labels == ("父亲", "母亲")
    assert result.member_kinship_types == ("father", "mother")


@pytest.mark.parametrize(
    ("label", "standard_label", "kinship_type", "member_labels", "member_kinship_types"),
    (
        ("双亲", "双亲", "parents", ("父亲", "母亲"), ("father", "mother")),
        ("父母", "双亲", "parents", ("父亲", "母亲"), ("father", "mother")),
        ("二亲", "双亲", "parents", ("父亲", "母亲"), ("father", "mother")),
        ("家双亲大人", "双亲", "parents", ("父亲", "母亲"), ("father", "mother")),
        (
            "岳双亲",
            "岳父母",
            "parents_in_law",
            ("岳父", "岳母"),
            ("father_in_law", "mother_in_law"),
        ),
        (
            "潮汕岳双亲大人",
            "岳父母",
            "parents_in_law",
            ("岳父", "岳母"),
            ("father_in_law", "mother_in_law"),
        ),
        (
            "岳父母",
            "岳父母",
            "parents_in_law",
            ("岳父", "岳母"),
            ("father_in_law", "mother_in_law"),
        ),
        (
            "外祖父母",
            "外祖父母",
            "maternal_grandparents",
            ("外祖父", "外祖母"),
            ("maternal_grandfather", "maternal_grandmother"),
        ),
        ("祖父母", "祖父母", "grandparents", ("祖父", "祖母"), ("grandfather", "grandmother")),
        (
            "岳祖父母",
            "岳祖父母",
            "grandparents_in_law",
            ("岳祖父", "岳祖母"),
            ("grandfather_in_law", "grandmother_in_law"),
        ),
    ),
)
def test_stable_collective_kinship_terms_remain_collective_nodes(
    label,
    standard_label,
    kinship_type,
    member_labels,
    member_kinship_types,
):
    results = normalize_kinship_people(label)

    assert len(results) == 1
    result = results[0]
    assert result.standard_label == standard_label
    assert result.person_kind == KINSHIP_TERM
    assert result.kinship_type == kinship_type
    assert result.is_collective_kinship is True
    assert result.member_labels == member_labels
    assert result.member_kinship_types == member_kinship_types
    assert label.replace("、", "") in result.raw_labels


def test_self_signature_male_character_requires_qiaopi_context():
    no_context = normalize_kinship_person("男")
    with_context = normalize_kinship_person("男", source_field="sender")

    assert no_context.standard_label == "男"
    assert no_context.person_kind == NAMED_PERSON
    assert no_context.kinship_type == NO_KINSHIP_TYPE

    assert with_context.standard_label == "儿子"
    assert with_context.person_kind == KINSHIP_TERM
    assert with_context.kinship_type == "son"


def test_named_people_and_non_kinship_titles_are_not_unknown_kinship():
    for label in ("丁南", "丁炳南", "丁陈氏", "万乘", "万道", "先生"):
        result = normalize_kinship_person(label)

        assert result.standard_label == label
        assert result.person_kind == NAMED_PERSON
        assert result.kinship_type == NO_KINSHIP_TYPE
        assert result.needs_review is False


def test_raw_labels_and_detected_terms_are_preserved():
    result = normalize_kinship_person("黄氏吾妻", raw_labels=["鳌头乡黄氏吾妻"])

    assert result.standard_label == "妻子"
    assert "黄氏吾妻" in result.raw_labels
    assert "鳌头乡黄氏吾妻" in result.raw_labels
    assert "吾妻" in result.detected_terms


def test_in_law_parent_terms_do_not_collapse_to_blood_parent_nodes():
    result = normalize_kinship_person("岳慈亲")

    assert result.standard_label == "岳母"
    assert result.kinship_type == "mother_in_law"
    assert result.needs_review is False
    assert "岳慈亲" in result.detected_terms


def test_compound_maternal_grandparents_stays_collective():
    results = normalize_kinship_people("外祖父母")
    result = results[0]

    assert len(results) == 1
    assert result.standard_label == "外祖父母"
    assert result.kinship_type == "maternal_grandparents"
    assert result.member_labels == ("外祖父", "外祖母")
    assert result.member_kinship_types == ("maternal_grandfather", "maternal_grandmother")
    assert "外祖父母" in result.raw_labels
    assert result.needs_review is False


def test_mixed_affinal_sibling_labels_split_to_elder_sister_and_younger_brother():
    results = normalize_kinship_people("妙姿姻姊、家国姻弟")
    by_type = {result.kinship_type: result for result in results}

    assert by_type["elder_sister"].standard_label == "姐姐"
    assert by_type["younger_brother"].standard_label == "弟弟"
    assert all("妙姿姻姊家国姻弟" in result.raw_labels for result in results)
    assert all(result.needs_review is False for result in results)


def test_mixed_in_law_grandmother_and_mother_labels_split():
    results = normalize_kinship_people("岳祖母、岳慈亲")
    by_type = {result.kinship_type: result for result in results}

    assert by_type["grandmother_in_law"].standard_label == "岳祖母"
    assert by_type["mother_in_law"].standard_label == "岳母"
    assert all("岳祖母岳慈亲" in result.raw_labels for result in results)
