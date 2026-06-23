from app.validation.evidence_mapper import map_generated_text_to_evidence


def test_generated_sentences_map_to_traceable_evidence_with_offsets():
    generated = "信中说明寄去洋银四元供家用。并向母亲报平安。"
    mappings = map_generated_text_to_evidence(
        generated,
        [
            {
                "record_id": "CSQP-SFHC-TEXT-017",
                "unit_id": "UNIT-REMITTANCE",
                "source_column": "body_core",
                "unit_text": "带去洋银肆元，至照查收，以安家计。",
            },
            {
                "record_id": "CSQP-SFHC-TEXT-017",
                "unit_id": "UNIT-SAFETY",
                "source_column": "evidence_safety",
                "unit_text": "儿在外平安，伏祈慈亲勿念。",
            },
        ],
    )

    assert len(mappings) == 2
    for mapping in mappings:
        assert generated[mapping["generated_start"] : mapping["generated_end"]] == mapping[
            "target_span"
        ]
        assert mapping["mapping_method"] == "lexical-evidence-map-v1"
        assert mapping["record_id"] == "CSQP-SFHC-TEXT-017"
        assert mapping["unit_id"]
        assert mapping["similarity_score"] > 0
        assert mapping["needs_review"] is False


def test_unmatched_generated_sentence_is_marked_for_review():
    mappings = map_generated_text_to_evidence(
        "新增了完全无依据的海外经商情节。",
        [
            {
                "record_id": "R1",
                "unit_id": "U1",
                "source_column": "body_core",
                "unit_text": "母亲大人尊前，儿平安。",
            }
        ],
    )

    assert mappings[0]["unit_id"] == ""
    assert mappings[0]["reason"] == "no_supported_evidence_match"
    assert mappings[0]["needs_review"] is True


def test_style_transfer_maps_user_content_and_knowledge_style_separately():
    generated = "母亲平安，寄回八元，请查收。"
    mappings = map_generated_text_to_evidence(
        generated,
        [
            {
                "record_id": "R1",
                "unit_id": "STYLE-REMITTANCE",
                "unit_type": "remittance",
                "source_column": "evidence_remittance",
                "unit_text": "奉上银捌元，至时查收。",
                "retrieval_sources": ["keyword", "semantic"],
            }
        ],
        input_text="母亲您好，我平安。这次寄八元回家，请您查收。",
    )

    content_rows = [row for row in mappings if row["evidence_role"] == "content"]
    style_rows = [row for row in mappings if row["evidence_role"] == "style"]
    assert content_rows
    assert content_rows[0]["reason"] == "user_input_support"
    assert content_rows[0]["source_field"] == "user_input"
    assert content_rows[0]["source_text"]
    assert content_rows[0]["needs_review"] is False
    assert style_rows
    assert style_rows[0]["reason"] == "hybrid_slot_style_support"
    assert style_rows[0]["slot_match"] is True
    assert style_rows[0]["source_unit_type"] == "remittance"
    assert style_rows[0]["record_id"] == "R1"
    assert all(
        row["mapping_method"] == "dual-evidence-map-v2"
        for row in mappings
    )


def test_style_mapping_prefers_prompt_injected_knowledge_and_can_return_two_sources():
    mappings = map_generated_text_to_evidence(
        "本月寄回三十元，二十元作家用，十元给孩子添衣。",
        [
            {
                "record_id": "R-INJECTED-1",
                "unit_id": "STYLE-1",
                "unit_type": "remittance",
                "source_column": "evidence_remittance",
                "unit_text": "现在邮上七十五元，作为家用，请查收。",
                "retrieval_sources": ["keyword", "semantic"],
                "prompt_included": True,
            },
            {
                "record_id": "R-INJECTED-2",
                "unit_id": "STYLE-2",
                "unit_type": "remittance",
                "source_column": "evidence_remittance",
                "unit_text": "内中分别作家用，并为儿女添置衣物。",
                "retrieval_sources": ["semantic"],
                "prompt_included": True,
            },
            {
                "record_id": "R-NOT-INJECTED",
                "unit_id": "STYLE-3",
                "unit_type": "remittance",
                "source_column": "evidence_remittance",
                "unit_text": "本月寄回三十元，二十元作家用，十元给孩子添衣。",
                "retrieval_sources": ["keyword"],
                "prompt_included": False,
            },
        ],
        input_text="这个月寄回三十元，二十元留作家用，十元给孩子添衣服。",
    )

    style_rows = [row for row in mappings if row["evidence_role"] == "style"]
    assert 1 <= len(style_rows) <= 2
    assert all(row["prompt_included"] for row in style_rows)
    assert all(row["record_id"] != "R-NOT-INJECTED" for row in style_rows)


def test_functional_slot_mapping_explains_multiple_injected_style_units():
    generated = (
        "淑兰如晤：\n"
        "住处已安，身体无恙，勿念。"
        "本月寄回三十元，二十元作家用，十元给孩子添衣。"
        "平日切勿过劳，有事可请二叔照应。"
        "钱信妥收，盼即回音。\n"
        "夫木泉泐"
    )
    references = [
        ("opening", "沈氏荆妻收知如晤："),
        ("safety", "余事后陈，两地平安。"),
        ("remittance", "顺便付去大银捌元，到时查收家用。"),
        ("family_care", "望诸宜珍摄，切勿过劳。"),
        ("instruction", "见字祈即赐复为盼。"),
        ("closing", "夫杨木良泐"),
    ]
    mappings = map_generated_text_to_evidence(
        generated,
        [
            {
                "record_id": f"R-{index}",
                "unit_id": f"U-{index}",
                "unit_type": slot,
                "source_column": f"evidence_{slot}",
                "unit_text": text,
                "retrieval_sources": ["keyword"],
                "prompt_included": True,
            }
            for index, (slot, text) in enumerate(references, start=1)
        ],
        input_text=generated,
    )

    mapped_slots = {
        row["source_unit_type"]
        for row in mappings
        if row["evidence_role"] == "style" and row["slot_match"]
    }
    assert {
        "opening",
        "safety",
        "remittance",
        "family_care",
        "instruction",
        "closing",
    }.issubset(mapped_slots)
