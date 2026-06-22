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
    assert style_rows[0]["reason"] == "hybrid_style_support"
    assert style_rows[0]["record_id"] == "R1"
    assert all(
        row["mapping_method"] == "dual-evidence-map-v2"
        for row in mappings
    )
