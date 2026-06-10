import pytest

from app.ingestion.build_database import build_database


@pytest.fixture(scope="session", autouse=True)
def rebuild_sqlite_database():
    build_database()
