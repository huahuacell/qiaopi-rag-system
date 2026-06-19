import os
from pathlib import Path

from dotenv import dotenv_values


BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BASE_DIR.parent
PROJECT_ENV_PATH = PROJECT_ROOT / ".env"
BACKEND_ENV_PATH = BASE_DIR / ".env"


def _load_env_file_values(
    *,
    backend_dir: Path = BASE_DIR,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, str]:
    values: dict[str, str] = {}
    for env_path in (project_root / ".env", backend_dir / ".env"):
        if not env_path.exists():
            continue
        for key, value in dotenv_values(env_path).items():
            if value is not None:
                values[key] = value
    return values


_ENV_FILE_VALUES = _load_env_file_values()


def _env(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    if value is not None:
        return value
    return _ENV_FILE_VALUES.get(name, default)


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

def _path_from_env(value: str | None, default: Path) -> Path:
    if value is None or not value.strip():
        return default
    path = Path(value.strip())
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def _bool_from_env(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    normalized_value = value.strip().lower()
    if normalized_value in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized_value in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _int_from_env(value: str | None, default: int) -> int:
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError:
        return default


QWEN_API_KEY = _env("QWEN_API_KEY") or _env("DASHSCOPE_API_KEY")
QWEN_BASE_URL = _env("QWEN_BASE_URL")
QWEN_MODEL = _env("QWEN_MODEL", "qwen-plus")
QWEN_TIMEOUT_SECONDS = _int_from_env(_env("QWEN_TIMEOUT_SECONDS"), 60)
QWEN_ENABLED = _bool_from_env(_env("QWEN_ENABLED"), False)

SEMANTIC_SEARCH_ENABLED = _bool_from_env(_env("SEMANTIC_SEARCH_ENABLED"), False)
EMBEDDING_PROVIDER = _env("EMBEDDING_PROVIDER", "local")
EMBEDDING_MODEL = _env("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
EMBEDDING_DIM = _int_from_env(_env("EMBEDDING_DIM"), 0)
EMBEDDING_BATCH_SIZE = _int_from_env(_env("EMBEDDING_BATCH_SIZE"), 32)
SEMANTIC_FAISS_INDEX_DIR = _path_from_env(
    _env("FAISS_INDEX_DIR"),
    INDEX_DIR,
)
SEMANTIC_FAISS_INDEX_PATH = _path_from_env(
    _env("FAISS_INDEX_PATH"),
    INDEX_DIR / "qiaopi_retrieval_units.faiss",
)
SEMANTIC_FAISS_METADATA_PATH = _path_from_env(
    _env("FAISS_METADATA_PATH"),
    INDEX_DIR / "qiaopi_retrieval_units_meta.jsonl",
)
SEMANTIC_FAISS_MANIFEST_PATH = _path_from_env(
    _env("FAISS_MANIFEST_PATH"),
    INDEX_DIR / "qiaopi_retrieval_units_manifest.json",
)
QWEN_EMBEDDING_API_KEY = _env("QWEN_EMBEDDING_API_KEY") or QWEN_API_KEY
QWEN_EMBEDDING_BASE_URL = _env("QWEN_EMBEDDING_BASE_URL")
QWEN_EMBEDDING_MODEL = _env("QWEN_EMBEDDING_MODEL")


def qwen_config_status() -> dict[str, object]:
    api_key_configured = bool(QWEN_API_KEY)
    base_url_configured = bool(QWEN_BASE_URL)
    return {
        "enabled": QWEN_ENABLED,
        "api_key_configured": api_key_configured,
        "base_url_configured": base_url_configured,
        "model": QWEN_MODEL,
        "timeout_seconds": QWEN_TIMEOUT_SECONDS,
        "project_env_exists": PROJECT_ENV_PATH.exists(),
        "backend_env_exists": BACKEND_ENV_PATH.exists(),
        "live_generation_ready": QWEN_ENABLED and api_key_configured and base_url_configured,
    }
