from __future__ import annotations

import re
import unicodedata
from typing import Any


_PUNCTUATION_RE = re.compile(r"[\s\u3000,，.。;；:：、!！?？\"'`“”‘’（）()\[\]【】{}<>《》/\\|]+")
_SEPARATOR_RE = re.compile(r"[;；,，、\n\r\t]+")
_AMOUNT_RE = re.compile(r"[\s\u3000,，.。;；:：、!！?？\"'`“”‘’（）()\[\]【】{}<>《》/\\|]+")

PLACE_ALIASES: dict[str, str] = {
    "叻": "新加坡",
    "叻埠": "新加坡",
    "石叻": "新加坡",
    "星洲": "新加坡",
    "暹罗": "泰国",
    "安南": "越南",
}


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\u3000", " ")
    return unicodedata.normalize("NFKC", text).strip()


def split_multi_value(value: Any) -> list[str]:
    text = clean_text(value)
    if not text:
        return []
    return [part.strip() for part in _SEPARATOR_RE.split(text) if part.strip()]


def normalize_person_label(label: Any) -> str:
    text = clean_text(label)
    if not text:
        return ""
    return _PUNCTUATION_RE.sub("", text)


def normalize_place_label(label: Any) -> str:
    text = clean_text(label)
    if not text:
        return ""
    compact = _PUNCTUATION_RE.sub("", text)
    return PLACE_ALIASES.get(compact, compact)


def normalize_theme_label(label: Any) -> str:
    text = clean_text(label)
    if not text:
        return ""
    compact = re.sub(r"[\s\u3000]+", "", text)
    if compact.isascii():
        return compact.lower()
    return compact


def normalize_date_label(label: Any) -> str:
    text = clean_text(label)
    if not text:
        return ""
    return re.sub(r"[\s\u3000]+", "", text)


def normalize_amount_raw(label: Any) -> str:
    text = clean_text(label)
    if not text:
        return ""
    return _AMOUNT_RE.sub("", text)


def normalize_amount_number(value: Any) -> str:
    text = clean_text(value)
    if not text:
        return ""
    try:
        number = float(text)
    except ValueError:
        return text
    if number.is_integer():
        return str(int(number))
    return f"{number:.6f}".rstrip("0").rstrip(".")


def is_uncertain_date(label: Any) -> bool:
    text = clean_text(label)
    if not text:
        return True
    return any(marker in text for marker in ("不详", "未详", "约", "?", "？", "[", "]", "〔", "〕"))
