import json
import shutil

import pytest

from app.database.connection import get_connection
from app.graph.readiness import (
    DataBuildNotReadyError,
    inspect_data_build,
    require_data_build,
)
from app.graph.graph_builder import build_knowledge_graph
from app.ingestion.build_metadata_database import build_metadata_database
from app.ingestion.link_metadata_text_records import link_metadata_text_records
from app import settings


def _write_manifest(path, db_path):
    with get_connection(db_path) as connection:
        counts = {
            table_name: int(
                connection.execute(
                    f"SELECT COUNT(*) FROM {table_name}"
                ).fetchone()[0]
            )
            for table_name in (
                "qiaopi_text_records",
                "qiaopi_metadata_records",
                "qiaopi_text_metadata_links",
                "qiaopi_text_metadata_link_candidates",
                "qiaopi_amount_mentions",
                "qiaopi_entity_mentions",
                "qiaopi_place_mentions",
                "qiaopi_evidence_spans",
                "qiaopi_retrieval_units",
                "qiaopi_retrieval_units_fts",
                "qiaopi_metadata_fts",
                "qiaopi_kg_nodes",
                "qiaopi_kg_edges",
            )
        }
    path.write_text(
        json.dumps(
            {
                "manifest_version": "1",
                "pipeline": "qiaopi-build-all",
                "status": "accepted",
                "database_acceptance": {"counts": counts},
            }
        ),
        encoding="utf-8",
    )


@pytest.fixture(scope="module")
def accepted_database(rebuild_sqlite_database, tmp_path_factory):
    db_path = rebuild_sqlite_database
    build_metadata_database(
        source_path=settings.METADATA_XLSX_PATH,
        db_path=db_path,
    )
    link_metadata_text_records(db_path)
    build_knowledge_graph(db_path)
    manifest_path = (
        tmp_path_factory.mktemp("qiaopi-accepted-manifest")
        / "qiaopi_build_manifest.json"
    )
    _write_manifest(manifest_path, db_path)
    return db_path, manifest_path


def test_readiness_accepts_a_complete_promoted_build(accepted_database):
    db_path, manifest_path = accepted_database

    status = require_data_build(
        db_path,
        manifest_path,
        validate_semantic=False,
    )

    assert status["ready"] is True
    assert status["source_record_count"] == 213
    assert status["metadata_record_count"] == 50_064
    assert status["graph_record_count"] == 213
    assert status["graph_edge_count"] > 0


def test_readiness_does_not_create_a_missing_database(tmp_path):
    db_path = tmp_path / "missing.db"

    status = inspect_data_build(
        db_path,
        tmp_path / "missing-manifest.json",
        validate_semantic=False,
    )

    assert status["ready"] is False
    assert status["reason"] == "database_missing"
    assert not db_path.exists()


def test_readiness_rejects_incomplete_graph_without_repairing(
    accepted_database,
    tmp_path,
):
    accepted_db_path, accepted_manifest_path = accepted_database
    db_path = tmp_path / "qiaopi.db"
    manifest_path = tmp_path / "qiaopi_build_manifest.json"
    shutil.copy2(accepted_db_path, db_path)
    shutil.copy2(accepted_manifest_path, manifest_path)
    with get_connection(db_path) as connection:
        connection.execute("DELETE FROM qiaopi_kg_edges")
        connection.execute("DELETE FROM qiaopi_kg_nodes")

    with pytest.raises(DataBuildNotReadyError, match="build_all"):
        require_data_build(
            db_path,
            manifest_path,
            validate_semantic=False,
        )

    with get_connection(db_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM qiaopi_kg_nodes"
        ).fetchone()[0] == 0
