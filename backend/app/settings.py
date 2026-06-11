import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
INDEX_DIR = DATA_DIR / "index"
OUTPUT_DIR = BASE_DIR / "outputs"

QIAOPI_DB_PATH = PROCESSED_DATA_DIR / "qiaopi.db"
DB_PATH = QIAOPI_DB_PATH

METADATA_XLSX_PATH = RAW_DATA_DIR / "qiaopi_50064_metadata.xlsx"
TEXT_XLSX_PATH = RAW_DATA_DIR / "qiaopi_213_text.xlsx"

QIAOPI_WIDE_TABLE_CSV = PROCESSED_DATA_DIR / "qiaopi_213_wide_table.csv"
QIAOPI_WIDE_TABLE_XLSX = PROCESSED_DATA_DIR / "qiaopi_213_wide_table.xlsx"
QIAOPI_AMOUNT_MENTIONS_CSV = PROCESSED_DATA_DIR / "qiaopi_amount_mentions.csv"
QIAOPI_ENTITY_MENTIONS_CSV = PROCESSED_DATA_DIR / "qiaopi_entity_mentions.csv"
QIAOPI_PLACE_MENTIONS_CSV = PROCESSED_DATA_DIR / "qiaopi_place_mentions.csv"
QIAOPI_EVIDENCE_SPANS_CSV = PROCESSED_DATA_DIR / "qiaopi_evidence_spans.csv"

FAISS_INDEX_PATH = INDEX_DIR / "qiaopi.faiss"
FAISS_METADATA_PATH = INDEX_DIR / "qiaopi_faiss_metadata.json"
GENERATED_RESULTS_PATH = OUTPUT_DIR / "generated_results.json"

QWEN_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
