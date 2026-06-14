import pytest

from app.ingestion.build_database import build_database
from app.ingestion.build_metadata_database import build_metadata_database
from app.ingestion.link_metadata_text_records import link_metadata_text_records


@pytest.fixture(scope="session", autouse=True)
def rebuild_sqlite_database():
    build_database()


@pytest.fixture(scope="session")
def metadata_layer_ready():
    metadata_stats = build_metadata_database()
    link_stats = link_metadata_text_records()
    return {
        "metadata_stats": metadata_stats,
        "link_stats": link_stats,
    }
