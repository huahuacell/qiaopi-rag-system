import pytest
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.ingestion.build_database import build_database
from app.ingestion.build_metadata_database import build_metadata_database
from app.ingestion.link_metadata_text_records import link_metadata_text_records


def pytest_configure(config):
    """Ensure a user-supplied nested --basetemp has an existing parent."""
    base_temp = config.getoption("basetemp")
    if base_temp:
        Path(base_temp).expanduser().resolve().parent.mkdir(
            parents=True,
            exist_ok=True,
        )


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
