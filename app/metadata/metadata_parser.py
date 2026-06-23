from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from app import settings


COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "source_eid": ("EID", "eid", "identifier", "编号"),
    "title_raw": ("DCTITLE", "title", "题名", "标题"),
    "sender_raw": ("DCCREATOR", "creator", "寄批人", "寄件人", "sender"),
    "recipient_raw": ("DCCONTRIBUTOR", "contributor", "收批人", "收件人", "recipient"),
    "date_text": ("DCDATE", "date", "日期", "时间"),
    "description": ("DCDESCRIPTION", "description", "描述", "说明"),
    "subject": ("DCSUBJECT", "subject", "主题"),
    "publisher": ("DCPUBLISHER", "publisher", "信局", "发行者"),
    "coverage": ("DCCOVERAGE", "coverage", "范围", "地点"),
}

KNOWN_PLACES: tuple[str, ...] = (
    "新加坡",
    "新嘉坡",
    "叻坡",
    "星洲",
    "石叻",
    "马来西亚",
    "槟城",
    "怡保",
    "霹雳",
    "吉隆坡",
    "古晋",
    "沙捞越",
    "泰国",
    "暹",
    "曼谷",
    "越南",
    "安南",
    "印尼",
    "爪哇",
    "泗水",
    "缅甸",
    "仰光",
    "菲律宾",
    "马尼拉",
    "香港",
    "澳门",
    "美国",
    "加拿大",
    "澳洲",
    "广东",
    "潮安",
    "潮州",
    "汕头",
    "澄海",
    "揭阳",
    "普宁",
    "潮汕",
    "海阳",
    "潮邑",
    "澄邑",
)

COUNTRY_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("新加坡", ("新加坡", "新嘉坡", "叻坡", "星洲", "石叻")),
    ("马来西亚", ("马来西亚", "槟城", "怡保", "霹雳", "吉隆坡")),
    ("沙捞越", ("沙捞越", "古晋")),
    ("泰国", ("泰国", "暹", "曼谷")),
    ("越南", ("越南", "安南")),
    ("印度尼西亚", ("印尼", "爪哇", "泗水")),
    ("缅甸", ("缅甸", "仰光")),
    ("菲律宾", ("菲律宾", "马尼拉")),
    ("中国香港", ("香港",)),
    ("中国澳门", ("澳门",)),
    ("美国", ("美国",)),
    ("加拿大", ("加拿大",)),
    ("澳大利亚", ("澳洲", "澳大利亚")),
    ("广东侨乡", ("广东", "潮安", "潮州", "汕头", "澄海", "揭阳", "普宁", "潮汕")),
)

KINSHIP_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("母亲", ("母亲", "慈亲", "家慈", "慈母", "萱堂", "阿母", "阿妈")),
    ("父亲", ("父亲", "严亲", "家严", "严父", "父亲大人")),
    ("父母", ("双亲", "严慈", "父母")),
    ("妻子", ("妻", "吾妻", "我妻", "荆妻", "内妻", "贤妻")),
    ("丈夫", ("夫", "丈夫")),
    ("儿子", ("儿", "吾儿", "我儿", "男", "犬子")),
    ("女儿", ("女", "吾女", "我女")),
    ("兄弟", ("兄", "弟", "胞兄", "胞弟", "姻兄")),
    ("姐妹", ("姐", "妹", "姊", "胞妹")),
    ("叔伯", ("叔", "伯", "叔父", "伯父")),
    ("嫂", ("嫂", "大嫂")),
)

CHINESE_DIGITS = {
    "零": 0,
    "〇": 0,
    "○": 0,
    "一": 1,
    "壹": 1,
    "二": 2,
    "贰": 2,
    "两": 2,
    "三": 3,
    "叁": 3,
    "四": 4,
    "肆": 4,
    "五": 5,
    "伍": 5,
    "六": 6,
    "陆": 6,
    "七": 7,
    "柒": 7,
    "八": 8,
    "捌": 8,
    "九": 9,
    "玖": 9,
}

CHINESE_TENS = {"十": 10, "拾": 10, "廿": 20, "念": 20, "卅": 30}


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value != value:
        return ""
    return re.sub(r"\s+", "", str(value).strip())


def _readable_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value != value:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def _normalized_columns(columns: list[str]) -> dict[str, str]:
    return {re.sub(r"[\s_]+", "", column).lower(): column for column in columns}


def _field(row: Mapping[str, Any], columns: Mapping[str, str], field_name: str) -> str:
    for alias in COLUMN_ALIASES[field_name]:
        key = re.sub(r"[\s_]+", "", alias).lower()
        if key in columns:
            return _readable_text(row.get(columns[key], ""))
    return ""


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        clean_value = _clean_text(value)
        if clean_value and clean_value not in seen:
            seen.add(clean_value)
            result.append(clean_value)
    return result


def normalize_title(title: str) -> str:
    clean_title = _clean_text(title)
    clean_title = re.sub(r"[［\[\(（].*?[］\]\)）]", "", clean_title)
    clean_title = clean_title.replace("〓", "")
    return clean_title


def normalize_name(name: str) -> str:
    clean_name = normalize_title(name)
    clean_name = re.sub(
        r"(转交|收交|吾儿|我儿|吾妻|我妻|家慈亲|家慈|慈亲|严亲|双亲|大人|少爷|姻兄|胞弟|胞兄|儿|女|妻|母亲|父亲)$",
        "",
        clean_name,
    )
    return clean_name or normalize_title(name)


def _country_for_place(place: str) -> str:
    for country, aliases in COUNTRY_ALIASES:
        if any(alias and alias in place for alias in aliases):
            return country
    return ""


def _extract_origin_place(title_clean: str, sender_raw: str, coverage: str) -> str:
    if coverage:
        return coverage
    sender_name = normalize_name(sender_raw)
    if sender_name and sender_name in title_clean:
        prefix = title_clean.split(sender_name, 1)[0]
        if prefix:
            return prefix
    for place in KNOWN_PLACES:
        if title_clean.startswith(place):
            return place
    for place in KNOWN_PLACES:
        if place in title_clean:
            return place
    return ""


def _extract_destination_place(title_clean: str, recipient_raw: str) -> str:
    recipient_name = normalize_name(recipient_raw)
    if "寄" not in title_clean:
        return ""
    after_send = title_clean.split("寄", 1)[1].replace("侨批", "")
    if recipient_name and recipient_name in after_send:
        return after_send.split(recipient_name, 1)[0]
    for place in KNOWN_PLACES:
        if place in after_send:
            return after_send.split(place, 1)[0] + place
    return ""


def _extract_place_mentions(*texts: str) -> list[str]:
    values: list[str] = []
    haystack = "；".join(texts)
    for place in KNOWN_PLACES:
        if place in haystack:
            values.append(place)
    return _dedupe(values)


def _parse_chinese_number(value: str) -> int | None:
    text = _clean_text(value)
    if not text:
        return None
    if text.isdigit():
        return int(text)
    if all(char in CHINESE_DIGITS for char in text):
        digits = "".join(str(CHINESE_DIGITS[char]) for char in text)
        return int(digits) if digits else None
    if text[0] in CHINESE_TENS and len(text) == 1:
        return CHINESE_TENS[text[0]]
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


def _extract_year(date_text: str, title_raw: str) -> tuple[str, str]:
    combined = f"{date_text} {title_raw}"
    era_text = ""
    bracket_match = re.search(r"[［\[]?([^［\[\]］]*(?:民国|同治|光绪|宣统|民國)[^［\[\]］]*)[］\]]?", combined)
    if bracket_match:
        era_text = _readable_text(bracket_match.group(1))

    def valid_year(value: int | None) -> str:
        if value is None:
            return ""
        return str(value) if 1800 <= value <= 2100 else ""

    four_digit = re.search(r"(?<!\d)(18|19|20)\d{2}(?!\d)", combined)
    if four_digit:
        return four_digit.group(0), era_text

    minguo = re.search(r"民[国國]([零〇○一二三四五六七八九十拾廿念卅壹贰叁肆伍陆柒捌玖两\d]+)年", combined)
    if minguo:
        value = _parse_chinese_number(minguo.group(1))
        year = valid_year(1911 + value if value else None)
        if year:
            return year, era_text or f"民国{minguo.group(1)}年"

    chinese_year = re.search(r"([一二三四五六七八九零〇○]{4})年", combined)
    if chinese_year:
        value = _parse_chinese_number(chinese_year.group(1))
        year = valid_year(value)
        if year:
            return year, era_text

    short_year = re.search(r"(?<!\d)([1-9]\d)年", combined)
    if short_year:
        return str(1900 + int(short_year.group(1))), era_text

    return "", era_text


def _extract_remittance(text: str) -> tuple[str, float | None, str, int]:
    pattern = re.compile(
        r"(?P<currency>洋银|大洋银|大洋|英洋|荷银|大银|银元|银|港币|国币|币)?"
        r"(?P<amount>[零〇○一二三四五六七八九十拾百佰千仟壹贰叁肆伍陆柒捌玖两廿念卅\d]+)"
        r"(?P<unit>元|圆|員|员)"
    )
    match = pattern.search(text)
    if not match:
        return "", None, "", 0
    amount = _parse_chinese_number(match.group("amount"))
    currency = match.group("currency") or match.group("unit")
    return match.group(0), float(amount) if amount is not None else None, currency, 1


def _extract_kinship_terms(*texts: str) -> list[str]:
    haystack = "；".join(texts)
    terms: list[str] = []
    for normalized, aliases in KINSHIP_ALIASES:
        if any(alias in haystack for alias in aliases):
            terms.append(normalized)
    return _dedupe(terms)


def _relationship_type(kinship_terms: list[str]) -> str:
    values = set(kinship_terms)
    if values & {"母亲", "父亲", "父母"}:
        return "child_to_parent"
    if values & {"妻子", "丈夫"}:
        return "spouse"
    if values & {"儿子", "女儿"}:
        return "parent_to_child"
    if values & {"兄弟", "姐妹", "叔伯", "嫂"}:
        return "extended_family"
    return ""


def _theme_tags(has_remittance: int, kinship_terms: list[str], place_mentions: list[str]) -> str:
    tags = ["theme_archive_catalog"]
    if has_remittance:
        tags.append("theme_remittance")
    if kinship_terms:
        tags.append("theme_family_affection")
    if place_mentions:
        tags.append("theme_place")
    return "；".join(tags)


def parse_metadata_dataframe(df: pd.DataFrame) -> list[dict[str, Any]]:
    columns = _normalized_columns(list(df.columns))
    records: list[dict[str, Any]] = []
    for index, raw_row in enumerate(df.to_dict("records"), start=1):
        row = {str(key): _readable_text(value) for key, value in raw_row.items()}
        title_raw = _field(row, columns, "title_raw")
        sender_raw = _field(row, columns, "sender_raw")
        recipient_raw = _field(row, columns, "recipient_raw")
        date_text = _field(row, columns, "date_text")
        description = _field(row, columns, "description")
        subject = _field(row, columns, "subject")
        coverage = _field(row, columns, "coverage")
        title_clean = normalize_title(title_raw)
        sender_name_clean = normalize_name(sender_raw)
        recipient_name_clean = normalize_name(recipient_raw)
        year_normalized, era_text = _extract_year(date_text, title_raw)
        origin_place = _extract_origin_place(title_clean, sender_raw, coverage)
        destination_place = _extract_destination_place(title_clean, recipient_raw)
        place_mentions = _extract_place_mentions(title_clean, origin_place, destination_place, coverage)
        country_or_region = _country_for_place(origin_place) or _country_for_place("；".join(place_mentions))
        remittance_raw, amount_number, currency, has_remittance = _extract_remittance(
            "；".join([title_raw, description, subject])
        )
        kinship_terms = _extract_kinship_terms(title_raw, recipient_raw)
        relationship_type = _relationship_type(kinship_terms)
        theme_tags = _theme_tags(has_remittance, kinship_terms, place_mentions)
        main_intent = "remittance" if has_remittance else "archive_catalog"

        warnings: list[str] = []
        if not title_raw:
            warnings.append("missing_title")
        if not sender_raw:
            warnings.append("missing_sender")
        if not recipient_raw:
            warnings.append("missing_recipient")
        if not year_normalized:
            warnings.append("year_unparsed")
        if not origin_place and not destination_place:
            warnings.append("place_unparsed")

        confidence = 0.45
        confidence += 0.15 if title_raw else 0.0
        confidence += 0.10 if sender_raw else 0.0
        confidence += 0.10 if recipient_raw else 0.0
        confidence += 0.10 if year_normalized else 0.0
        confidence += 0.08 if origin_place or destination_place else 0.0
        confidence += 0.02 if kinship_terms else 0.0
        confidence = min(confidence, 0.99)

        records.append(
            {
                "metadata_id": f"CSQP-META-{index:06d}",
                "source_index": index,
                "title_raw": title_raw,
                "title_clean": title_clean,
                "sender_raw": sender_raw,
                "recipient_raw": recipient_raw,
                "sender_name_clean": sender_name_clean,
                "recipient_name_clean": recipient_name_clean,
                "date_text": date_text,
                "year_normalized": year_normalized,
                "era_text": era_text,
                "origin_place": origin_place,
                "destination_place": destination_place,
                "place_mentions": "；".join(place_mentions),
                "country_or_region": country_or_region,
                "remittance_raw": remittance_raw,
                "amount_number": amount_number,
                "currency": currency,
                "has_remittance": has_remittance,
                "kinship_terms": "；".join(kinship_terms),
                "relationship_type": relationship_type,
                "theme_tags": theme_tags,
                "main_intent": main_intent,
                "has_linked_text": 0,
                "linked_record_id": "",
                "parse_confidence": round(confidence, 4),
                "needs_review": 1 if confidence < 0.75 or warnings else 0,
                "warnings": "；".join(warnings),
                "raw_json": json.dumps(row, ensure_ascii=False, sort_keys=True),
            }
        )
    return records


def resolve_metadata_excel_path(path: Path | None = None) -> Path:
    candidates = [
        path,
        settings.METADATA_XLSX_PATH,
        settings.PROJECT_ROOT / "raw" / "qiaopi_50064_metadata.xlsx",
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    expected = " or ".join(str(candidate) for candidate in candidates if candidate)
    raise FileNotFoundError(f"Metadata Excel file is missing. Expected {expected}.")


def read_metadata_excel(path: Path | None = None) -> pd.DataFrame:
    resolved_path = resolve_metadata_excel_path(path)
    return pd.read_excel(resolved_path, dtype=str, keep_default_na=False).fillna("")


def parse_metadata_excel(path: Path | None = None) -> list[dict[str, Any]]:
    return parse_metadata_dataframe(read_metadata_excel(path))
