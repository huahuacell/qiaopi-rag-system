import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.settings import QIAOPI_DB_PATH


def resolve_database_path(db_path: Path | str | None = None) -> Path:
    return Path(db_path) if db_path is not None else Path(QIAOPI_DB_PATH)


@contextmanager
def get_connection(db_path: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    resolved_path = resolve_database_path(db_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(resolved_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


@contextmanager
def get_readonly_connection(
    db_path: Path | str | None = None,
) -> Iterator[sqlite3.Connection]:
    resolved_path = resolve_database_path(db_path).resolve()
    if not resolved_path.is_file():
        raise FileNotFoundError(f"SQLite database is missing: {resolved_path}")
    connection = sqlite3.connect(
        f"{resolved_path.as_uri()}?mode=ro",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    finally:
        connection.close()
