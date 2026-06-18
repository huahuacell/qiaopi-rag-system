import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BASE_DIR.parent

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
INDEX_DIR = DATA_DIR / "index"
OUTPUT_DIR = BASE_DIR / "outputs"

DB_PATH = Path(
    os.getenv("QIAOPI_DB_PATH", str(PROCESSED_DATA_DIR / "qiaopi.db"))
).resolve()
METADATA_XLSX_PATH = RAW_DATA_DIR / "qiaopi_50064_metadata.xlsx"
TEXT_XLSX_PATH = RAW_DATA_DIR / "qiaopi_213_text.xlsx"
FAISS_INDEX_PATH = INDEX_DIR / "qiaopi.faiss"
FAISS_METADATA_PATH = INDEX_DIR / "qiaopi_faiss_metadata.json"
GENERATED_RESULTS_PATH = OUTPUT_DIR / "generated_results.json"

QWEN_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
