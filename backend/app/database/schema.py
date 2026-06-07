from app.database.connection import get_connection


CREATE_RECORDS_TABLE = """
CREATE TABLE IF NOT EXISTS qiaopi_records (
    record_id TEXT PRIMARY KEY,
    origin_place TEXT,
    destination_place TEXT,
    date TEXT,
    sender TEXT,
    recipient TEXT,
    kinship TEXT,
    money TEXT,
    original_text TEXT,
    normalized_text TEXT
);
"""


def initialize_database() -> None:
    with get_connection() as connection:
        connection.execute(CREATE_RECORDS_TABLE)

