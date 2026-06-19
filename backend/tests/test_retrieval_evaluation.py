from __future__ import annotations

from app.evaluation.retrieval_evaluation import (
    evaluate_retrieval,
    load_benchmark,
    metric_bundle,
    validate_benchmark_against_database,
    validate_corpus_boundaries,
)
from app.search.corpus_domains import (
    FULL_TEXT_EVIDENCE_DOMAIN,
    METADATA_CATALOG_DOMAIN,
)


def test_retrieval_benchmark_has_two_separate_domains(metadata_layer_ready):
    cases = load_benchmark()
    domains = {case["domain"] for case in cases}

    assert domains == {METADATA_CATALOG_DOMAIN, FULL_TEXT_EVIDENCE_DOMAIN}
    validation = validate_benchmark_against_database(cases)
    assert validation["metadata_judgment_count"] > 0
    assert validation["record_judgment_count"] > 0
    assert validation["unit_judgment_count"] > 0


def test_metric_bundle_calculates_recall_mrr_and_ndcg():
    metrics = metric_bundle(
        ["doc-b", "doc-a", "doc-x"],
        {"doc-a": 3, "doc-b": 1, "doc-c": 2},
        cutoffs=(1, 3),
    )

    assert metrics["recall@1"] == 0.333333
    assert metrics["recall@3"] == 0.666667
    assert metrics["mrr@3"] == 1.0
    assert 0 < metrics["ndcg@3"] < 1


def test_metadata_cannot_enter_full_text_or_rag_corpus(metadata_layer_ready):
    boundaries = validate_corpus_boundaries()

    assert boundaries["metadata_catalog"]["record_count"] == 50064
    assert boundaries["metadata_catalog"]["rag_evidence_allowed"] is False
    assert boundaries["full_text_evidence"]["record_count"] == 213
    assert boundaries["full_text_evidence"]["retrieval_unit_count"] == 1959
    assert boundaries["metadata_units_in_full_text_corpus"] == 0
    assert boundaries["unlinked_metadata_in_rag_corpus"] == 0
    assert boundaries["orphan_retrieval_units"] == 0


def test_hash_evaluation_is_reported_as_test_only(metadata_layer_ready, tmp_path):
    report = evaluate_retrieval(
        output_path=tmp_path / "retrieval_report.json",
        build_hash_test_index=True,
        top_k=10,
    )

    assert report["hash_test_index_used"] is True
    assert report["benchmark_domain_counts"] == {
        METADATA_CATALOG_DOMAIN: 7,
        FULL_TEXT_EVIDENCE_DOMAIN: 7,
    }
    assert len(report["benchmark_sha256"]) == 64
    assert report["semantic_runtime_status"]["semantic_quality"] == "test_hash"
    assert report["semantic_runtime_status"]["production_semantic_eligible"] is False
    assert report["improvement"]["production_semantic_accepted"] is False
    assert any(
        summary["method"] == "metadata_fts5_bm25"
        for summary in report["summaries"]
    )
    assert any(
        summary["method"] == "keyword"
        and summary["target_level"] == "retrieval_unit"
        for summary in report["summaries"]
    )
