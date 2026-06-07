from typing import Optional

from app.database.connection import get_connection


def get_record_by_id(record_id: str) -> Optional[dict]:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM qiaopi_records WHERE record_id = ?",
            (record_id,),
        ).fetchone()
    return dict(row) if row else None

