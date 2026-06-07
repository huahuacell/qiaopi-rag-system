from app.database.schema import initialize_database
from app.ingestion.excel_loader import load_excel_if_exists
from app.settings import METADATA_XLSX_PATH, TEXT_XLSX_PATH


def build_database_from_excel() -> dict:
    initialize_database()
    metadata = load_excel_if_exists(METADATA_XLSX_PATH)
    texts = load_excel_if_exists(TEXT_XLSX_PATH)
    return {
        "status": "placeholder",
        "metadata_loaded": metadata is not None,
        "texts_loaded": texts is not None,
        "message": "SQLite build placeholder completed without requiring Excel files.",
    }

