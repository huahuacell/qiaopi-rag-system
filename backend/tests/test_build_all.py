from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app import settings
from app.database.connection import get_connection
from app.database.schema import create_tables
from app.ingestion.build_all import (
    BuildAllError,
    _prepare_build_paths,
    compare_acceptance_manifests,
    promote_artifacts,
    relational_signature,
)
from app.ingestion.build_database import build_database


def _file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_staging_directory_cannot_be_inside_live_asset_directories(tmp_path):
    with pytest.raises(BuildAllError):
        _prepare_build_paths(settings.PROCESSED_DATA_DIR / "unsafe-build")

    non_empty = tmp_path / "non-empty"
    non_empty.mkdir()
    (non_empty / "keep.txt").write_text("do not delete", encoding="utf-8")
    with pytest.raises(BuildAllError):
        _prepare_build_paths(non_empty)
    assert (non_empty / "keep.txt").read_text(encoding="utf-8") == "do not delete"


def test_build_database_can_target_staging_without_touching_live_database(tmp_path):
    live_existed_before = settings.QIAOPI_DB_PATH.exists()
    live_before = (
        _file_sha256(settings.QIAOPI_DB_PATH)
        if live_existed_before
        else None
    )
    staged_database = tmp_path / "qiaopi.db"

    stats = build_database(
        staged_database,
        processed_dir=settings.PROCESSED_DATA_DIR,
    )

    assert stats["text_record_count"] == 213
    assert staged_database.exists()
    assert settings.QIAOPI_DB_PATH.exists() is live_existed_before
    if live_before is not None:
        assert _file_sha256(settings.QIAOPI_DB_PATH) == live_before


def test_relational_signature_ignores_created_at_but_detects_data_changes(tmp_path):
    first_path = tmp_path / "first.db"
    second_path = tmp_path / "second.db"
    for path, created_at in (
        (first_path, "2026-01-01 00:00:00"),
        (second_path, "2026-06-19 12:34:56"),
    ):
        with get_connection(path) as connection:
            create_tables(connection)
            connection.execute(
                """
                INSERT INTO qiaopi_generation_cache (
                    cache_id,
                    task_type,
                    input_hash,
                    record_id,
                    result_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "cache-1",
                    "interpret",
                    "input-hash",
                    "record-1",
                    json.dumps({"value": 1}, sort_keys=True),
                    created_at,
                ),
            )

    first = relational_signature(first_path)
    second = relational_signature(second_path)
    assert first["combined_sha256"] == second["combined_sha256"]
    assert first["schema_sha256"] == second["schema_sha256"]

    with get_connection(second_path) as connection:
        connection.execute(
            "UPDATE qiaopi_generation_cache SET result_json = ? WHERE cache_id = ?",
            (json.dumps({"value": 2}, sort_keys=True), "cache-1"),
        )
    changed = relational_signature(second_path)
    assert changed["combined_sha256"] != first["combined_sha256"]


def test_manifest_comparison_uses_vector_identity_and_ranked_ids_not_bytes_or_scores():
    baseline = {
        "relational": {
            "combined_sha256": "relational",
            "schema_sha256": "schema",
        },
        "vector": {
            "embedding_provider": "hash",
            "embedding_model": "hash-sha256-char-v1",
            "embedding_dimension": 64,
            "corpus_fingerprint": "corpus",
            "vector_count": 2,
            "retrieval_regression": [
                {
                    "query": "母亲 寄款",
                    "hits": [
                        {"unit_id": "unit-1", "score": 0.91},
                        {"unit_id": "unit-2", "score": 0.82},
                    ],
                }
            ],
            "byte_checksum_enforced": False,
        },
    }
    current = json.loads(json.dumps(baseline))
    current["vector"]["retrieval_regression"][0]["hits"][0]["score"] = 0.900001
    current["vector"]["index_file_sha256"] = "different-hardware-bytes"

    assert compare_acceptance_manifests(current, baseline)["matches"] is True

    current["vector"]["retrieval_regression"][0]["hits"][0]["unit_id"] = "unit-x"
    comparison = compare_acceptance_manifests(current, baseline)
    assert comparison["matches"] is False
    assert "vector.retrieval_regression_unit_ids" in comparison["differences"]


def test_promotion_rolls_back_all_targets_when_one_replace_fails(tmp_path, monkeypatch):
    source_one = tmp_path / "source-one.txt"
    source_two = tmp_path / "source-two.txt"
    target_one = tmp_path / "target-one.txt"
    target_two = tmp_path / "target-two.txt"
    source_one.write_text("new-one", encoding="utf-8")
    source_two.write_text("new-two", encoding="utf-8")
    target_one.write_text("old-one", encoding="utf-8")
    target_two.write_text("old-two", encoding="utf-8")

    real_replace = os.replace
    failed = False

    def fail_second_promotion(source, target):
        nonlocal failed
        source_path = Path(source)
        target_path = Path(target)
        if (
            not failed
            and source_path.name.endswith(".new")
            and target_path == target_two
        ):
            failed = True
            raise OSError("simulated promotion failure")
        return real_replace(source, target)

    monkeypatch.setattr("app.ingestion.build_all.os.replace", fail_second_promotion)

    with pytest.raises(OSError, match="simulated promotion failure"):
        promote_artifacts(
            [
                (source_one, target_one),
                (source_two, target_two),
            ]
        )

    assert target_one.read_text(encoding="utf-8") == "old-one"
    assert target_two.read_text(encoding="utf-8") == "old-two"


def test_promotion_verifies_and_replaces_all_target_bytes(tmp_path):
    source_one = tmp_path / "source-one.txt"
    source_two = tmp_path / "source-two.txt"
    target_one = tmp_path / "target-one.txt"
    target_two = tmp_path / "target-two.txt"
    source_one.write_text("accepted-one", encoding="utf-8")
    source_two.write_text("accepted-two", encoding="utf-8")
    target_one.write_text("old-one", encoding="utf-8")

    promoted = promote_artifacts(
        [
            (source_one, target_one),
            (source_two, target_two),
        ]
    )

    assert promoted == [str(target_one), str(target_two)]
    assert target_one.read_bytes() == source_one.read_bytes()
    assert target_two.read_bytes() == source_two.read_bytes()
