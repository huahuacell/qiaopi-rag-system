import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.settings import QIAOPI_DB_PATH


@contextmanager
def get_connection(db_path: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    resolved_path = Path(db_path) if db_path is not None else QIAOPI_DB_PATH
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(resolved_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()
