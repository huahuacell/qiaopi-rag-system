from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any


TRADITIONAL_DISPLAY_NOTE = (
    "Traditional Chinese month/day normalized for display; not converted to exact "
    "Gregorian calendar date."
)
MISSING_YEAR_NOTE = "Missing year; month/day retained without date_standard."
UNKNOWN_DATE_NOTE = "Date is unknown or cannot be parsed safely."
MISSING_DAY_NOTE = "Day missing; not defaulted."

UNKNOWN_MARKERS = ("不详", "未详", "不明", "未知", "无日期", "日期不详")
VALID_PRECISIONS = {"day", "month", "year", "month_day_no_year", "unknown"}
VALID_CALENDARS = {"gregorian", "roc", "traditional_lunar_text", "unknown"}

CHINESE_DIGITS: dict[str, int] = {
    "零": 0,
    "〇": 0,
    "○": 0,
    "一": 1,
    "壹": 1,
    "二": 2,
    "贰": 2,
    "貳": 2,
    "弍": 2,
    "两": 2,
    "三": 3,
    "叁": 3,
    "參": 3,
    "四": 4,
    "肆": 4,
    "五": 5,
    "伍": 5,
    "六": 6,
    "陆": 6,
    "陸": 6,
    "七": 7,
    "柒": 7,
    "八": 8,
    "捌": 8,
    "九": 9,
    "玖": 9,
}
CHINESE_TENS = {"十": 10, "拾": 10, "廿": 20, "念": 20, "卄": 20, "卅": 30}
MONTH_ALIASES: dict[str, int] = {
    "正": 1,
    "正月": 1,
    "元": 1,
    "元月": 1,
    "冬": 11,
    "冬月": 11,
    "腊": 12,
    "腊月": 12,
    "臘": 12,
    "臘月": 12,
    "阳": 10,
    "阳月": 10,
    "陽": 10,
    "陽月": 10,
}

_YEAR_RE = re.compile(r"(?<!\d)((?:18|19|20)\d{2})(?!\d)")
_PAREN_YEAR_RE = re.compile(r"[\(（]((?:18|19|20)\d{2})[\)）]")
_ROC_RE = re.compile(
    r"(?:中华|中華)?民[国國]\s*"
    r"(?P<year>[零〇○一二三四五六七八九十拾廿念卄卅壹贰貳叁參肆伍陆陸柒捌玖两弍\d]+)"
    r"\s*年"
)
_CHINESE_YEAR_RE = re.compile(r"([零〇○一二三四五六七八九]{4})年")
_NUMERIC_DATE_RE = re.compile(
    r"(?<!\d)(?P<year>(?:18|19|20)\d{2})\s*[年./-]\s*"
    r"(?P<month>0?[1-9]|1[0-2])"
    r"(?:\s*(?:月|[./-])\s*(?P<day>[12]\d|3[01]|0?[1-9])\s*(?:日|号|號)?)?"
)
_MONTH_TOKEN = (
    r"1[0-2]|0?[1-9]|"
    r"正|元|冬|腊|臘|阳|陽|"
    r"[零〇○一二三四五六七八九十拾壹贰貳叁參肆伍陆陸柒捌玖两弍]{1,3}"
)
_DAY_TOKEN = (
    r"[12]\d|3[01]|0?[1-9]|"
    r"初[一二三四五六七八九十拾壹贰貳叁參肆伍陆陸柒捌玖两弍]{1,2}|"
    r"[一二三四五六七八九壹贰貳叁參肆伍陆陸柒捌玖两弍]?[十拾]"
    r"[一二三四五六七八九壹贰貳叁參肆伍陆陸柒捌玖两弍]?|"
    r"[廿念卄][一二三四五六七八九壹贰貳叁參肆伍陆陸柒捌玖两弍]?|"
    r"卅|三十|"
    r"[一二三四五六七八九壹贰貳叁參肆伍陆陸柒捌玖两弍]{1,3}"
)
_MONTH_DAY_RE = re.compile(
    rf"(?P<month>{_MONTH_TOKEN})月"
    rf"(?:[\(（][^\)）月]*月[\)）])?"
    rf"(?P<day>{_DAY_TOKEN})?"
    rf"(?:日|号|號)?"
)


@dataclass(frozen=True)
class DateNormalizationResult:
    date_standard: str
    date_year: int | None
    date_month: int | None
    date_day: int | None
    date_precision: str
    date_calendar: str
    date_parse_confidence: float
    date_parse_note: str

    def as_db_fields(self) -> dict[str, Any]:
        return asdict(self)


def normalize_qiaopi_date(
    raw_date_text: Any,
    *,
    context_text: Any = "",
    year_hint: Any = "",
) -> DateNormalizationResult:
    raw_text = _clean_text(raw_date_text)
    context = _clean_text(context_text)
    combined = " ".join(part for part in (raw_text, context) if part)

    if _is_unknown_date(raw_text, context):
        return _unknown(UNKNOWN_DATE_NOTE)

    numeric_date = _extract_numeric_date(raw_text) or _extract_numeric_date(context)
    if numeric_date:
        year, month, day = numeric_date
        return _build_result(
            year=year,
            month=month,
            day=day,
            calendar="gregorian",
            confidence=1.0 if day else 0.60,
            note="" if day else MISSING_DAY_NOTE,
        )

    year, year_source = _extract_year(combined)
    if year is None:
        year = _valid_year(_parse_int_like(year_hint))
        if year is not None:
            year_source = "hint"

    month_day_source = raw_text or context
    month, day, month_token, day_token = _extract_month_day(month_day_source)
    if month is None and context:
        month, day, month_token, day_token = _extract_month_day(context)

    calendar = _calendar_for(
        raw_text=raw_text,
        context=context,
        year_source=year_source,
        month_token=month_token,
        day_token=day_token,
    )
    confidence = _confidence_for(
        year=year,
        month=month,
        day=day,
        calendar=calendar,
        year_source=year_source,
    )
    note = _note_for(year=year, month=month, day=day, calendar=calendar)
    return _build_result(
        year=year,
        month=month,
        day=day,
        calendar=calendar,
        confidence=confidence,
        note=note,
    )


def _build_result(
    *,
    year: int | None,
    month: int | None,
    day: int | None,
    calendar: str,
    confidence: float,
    note: str,
) -> DateNormalizationResult:
    year = _valid_year(year)
    month = month if month is not None and 1 <= month <= 12 else None
    day = day if day is not None and 1 <= day <= 31 else None
    calendar = calendar if calendar in VALID_CALENDARS else "unknown"

    if year and month and day:
        precision = "day"
        standard = f"{year}.{month}.{day}"
    elif year and month:
        precision = "month"
        standard = f"{year}.{month}"
    elif year:
        precision = "year"
        standard = str(year)
    elif month and day:
        precision = "month_day_no_year"
        standard = ""
    else:
        precision = "unknown"
        standard = ""
        calendar = "unknown" if calendar != "traditional_lunar_text" else calendar
        confidence = 0.0
        note = note or UNKNOWN_DATE_NOTE

    if precision not in VALID_PRECISIONS:
        precision = "unknown"
    return DateNormalizationResult(
        date_standard=standard,
        date_year=year,
        date_month=month,
        date_day=day,
        date_precision=precision,
        date_calendar=calendar,
        date_parse_confidence=round(confidence, 4),
        date_parse_note=note,
    )


def _unknown(note: str = UNKNOWN_DATE_NOTE) -> DateNormalizationResult:
    return DateNormalizationResult(
        date_standard="",
        date_year=None,
        date_month=None,
        date_day=None,
        date_precision="unknown",
        date_calendar="unknown",
        date_parse_confidence=0.0,
        date_parse_note=note,
    )


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value != value:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = text.replace("【", "[").replace("】", "]")
    text = text.replace("〔", "[").replace("〕", "]")
    text = re.sub(r"\[([^\[\]]{1,8})\]", r"\1", text)
    text = re.sub(r"\s+", "", text.strip())
    return text


def _is_unknown_date(raw_text: str, context: str) -> bool:
    text = raw_text or context
    if not text:
        return True
    return any(marker in text for marker in UNKNOWN_MARKERS)


def _extract_numeric_date(text: str) -> tuple[int, int | None, int | None] | None:
    if not text:
        return None
    match = _NUMERIC_DATE_RE.search(text)
    if not match:
        return None
    year = _valid_year(int(match.group("year")))
    if year is None:
        return None
    month = int(match.group("month"))
    day = int(match.group("day")) if match.group("day") else None
    return year, month, day


def _extract_year(text: str) -> tuple[int | None, str]:
    if not text:
        return None, ""
    roc_match = _ROC_RE.search(text)
    if roc_match:
        roc_year = _parse_chinese_number(roc_match.group("year"))
        year = _valid_year(1911 + roc_year if roc_year is not None else None)
        if year is not None:
            return year, "roc"

    parenthetical_year = _PAREN_YEAR_RE.search(text)
    if parenthetical_year:
        year = _valid_year(int(parenthetical_year.group(1)))
        if year is not None:
            return year, "parenthetical_western"

    western_year = _YEAR_RE.search(text)
    if western_year:
        year = _valid_year(int(western_year.group(1)))
        if year is not None:
            return year, "western"

    chinese_year = _CHINESE_YEAR_RE.search(text)
    if chinese_year:
        year = _valid_year(_parse_chinese_number(chinese_year.group(1)))
        if year is not None:
            return year, "western_chinese_digits"

    return None, ""


def _extract_month_day(text: str) -> tuple[int | None, int | None, str, str]:
    if not text:
        return None, None, "", ""
    for match in _MONTH_DAY_RE.finditer(text):
        month_token = match.group("month") or ""
        day_token = match.group("day") or ""
        month = _parse_month(month_token)
        day = _parse_day(day_token) if day_token else None
        if month is None:
            continue
        if day is not None and not 1 <= day <= 31:
            day = None
        return month, day, month_token, day_token
    return None, None, "", ""


def _parse_month(token: str) -> int | None:
    token = token.strip()
    if not token:
        return None
    if token in MONTH_ALIASES:
        return MONTH_ALIASES[token]
    if f"{token}月" in MONTH_ALIASES:
        return MONTH_ALIASES[f"{token}月"]
    value = _parse_chinese_number(token)
    if value is None:
        return None
    return value if 1 <= value <= 12 else None


def _parse_day(token: str) -> int | None:
    token = token.strip()
    if not token:
        return None
    token = token.removeprefix("初")
    return _parse_chinese_number(token)


def _parse_chinese_number(value: str) -> int | None:
    text = value.strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    if all(char in CHINESE_DIGITS for char in text):
        digits = "".join(str(CHINESE_DIGITS[char]) for char in text)
        return int(digits) if digits else None
    if len(text) == 1 and text in CHINESE_TENS:
        return CHINESE_TENS[text]
    if text[0] in CHINESE_TENS:
        suffix = CHINESE_DIGITS.get(text[1], 0) if len(text) > 1 else 0
        return CHINESE_TENS[text[0]] + suffix
    for ten_char in ("十", "拾"):
        if ten_char in text:
            prefix, suffix = text.split(ten_char, 1)
            tens = CHINESE_DIGITS.get(prefix, 1) * 10 if prefix else 10
            ones = CHINESE_DIGITS.get(suffix, 0) if suffix else 0
            return tens + ones
    return None


def _parse_int_like(value: Any) -> int | None:
    text = _clean_text(value)
    if not text:
        return None
    if text.isdigit():
        return int(text)
    return _parse_chinese_number(text)


def _valid_year(value: int | None) -> int | None:
    if value is None:
        return None
    return value if 1800 <= value <= 2100 else None


def _calendar_for(
    *,
    raw_text: str,
    context: str,
    year_source: str,
    month_token: str,
    day_token: str,
) -> str:
    combined = f"{raw_text}{context}"
    if year_source == "roc":
        return "roc"
    if _is_traditional_month_day(combined, month_token, day_token):
        return "traditional_lunar_text"
    if year_source in {"western", "western_chinese_digits", "parenthetical_western", "hint"}:
        return "gregorian"
    return "unknown"


def _is_traditional_month_day(text: str, month_token: str, day_token: str) -> bool:
    if any(marker in text for marker in ("夏历", "夏曆", "农历", "農曆", "旧历", "舊曆")):
        return True
    if any(marker in text for marker in ("正月", "元月", "冬月", "腊月", "臘月", "阳月", "陽月")):
        return True
    if re.search(r"[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]?", text):
        return True
    if month_token and not month_token.isdigit():
        return True
    if day_token and not day_token.isdigit():
        return True
    return False


def _confidence_for(
    *,
    year: int | None,
    month: int | None,
    day: int | None,
    calendar: str,
    year_source: str,
) -> float:
    if year is None and month and day:
        return 0.30
    if calendar == "roc" and year:
        return 0.95
    if calendar == "traditional_lunar_text" and year and month and day:
        if year_source == "parenthetical_western":
            return 0.85
        return 0.75
    if year and month and day:
        return 1.0
    if year and month:
        return 0.60
    if year:
        return 0.60
    return 0.0


def _note_for(
    *,
    year: int | None,
    month: int | None,
    day: int | None,
    calendar: str,
) -> str:
    notes: list[str] = []
    if year is None and month and day:
        notes.append(MISSING_YEAR_NOTE)
    elif year and month and day is None:
        notes.append(MISSING_DAY_NOTE)
    if calendar == "traditional_lunar_text" and year and month:
        notes.append(TRADITIONAL_DISPLAY_NOTE)
    return " ".join(notes)
