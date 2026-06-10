from collections import Counter

from app.ingestion.build_database import read_processed_inputs
from app.ingestion.build_retrieval_units import build_retrieval_units


def test_retrieval_units_are_traceable_and_deduplicated():
    inputs = read_processed_inputs()
    wide_table = inputs["wide_table"]
    evidence_spans = inputs["evidence_spans"]
    units = build_retrieval_units(wide_table, evidence_spans)

    assert len(units) > len(wide_table)

    required_fields = {
        "unit_id",
        "record_id",
        "unit_type",
        "source_column",
        "unit_text",
        "title_reference",
        "sender",
        "recipient",
        "date_text",
        "main_intent",
        "theme_tags",
        "style_keywords",
        "relationship_type",
        "place_mentions_normalized",
        "retrieval_keywords",
        "weight",
        "evidence_type",
        "fts_text",
        "raw_json",
    }
    assert required_fields.issubset(units[0])
    assert all(unit["unit_id"] for unit in units)
    assert all(unit["unit_text"] for unit in units)
    assert all(unit["fts_text"] for unit in units)

    duplicate_keys = Counter(
        (
            unit["record_id"],
            unit["unit_type"],
            "".join(str(unit["unit_text"]).split()),
        )
        for unit in units
    )
    assert max(duplicate_keys.values()) == 1


def test_retrieval_units_include_expected_unit_types():
    inputs = read_processed_inputs()
    units = build_retrieval_units(inputs["wide_table"], inputs["evidence_spans"])
    unit_types = {unit["unit_type"] for unit in units}

    assert "record_full" in unit_types
    assert "body_core" in unit_types
    assert "remittance" in unit_types
    assert "style_reference" in unit_types
    assert "rag_summary" in unit_types
