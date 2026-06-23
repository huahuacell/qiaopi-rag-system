from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Iterable, Mapping

from app.database.repository import fetch_retrieval_units
from app.search.hybrid_retriever import retrieve_hybrid
from app.search.keyword_retriever import retrieve_keyword
from app.search.query_expansion import expand_query, terms_for_expansion_mode
from app.search.result_aggregator import group_results_by_record
from app.search.semantic_retriever import semantic_search
from app.validation.fact_extractor import infer_recipient_relationship


RAG_UNIT_TYPES: tuple[str, ...] = (
    "body_core",
    "remittance",
    "family_care",
    "instruction",
    "rag_summary",
)

RECORD_CONTEXT_UNIT_TYPES: tuple[str, ...] = (
    "body_core",
    "remittance",
    "family_care",
    "instruction",
    "safety",
    "opening",
    "closing",
    "rag_summary",
    "style_reference",
    "record_full",
)

STYLE_SLOT_TYPES: tuple[str, ...] = (
    "opening",
    "safety",
    "remittance",
    "family_care",
    "instruction",
    "closing",
    "style_reference",
)

STYLE_SLOT_LABELS: dict[str, str] = {
    "opening": "开头称谓样例",
    "safety": "报平安样例",
    "remittance": "寄款表达样例",
    "family_care": "问候保重样例",
    "instruction": "嘱托表达样例",
    "closing": "结尾署名样例",
    "style_reference": "综合风格参考",
}

CONTEXT_HINT_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("母亲", "妈妈", "阿母", "阿妈", "阿嬷", "祖母"), ("母亲",)),
    (("父亲", "爸爸", "阿爸", "双亲", "父母"), ("父亲",)),
    (("平安", "安好", "无恙", "勿念", "毋念"), ("平安",)),
    (("寄款", "汇款", "寄", "钱", "元", "银", "款"), ("寄款",)),
    (("查收", "收讫", "收用", "检收"), ("查收",)),
    (("读书", "学习", "勤奋", "勤学", "学业"), ("读书",)),
    (("保重", "身体", "安康", "调养"), ("保重",)),
    (("新加坡", "星洲", "叻坡", "石叻"), ("新加坡",)),
)

STYLE_HINT_RULES: tuple[tuple[tuple[str, ...], str, tuple[str, ...]], ...] = (
    (("母亲", "妈妈", "阿母", "阿妈", "阿嬷"), "opening", ("慈亲", "母亲", "大人", "膝下")),
    (
        ("平安", "安好", "无恙", "勿念", "毋念", "放心", "住处", "生意", "顺手"),
        "safety",
        ("平安", "安好", "无恙", "勿念", "两地平安"),
    ),
    (
        ("寄", "钱", "元", "汇款", "寄款", "银", "捎回", "带回", "寄回", "家用"),
        "remittance",
        ("寄款", "汇款", "批款", "查收", "付去", "家用"),
    ),
    (
        ("读书", "学习", "勤奋", "勤学"),
        "instruction",
        ("读书", "勤学", "学业", "务望"),
    ),
    (
        ("回信", "回音", "记得", "帮忙", "照应", "商量", "办理"),
        "instruction",
        ("祈复", "示复", "照应", "办理", "务望"),
    ),
    (
        ("保重", "身体", "安康", "调养", "操劳", "过劳", "劳累", "太累", "休息"),
        "family_care",
        ("保重", "珍摄", "切勿过劳", "调养"),
    ),
)

STYLE_SLOT_FALLBACK_TERMS: dict[str, tuple[str, ...]] = {
    "opening": ("收知", "如晤", "敬启"),
    "safety": ("平安", "安好", "无恙"),
    "remittance": ("寄款", "批款", "查收"),
    "family_care": ("保重", "珍摄", "切勿过劳"),
    "instruction": ("务望", "祈知", "示复"),
    "closing": ("谨上", "叩上", "敬上"),
    "style_reference": ("侨批", "风格", "慈亲", "平安", "寄款"),
}

RELATIONSHIP_STYLE_TERMS: dict[str, dict[str, tuple[str, ...]]] = {
    "mother": {
        "opening": ("慈亲", "母亲", "大人", "膝下"),
        "closing": ("儿", "谨禀", "叩上"),
    },
    "father": {
        "opening": ("严亲", "父亲", "大人", "膝下"),
        "closing": ("儿", "谨禀", "叩上"),
    },
    "wife": {
        "opening": ("妻子", "吾妻", "贤妻", "荆妻", "收知", "如晤"),
        "closing": ("夫", "敬上", "泐", "缄"),
    },
    "husband": {
        "opening": ("夫君", "丈夫", "如晤"),
        "closing": ("妻", "敬上", "泐", "缄"),
    },
    "sibling": {
        "opening": ("兄弟", "姊妹", "如晤"),
        "closing": ("弟", "兄", "敬上"),
    },
}

STYLE_SLOT_TRIGGER_TERMS: dict[str, tuple[str, ...]] = {
    "safety": ("平安", "安好", "无恙", "健康", "身体", "勿念", "放心", "生意", "顺利"),
    "remittance": ("寄回", "寄钱", "汇款", "寄款", "款项", "查收", "元", "银", "钱"),
    "family_care": ("保重", "照顾", "操劳", "过劳", "调养", "珍重", "身体", "家中"),
    "instruction": (
        "请",
        "务必",
        "不要",
        "不可",
        "切勿",
        "记得",
        "商量",
        "照看",
        "读书",
        "学习",
        "练习",
        "办理",
    ),
}

STYLE_SLOT_MARKERS: dict[str, tuple[str, ...]] = {
    "opening": ("尊前", "膝下", "如晤", "福安", "展信", "大人"),
    "safety": ("平安", "安好", "无恙", "康健", "勿念", "毋念", "顺遂"),
    "remittance": ("寄", "汇", "奉上", "带去", "付去", "查收", "收讫", "银", "元"),
    "family_care": ("保重", "珍摄", "调养", "身体", "安康", "操劳"),
    "instruction": ("务望", "切勿", "不可", "应当", "读书", "勤学", "办理", "照看"),
    "closing": (
        "敬上",
        "谨上",
        "谨启",
        "谨禀",
        "叩上",
        "泐",
        "缄",
        "顿",
        "字",
        "草",
        "手书",
        "珍重",
    ),
    "style_reference": (),
}

STYLE_SLOT_CONTAMINATION_TERMS: dict[str, tuple[str, ...]] = {
    "opening": ("奉上", "带去", "查收", "收讫", "务望", "切勿"),
    "safety": ("奉上", "带去", "查收", "收讫", "务望", "切勿"),
    "remittance": ("读书", "勤学", "保重", "珍摄", "调养"),
    "family_care": ("奉上", "带去", "查收", "收讫"),
    "instruction": ("奉上", "带去", "查收", "收讫"),
    "closing": ("奉上", "带去", "查收", "收讫", "读书", "勤学"),
    "style_reference": (),
}

STYLE_SLOT_CONCEPT_GROUPS: dict[str, tuple[tuple[str, ...], ...]] = {
    "opening": (
        ("母亲", "妈妈", "阿母", "阿妈", "慈亲", "家母"),
        ("父亲", "爸爸", "严亲", "家父"),
        ("妻子", "妻", "夫人", "贤内"),
        ("弟弟", "妹妹", "兄长", "姐姐", "兄弟", "姊妹"),
        ("儿子", "女儿", "孩子"),
    ),
    "safety": (
        ("身体", "健康", "安康", "无恙", "平安"),
        ("生意", "营生", "工作", "码头"),
        ("家中", "家人", "合家"),
        ("行船", "旅途", "路上"),
    ),
    "remittance": (
        ("药", "看病", "医治"),
        ("学费", "读书", "学习"),
        ("家用", "米", "粮", "生活"),
        ("还债", "欠款", "借款"),
    ),
    "family_care": (
        ("身体", "健康", "安康", "调养"),
        ("操劳", "劳累", "过劳", "太累", "休息", "工作", "家务", "独力", "主持"),
        ("家中", "家人", "父母", "孩子"),
    ),
    "instruction": (
        ("读书", "学习", "勤学", "学业", "学校", "用功"),
        ("回信", "来信", "写信"),
        ("田地", "物业", "房产", "买卖"),
        ("照看", "照顾", "办理", "商量"),
        ("借款", "还款", "欠债", "开销"),
    ),
    "closing": (),
    "style_reference": (),
}

STYLE_SLOT_LENGTH_LIMITS: dict[str, tuple[int, int]] = {
    "opening": (2, 32),
    "safety": (10, 72),
    "remittance": (10, 88),
    "family_care": (10, 72),
    "instruction": (10, 72),
    "closing": (2, 48),
    "style_reference": (10, 120),
}

STYLE_SLOT_PREFERRED_MAX: dict[str, int] = {
    "opening": 20,
    "safety": 32,
    "remittance": 60,
    "family_care": 40,
    "instruction": 48,
    "closing": 24,
    "style_reference": 90,
}

STYLE_PROMPT_CHARACTER_BUDGET = 900

RECORD_CONTEXT_PRIORITY: dict[str, float] = {
    "body_core": 2.0,
    "remittance": 1.9,
    "family_care": 1.7,
    "instruction": 1.7,
    "safety": 1.5,
    "rag_summary": 1.4,
    "opening": 1.2,
    "closing": 1.1,
    "style_reference": 0.9,
    "record_full": 0.8,
}

WHITESPACE_PATTERN = re.compile(r"\s+")
STYLE_SEGMENT_PATTERN = re.compile(r"[^。！？；\n]+[。！？；]?")
STYLE_BAD_SEPARATOR_PATTERN = re.compile(r"([。！？])\s*[；;]+")
STYLE_REPEATED_SEPARATOR_PATTERN = re.compile(r"[；;]{2,}")
STYLE_AMOUNT_PATTERN = re.compile(
    r"(?:国币|中央币|港币|大洋|洋银|银)?"
    r"[零〇一二三四五六七八九十百千万壹贰弍叁肆伍陆柒捌玖拾佰仟萬\d]+元"
)
STYLE_DATE_PATTERN = re.compile(
    r"(?:民国)?[一二三四五六七八九十廿卅\d]{1,4}年"
    r"[一二三四五六七八九十廿卅\d]{1,3}月"
    r"[初十廿卅一二三四五六七八九\d]{1,4}日?"
)
STYLE_SPECIFIC_ROLE_TERMS = (
    "孙",
    "侄",
    "婿",
    "岳父",
    "岳母",
    "祖母",
    "父亲",
    "母亲",
    "妻",
    "夫",
    "兄",
    "弟",
    "大妗",
    "细姨",
    "合家老少",
)


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _normalize_unit_text(text: str) -> str:
    return WHITESPACE_PATTERN.sub("", text)


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    deduped_values: list[str] = []
    for value in values:
        clean_value = value.strip()
        if not clean_value or clean_value in seen:
            continue
        seen.add(clean_value)
        deduped_values.append(clean_value)
    return deduped_values


def _detected_context_terms(query: str) -> list[str]:
    terms: list[str] = []
    for triggers, hints in CONTEXT_HINT_RULES:
        if any(trigger in query for trigger in triggers):
            terms.extend(hints)
    return _dedupe(terms)


def _query_with_context_hints(query: str) -> str:
    terms = _detected_context_terms(query)
    return " ".join(_dedupe([query, *terms]))


def _style_hints_for_slot(query: str, slot_type: str) -> list[str]:
    terms: list[str] = []
    for triggers, target_slot, hints in STYLE_HINT_RULES:
        if target_slot == slot_type and any(trigger in query for trigger in triggers):
            terms.extend(hints)
    return _dedupe(terms)


def _style_base_query(query: str) -> str:
    terms = _detected_context_terms(query)
    for triggers, _slot_type, hints in STYLE_HINT_RULES:
        if any(trigger in query for trigger in triggers):
            terms.extend(hints)
    return " ".join(_dedupe([query, *terms]))


def _style_query_for_slot(query: str, slot_type: str) -> str:
    relationship = infer_recipient_relationship(query)
    terms = [
        query,
        *_detected_context_terms(query),
        *_style_hints_for_slot(query, slot_type),
        *RELATIONSHIP_STYLE_TERMS.get(relationship["key"], {}).get(slot_type, ()),
        *STYLE_SLOT_FALLBACK_TERMS.get(slot_type, ()),
    ]
    return " ".join(_dedupe(terms))


def _style_focus_query(query: str, slot_type: str) -> str:
    relationship = infer_recipient_relationship(query)
    focus_text = _slot_focus_text(query, slot_type)
    concept_query = focus_text or query
    matched_concepts = [
        term
        for concept_group in STYLE_SLOT_CONCEPT_GROUPS.get(slot_type, ())
        if any(term in concept_query for term in concept_group)
        for term in concept_group
    ]
    terms = [
        focus_text,
        *_style_hints_for_slot(query, slot_type),
        *matched_concepts,
        *RELATIONSHIP_STYLE_TERMS.get(relationship["key"], {}).get(slot_type, ()),
        *STYLE_SLOT_FALLBACK_TERMS.get(slot_type, ()),
    ]
    return " ".join(_dedupe(terms))


def _slot_focus_text(query: str, slot_type: str) -> str:
    if slot_type in {"opening", "closing", "style_reference"}:
        return ""
    spans = [
        span.strip()
        for span in re.split(r"[。！？!?；;\n]+", query)
        if span.strip()
    ]
    triggers = STYLE_SLOT_TRIGGER_TERMS.get(slot_type, ())
    selected = [
        span
        for span in spans
        if any(trigger in span for trigger in triggers)
    ]
    return " ".join(selected[:3])


def _merge_style_candidate_rows(
    primary_rows: list[dict[str, Any]],
    focused_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    combined: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for source_name, rows in (
        ("context", primary_rows),
        ("slot_focus", focused_rows),
    ):
        for row in rows:
            unit_id = _text(row.get("unit_id"))
            if not unit_id:
                continue
            if unit_id not in combined:
                combined[unit_id] = dict(row)
                combined[unit_id]["style_query_sources"] = []
                order.append(unit_id)
            target = combined[unit_id]
            if source_name not in target["style_query_sources"]:
                target["style_query_sources"].append(source_name)
            retrieval_sources = list(target.get("retrieval_sources") or [])
            incoming_sources = list(row.get("retrieval_sources") or ["keyword"])
            target["retrieval_sources"] = _dedupe(
                [*retrieval_sources, *incoming_sources]
            )
            target["semantic_score"] = max(
                _float(target.get("semantic_score")),
                _float(row.get("semantic_score")),
            )
            target["final_score"] = max(
                _float(target.get("final_score")),
                _float(row.get("final_score")),
            )
            incoming_reason = _text(row.get("matched_reason"))
            existing_reason = _text(target.get("matched_reason"))
            if incoming_reason and incoming_reason not in existing_reason:
                target["matched_reason"] = (
                    f"{existing_reason}；{incoming_reason}"
                    if existing_reason
                    else incoming_reason
                )
    return [combined[unit_id] for unit_id in order]


def _relationship_compatibility(
    row: Mapping[str, Any],
    relationship: Mapping[str, Any],
    slot_type: str,
) -> tuple[str, float]:
    if slot_type not in {"opening", "closing"}:
        return "neutral", 0.5
    expected_types = set(relationship.get("relationship_types") or [])
    row_type = _text(row.get("relationship_type"))
    if not expected_types:
        return "neutral", 0.5
    if row_type in expected_types:
        return "matched", 1.0
    if not row_type or row_type == "unknown":
        return "neutral", 0.4
    return "mismatched", 0.0


def _relationship_expression_score(
    fragment: str,
    slot_type: str,
    relationship: Mapping[str, Any],
) -> float:
    relationship_key = _text(relationship.get("key"))
    if relationship_key == "unknown" or slot_type not in {"opening", "closing"}:
        return 0.5

    expression_terms: dict[str, dict[str, tuple[str, ...]]] = {
        "wife": {
            "opening": ("吾妻", "贤妻", "荆妻", "妻", "如晤", "收知"),
            "closing": ("夫", "泐", "顿", "字", "草", "手书", "启", "缄"),
        },
        "husband": {
            "opening": ("夫君", "丈夫", "如晤"),
            "closing": ("妻", "泐", "顿", "字", "草", "手书", "启", "缄"),
        },
        "mother": {
            "opening": ("慈亲", "母亲", "大人", "膝下"),
            "closing": ("儿", "男", "谨禀", "叩上", "泐"),
        },
        "father": {
            "opening": ("严亲", "父亲", "大人", "膝下"),
            "closing": ("儿", "男", "谨禀", "叩上", "泐"),
        },
    }
    terms = expression_terms.get(relationship_key, {}).get(slot_type, ())
    if not terms:
        return 0.5
    hits = sum(1 for term in terms if term in fragment)
    return min(1.0, 0.35 + (hits * 0.22))


def _active_style_slots(query: str) -> list[str]:
    active = ["opening"]
    for slot_type in ("safety", "remittance", "family_care", "instruction"):
        if any(term in query for term in STYLE_SLOT_TRIGGER_TERMS[slot_type]):
            active.append(slot_type)
    active.extend(["closing", "style_reference"])
    return active


def _clean_style_text(text: str) -> str:
    clean = WHITESPACE_PATTERN.sub(" ", text).strip()
    clean = STYLE_BAD_SEPARATOR_PATTERN.sub(r"\1", clean)
    clean = STYLE_REPEATED_SEPARATOR_PATTERN.sub("；", clean)
    return clean.strip("；; ")


def _style_segments(text: str) -> list[str]:
    return [
        segment.strip()
        for segment in STYLE_SEGMENT_PATTERN.findall(_clean_style_text(text))
        if segment.strip("；; ")
    ]


def _extract_style_fragment(text: str, slot_type: str) -> str:
    clean = _clean_style_text(text)
    if not clean:
        return ""
    minimum, maximum = STYLE_SLOT_LENGTH_LIMITS[slot_type]
    segments = _style_segments(clean)
    markers = STYLE_SLOT_MARKERS[slot_type]
    matching = [
        segment
        for segment in segments
        if not markers or any(marker in segment for marker in markers)
    ]

    if slot_type == "opening":
        candidates = matching or segments[:1]
    elif slot_type == "closing":
        candidates = list(reversed(matching or segments[-2:]))
    else:
        candidates = matching or segments

    selected: list[str] = []
    for segment in candidates:
        candidate = _clean_style_text(segment)
        if not candidate:
            continue
        if selected and len("".join(selected)) + len(candidate) > maximum:
            continue
        selected.append(candidate)
        if len("".join(selected)) >= minimum or slot_type in {"opening", "closing"}:
            break

    fragment = "".join(reversed(selected)) if slot_type == "closing" else "".join(selected)
    if not fragment:
        fragment = clean
    if len(fragment) > maximum:
        fragment = fragment[:maximum].rstrip("，、；; ") + "…"
    return fragment


def _style_prompt_text(fragment: str, slot_type: str) -> str:
    prompt_text = STYLE_AMOUNT_PATTERN.sub("【用户金额】", fragment)
    prompt_text = STYLE_DATE_PATTERN.sub("【用户日期】", prompt_text)
    if slot_type == "instruction":
        instruction_markers = ("但须", "务望", "切勿", "不可", "须当", "应当", "请")
        marker_positions = [
            prompt_text.find(marker)
            for marker in instruction_markers
            if marker in prompt_text
        ]
        if marker_positions:
            prompt_text = prompt_text[min(marker_positions) :]
    if slot_type == "closing":
        compact_closing = re.sub(r"\s+", "", prompt_text)
        closing_match = re.search(
            r"(敬上|谨上|谨启|谨禀|叩上|泐|缄|顿|字|草|手书)$",
            compact_closing,
        )
        if closing_match:
            marker = closing_match.group(1)
            relationship = next(
                (
                    role
                    for role in ("儿", "男", "女", "弟", "兄", "夫", "妻", "侄", "孙")
                    if role in compact_closing
                ),
                "",
            )
            prompt_text = f"{relationship}【署名】{marker}"
    return prompt_text


def _character_bigrams(text: str) -> set[str]:
    compact = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", text)
    return {compact[index : index + 2] for index in range(max(0, len(compact) - 1))}


def _style_lexical_score(query: str, fragment: str, slot_type: str) -> float:
    query_bigrams = _character_bigrams(query)
    fragment_bigrams = _character_bigrams(fragment)
    bigram_score = (
        len(query_bigrams & fragment_bigrams) / max(1, len(fragment_bigrams))
        if fragment_bigrams
        else 0.0
    )
    markers = STYLE_SLOT_MARKERS[slot_type]
    marker_score = (
        min(1.0, sum(1 for marker in markers if marker in fragment) / 2)
        if markers
        else 0.5
    )
    relevant_concepts = [
        concept_terms
        for concept_terms in STYLE_SLOT_CONCEPT_GROUPS[slot_type]
        if any(term in query for term in concept_terms)
    ]
    concept_score = (
        sum(
            1
            for concept_terms in relevant_concepts
            if any(term in fragment for term in concept_terms)
        )
        / len(relevant_concepts)
        if relevant_concepts
        else 0.5
    )
    return min(
        1.0,
        (bigram_score * 0.35) + (marker_score * 0.20) + (concept_score * 0.45),
    )


def _style_quality_scores(
    raw_text: str,
    fragment: str,
    slot_type: str,
    query: str,
) -> tuple[float, float]:
    minimum, maximum = STYLE_SLOT_LENGTH_LIMITS[slot_type]
    fragment_length = len(fragment)
    if minimum <= fragment_length <= maximum:
        length_score = 1.0
    elif fragment_length < minimum:
        length_score = max(0.25, fragment_length / max(1, minimum))
    else:
        length_score = max(0.0, 1 - ((fragment_length - maximum) / max(1, maximum)))
    preferred_max = STYLE_SLOT_PREFERRED_MAX[slot_type]
    if fragment_length > preferred_max:
        length_score -= min(
            0.45,
            ((fragment_length - preferred_max) / max(1, maximum)) * 0.9,
        )

    malformed_count = len(re.findall(r"[。！？][；;]|[；;]{2,}", raw_text))
    correction_count = len(re.findall(r"[（(][^）)]{1,6}[）)]", raw_text))
    segment_count = len(_style_segments(raw_text))
    role_mismatch_count = sum(
        1
        for term in STYLE_SPECIFIC_ROLE_TERMS
        if term in fragment and term not in query
    )
    question_mismatch = "？" in fragment and not any(
        marker in query for marker in ("？", "吗", "是否", "可否", "怎样", "如何")
    )
    contamination_count = sum(
        1
        for term in STYLE_SLOT_CONTAMINATION_TERMS[slot_type]
        if term in fragment
    )
    quality_score = max(
        0.0,
        min(
            1.0,
            length_score
            - (malformed_count * 0.18)
            - (correction_count * 0.06)
            - (max(0, segment_count - 3) * 0.08)
            - (min(3, role_mismatch_count) * 0.10)
            - (min(3, contamination_count) * 0.08)
            - (0.12 if question_mismatch else 0.0),
        ),
    )

    markers = STYLE_SLOT_MARKERS[slot_type]
    marker_hit = any(marker in fragment for marker in markers) if markers else True
    purity_score = 0.7 + (0.3 if marker_hit else 0.0)
    if segment_count > 3:
        purity_score -= min(0.35, (segment_count - 3) * 0.08)
    purity_score -= min(0.25, role_mismatch_count * 0.08)
    purity_score -= min(0.24, contamination_count * 0.08)
    return round(max(0.0, purity_score), 4), round(quality_score, 4)


def _rerank_style_rows(
    rows: list[dict[str, Any]],
    *,
    query: str,
    slot_type: str,
) -> list[dict[str, Any]]:
    reranked: list[dict[str, Any]] = []
    relationship = infer_recipient_relationship(query)
    scoring_query = (
        _style_focus_query(query, slot_type)
        if slot_type not in {"opening", "closing", "style_reference"}
        else _style_query_for_slot(query, slot_type)
    )
    for rank, row in enumerate(rows, start=1):
        raw_text = _text(row.get("unit_text"))
        fragment = _extract_style_fragment(raw_text, slot_type)
        if not fragment:
            continue
        lexical_score = _style_lexical_score(scoring_query, fragment, slot_type)
        purity_score, quality_score = _style_quality_scores(
            raw_text,
            fragment,
            slot_type,
            scoring_query,
        )
        semantic_score = max(0.0, min(1.0, _float(row.get("semantic_score"))))
        relationship_match, relationship_score = _relationship_compatibility(
            row,
            relationship,
            slot_type,
        )
        relationship_expression_score = _relationship_expression_score(
            fragment,
            slot_type,
            relationship,
        )
        rank_score = 1.0 / rank
        slot_score = (
            (rank_score * 0.10)
            + (semantic_score * 0.15)
            + (lexical_score * 0.25)
            + (purity_score * 0.13)
            + (quality_score * 0.12)
            + (relationship_score * 0.15)
            + (relationship_expression_score * 0.10)
        )
        if slot_type in {"opening", "closing"} and relationship_match == "mismatched":
            slot_score *= 0.35
        prepared = dict(row)
        prepared["raw_unit_text"] = raw_text
        prepared["unit_text"] = fragment
        prepared["prompt_text"] = _style_prompt_text(fragment, slot_type)
        prepared["slot_score"] = round(min(1.0, slot_score), 4)
        prepared["slot_purity_score"] = purity_score
        prepared["quality_score"] = quality_score
        prepared["relationship_profile"] = relationship["key"]
        prepared["relationship_label"] = relationship["label"]
        prepared["relationship_match"] = relationship_match
        prepared["relationship_score"] = relationship_score
        prepared["relationship_expression_score"] = relationship_expression_score
        prepared["prompt_included"] = False
        prepared["matched_reason"] = (
            f"{_text(row.get('matched_reason'))}；槽位纯度、片段质量与收信关系重排"
        ).strip("；")
        reranked.append(prepared)
    return sorted(
        reranked,
        key=lambda item: (
            -_float(item.get("slot_score")),
            -_float(item.get("quality_score")),
            -_float(item.get("semantic_score")),
            _text(item.get("unit_id")),
        ),
    )


def _matches_context_filters(row: Mapping[str, Any], filters: Mapping[str, Any]) -> bool:
    if not filters:
        return True
    for key, value in filters.items():
        if value in (None, "", []):
            continue
        row_value = _text(row.get(key))
        if key in {"unit_type", "evidence_type", "source_column", "main_intent"} and row_value != str(value):
            return False
        if key == "unit_types":
            values = {str(item) for item in value}
            if _text(row.get("unit_type")) not in values:
                return False
    return True


def _select_units(
    rows: list[dict[str, Any]],
    top_k: int,
    *,
    preferred_unit_types: Iterable[str] | None = None,
    max_per_record: int = 2,
) -> list[dict[str, Any]]:
    preferred_set = {unit_type for unit_type in (preferred_unit_types or []) if unit_type}
    preferred_rows = [row for row in rows if _text(row.get("unit_type")) in preferred_set]
    first_pass_rows = preferred_rows if preferred_rows else rows

    selected_rows: list[dict[str, Any]] = []
    seen_texts: set[str] = set()
    record_counts: dict[str, int] = defaultdict(int)

    def try_add(row: dict[str, Any], *, enforce_record_cap: bool) -> None:
        if len(selected_rows) >= top_k:
            return
        unit_text = _text(row.get("unit_text"))
        normalized_text = _normalize_unit_text(unit_text)
        if not normalized_text or normalized_text in seen_texts:
            return
        record_id = _text(row.get("record_id"))
        if enforce_record_cap and record_id and record_counts[record_id] >= max_per_record:
            return
        seen_texts.add(normalized_text)
        if record_id:
            record_counts[record_id] += 1
        selected_rows.append(row)

    for row in first_pass_rows:
        try_add(row, enforce_record_cap=True)
    for row in rows:
        try_add(row, enforce_record_cap=True)
    for row in first_pass_rows:
        try_add(row, enforce_record_cap=False)
    for row in rows:
        try_add(row, enforce_record_cap=False)

    return selected_rows


def _rag_context_item(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "record_id": _text(row.get("record_id")),
        "unit_id": _text(row.get("unit_id")),
        "unit_type": _text(row.get("unit_type")),
        "title_reference": _text(row.get("title_reference")),
        "sender": _text(row.get("sender")),
        "recipient": _text(row.get("recipient")),
        "date_text": _text(row.get("date_text")),
        "main_intent": _text(row.get("main_intent")),
        "unit_text": _text(row.get("unit_text")),
        "source_column": _text(row.get("source_column")),
        "evidence_type": _text(row.get("evidence_type")),
        "matched_reason": _text(row.get("matched_reason")),
        "final_score": _float(row.get("final_score")),
    }


def _style_slot_example(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "record_id": _text(row.get("record_id")),
        "unit_id": _text(row.get("unit_id")),
        "unit_type": _text(row.get("unit_type")),
        "title_reference": _text(row.get("title_reference")),
        "unit_text": _text(row.get("unit_text")),
        "prompt_text": _text(row.get("prompt_text")),
        "raw_unit_text": _text(row.get("raw_unit_text")),
        "source_column": _text(row.get("source_column")),
        "evidence_type": _text(row.get("evidence_type")),
        "matched_reason": _text(row.get("matched_reason")),
        "final_score": _float(row.get("final_score")),
        "semantic_score": _float(row.get("semantic_score")),
        "slot_score": _float(row.get("slot_score")),
        "slot_purity_score": _float(row.get("slot_purity_score")),
        "quality_score": _float(row.get("quality_score")),
        "relationship_type": _text(row.get("relationship_type")),
        "relationship_profile": _text(row.get("relationship_profile")),
        "relationship_label": _text(row.get("relationship_label")),
        "relationship_match": _text(row.get("relationship_match")) or "neutral",
        "relationship_score": _float(row.get("relationship_score")),
        "relationship_expression_score": _float(
            row.get("relationship_expression_score")
        ),
        "retrieval_sources": list(row.get("retrieval_sources") or []),
        "prompt_included": bool(row.get("prompt_included", False)),
    }


def _expanded_query(query: str, expansion_mode: str) -> tuple[str, str]:
    expansion = expand_query(query)
    mode = expansion_mode if expansion_mode in {"strict", "balanced", "broad"} else "balanced"
    return (
        expansion.normalized_query,
        " ".join(terms_for_expansion_mode(expansion, mode)),
    )


def _build_rag_prompt_context(query: str, contexts: list[dict[str, Any]]) -> str:
    parts = ["【检索问题】", query.strip()]
    if not contexts:
        parts.extend(["", "【相关侨批证据】", "暂无可用证据。"])
        return "\n".join(parts)

    for index, context in enumerate(contexts, start=1):
        parts.extend(
            [
                "",
                f"【相关侨批证据 {index}】",
                f"来源记录：{context['record_id']}",
                f"题名：{context['title_reference']}",
                f"寄批人：{context['sender']}",
                f"收批人：{context['recipient']}",
                f"日期：{context['date_text']}",
                f"证据类型：{context['evidence_type'] or context['unit_type']}",
                f"来源字段：{context['source_column']}",
                f"原文片段：{context['unit_text']}",
            ]
        )
    return "\n".join(parts)


def _record_context_rows(record_id: str, filters: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in fetch_retrieval_units(record_id):
        unit_type = _text(row.get("unit_type"))
        if unit_type not in RECORD_CONTEXT_UNIT_TYPES:
            continue
        if not _matches_context_filters(row, filters):
            continue
        prepared_row = dict(row)
        prepared_row["bm25_score"] = 0.0
        prepared_row["final_score"] = round(
            RECORD_CONTEXT_PRIORITY.get(unit_type, 1.0) * float(row.get("weight") or 1.0),
            8,
        )
        prepared_row["matched_reason"] = f"来自指定记录的{unit_type}检索单元"
        prepared_row["original_hit_count"] = 0
        prepared_row["strong_hit_count"] = 0
        prepared_row["medium_hit_count"] = 0
        prepared_row["weak_hit_count"] = 0
        rows.append(prepared_row)
    return sorted(
        rows,
        key=lambda item: (
            -float(item.get("final_score") or 0.0),
            _text(item.get("unit_id")),
        ),
    )


def _build_style_prompt_context(
    query: str,
    style_slots: Mapping[str, list[dict[str, Any]]],
    *,
    active_slots: Iterable[str],
    character_budget: int = STYLE_PROMPT_CHARACTER_BUDGET,
) -> tuple[str, int]:
    relationship = infer_recipient_relationship(query)
    parts = [
        "【事实来源（唯一）】",
        query.strip(),
        "",
        "【文体参考使用规则】",
        "以下知识库片段只用于借鉴称谓、句式和收束方式，不得复制其中的人物、金额、地点或事件。",
        "称谓和落款必须与本次收信关系一致；若落款样例含关系自称，可保留该自称，但署名只能使用用户输入中的姓名。",
    ]
    if relationship["key"] != "unknown":
        parts.extend(
            [
                "",
                "【本次收信关系】",
                f"{relationship['label']}（{relationship['reason']}）",
            ]
        )
    used_characters = sum(len(part) for part in parts)
    included_count = 0
    active_slot_list = list(active_slots)
    if any(
        slot_type in active_slot_list
        for slot_type in ("safety", "remittance", "family_care", "instruction")
    ):
        active_slot_list = [
            slot_type
            for slot_type in active_slot_list
            if slot_type != "style_reference"
        ]
    for slot_type in active_slot_list:
        examples = style_slots.get(slot_type, [])
        if not examples:
            continue
        example = examples[0]
        section = [
            "",
            f"【{STYLE_SLOT_LABELS[slot_type]}】",
            example.get("prompt_text") or example["unit_text"],
            f"来源：{example['record_id']} / {example['unit_id']}",
        ]
        section_length = sum(len(part) for part in section)
        if used_characters + section_length > character_budget:
            continue
        example["prompt_included"] = True
        parts.extend(section)
        used_characters += section_length
        included_count += 1
    if included_count == 0:
        parts.extend(["", "【文体参考】", "暂无达到质量要求的知识库样例。"])
    return "\n".join(parts), included_count


def build_rag_context(
    *,
    query: str,
    top_k: int,
    unit_types: list[str],
    filters: Mapping[str, Any],
    expansion_mode: str,
    retrieval_mode: str = "hybrid",
) -> dict[str, Any]:
    retrieval_query = _query_with_context_hints(query)
    requested_unit_types = [unit_type for unit_type in unit_types if unit_type] or list(RAG_UNIT_TYPES)
    mode = retrieval_mode if retrieval_mode in {"keyword", "semantic", "hybrid"} else "hybrid"
    retrieval_limit = max(20, top_k * 4)
    semantic_enabled = False
    semantic_quality = "disabled"
    if mode == "semantic":
        semantic_result = semantic_search(
            query=retrieval_query,
            top_k=retrieval_limit,
            unit_types=requested_unit_types,
            filters=filters,
        )
        if semantic_result.get("semantic_enabled") and semantic_result.get("results"):
            retrieval_result = {
                "results": semantic_result["results"],
                "expansion_mode": expansion_mode if expansion_mode in {"strict", "balanced", "broad"} else "balanced",
            }
            semantic_enabled = True
            semantic_quality = semantic_result.get(
                "semantic_quality",
                "disabled",
            )
        else:
            retrieval_result = retrieve_keyword(
                query=retrieval_query,
                top_k=retrieval_limit,
                unit_types=requested_unit_types,
                filters=filters,
                expansion_mode=expansion_mode,
            )
    elif mode == "hybrid":
        retrieval_result = retrieve_hybrid(
            query=retrieval_query,
            top_k=retrieval_limit,
            unit_types=requested_unit_types,
            filters=filters,
            expansion_mode=expansion_mode,
        )
        semantic_enabled = bool(retrieval_result.get("semantic_enabled", False))
        semantic_quality = retrieval_result.get(
            "semantic_quality",
            "disabled",
        )
    else:
        retrieval_result = retrieve_keyword(
            query=retrieval_query,
            top_k=retrieval_limit,
            unit_types=requested_unit_types,
            filters=filters,
            expansion_mode=expansion_mode,
        )
    selected_rows = _select_units(
        retrieval_result["results"],
        top_k,
        preferred_unit_types=RAG_UNIT_TYPES,
        max_per_record=2,
    )
    contexts = [_rag_context_item(row) for row in selected_rows]
    normalized_query, expanded_query = _expanded_query(retrieval_query, retrieval_result["expansion_mode"])
    source_record_ids = {context["record_id"] for context in contexts if context["record_id"]}
    return {
        "query": query,
        "normalized_query": normalized_query,
        "expanded_query": expanded_query,
        "expansion_mode": retrieval_result["expansion_mode"],
        "semantic_enabled": semantic_enabled,
        "semantic_quality": semantic_quality,
        "contexts": contexts,
        "grouped_contexts": group_results_by_record(selected_rows),
        "prompt_context": _build_rag_prompt_context(query, contexts),
        "evidence_count": len(contexts),
        "source_record_count": len(source_record_ids),
    }


def build_record_rag_context(
    *,
    query: str,
    record_id: str,
    top_k: int,
    filters: Mapping[str, Any],
    expansion_mode: str,
) -> dict[str, Any]:
    retrieval_query = _query_with_context_hints(query)
    rows = _record_context_rows(record_id, filters)
    selected_rows = _select_units(
        rows,
        top_k,
        preferred_unit_types=RAG_UNIT_TYPES,
        max_per_record=top_k,
    )
    contexts = [_rag_context_item(row) for row in selected_rows]
    normalized_query, expanded_query = _expanded_query(retrieval_query, expansion_mode)
    source_record_ids = {context["record_id"] for context in contexts if context["record_id"]}
    return {
        "query": query,
        "normalized_query": normalized_query,
        "expanded_query": expanded_query,
        "expansion_mode": expansion_mode if expansion_mode in {"strict", "balanced", "broad"} else "balanced",
        "semantic_enabled": False,
        "semantic_quality": "disabled",
        "contexts": contexts,
        "grouped_contexts": group_results_by_record(selected_rows),
        "prompt_context": _build_rag_prompt_context(query, contexts),
        "evidence_count": len(contexts),
        "source_record_count": len(source_record_ids),
    }


def build_style_context(
    *,
    query: str,
    top_k: int,
    filters: Mapping[str, Any],
    expansion_mode: str,
) -> dict[str, Any]:
    active_slots = _active_style_slots(query)
    style_slots: dict[str, list[dict[str, Any]]] = {
        slot_type: [] for slot_type in STYLE_SLOT_TYPES
    }
    selected_rows_by_slot: dict[str, list[dict[str, Any]]] = {}
    all_selected_rows: list[dict[str, Any]] = []
    semantic_enabled = False
    semantic_qualities: list[str] = []

    for slot_type in active_slots:
        retrieval_result = retrieve_hybrid(
            query=_style_query_for_slot(query, slot_type),
            top_k=max(20, top_k * 8),
            unit_types=[slot_type],
            filters=filters,
            expansion_mode=expansion_mode,
        )
        focus_query = _style_focus_query(query, slot_type)
        focused_result = (
            retrieve_keyword(
                query=focus_query,
                top_k=max(20, top_k * 8),
                unit_types=[slot_type],
                filters=filters,
                expansion_mode="strict",
            )
            if focus_query
            else {"results": []}
        )
        semantic_enabled = semantic_enabled or bool(
            retrieval_result.get("semantic_enabled", False)
        )
        semantic_qualities.append(
            _text(retrieval_result.get("semantic_quality")) or "disabled"
        )
        reranked_rows = _rerank_style_rows(
            _merge_style_candidate_rows(
                retrieval_result["results"],
                focused_result["results"],
            ),
            query=query,
            slot_type=slot_type,
        )
        selected_rows = _select_units(
            reranked_rows,
            top_k,
            preferred_unit_types=[slot_type],
            max_per_record=1,
        )
        selected_rows_by_slot[slot_type] = selected_rows
        all_selected_rows.extend(selected_rows)
        style_slots[slot_type] = [_style_slot_example(row) for row in selected_rows]

    prompt_context, prompt_included_count = _build_style_prompt_context(
        query,
        style_slots,
        active_slots=active_slots,
    )
    normalized_query, expanded_query = _expanded_query(_style_base_query(query), expansion_mode)
    source_record_ids = {
        _text(row.get("record_id"))
        for rows in selected_rows_by_slot.values()
        for row in rows
        if _text(row.get("record_id"))
    }
    return {
        "query": query,
        "normalized_query": normalized_query,
        "expanded_query": expanded_query,
        "expansion_mode": expansion_mode if expansion_mode in {"strict", "balanced", "broad"} else "balanced",
        "semantic_enabled": semantic_enabled,
        "semantic_quality": (
            "production"
            if "production" in semantic_qualities
            else "test_hash"
            if "test_hash" in semantic_qualities
            else "disabled"
        ),
        "retrieval_mode": "hybrid",
        "active_style_slots": active_slots,
        "style_slots": style_slots,
        "grouped_contexts": group_results_by_record(all_selected_rows),
        "prompt_context": prompt_context,
        "prompt_included_count": prompt_included_count,
        "prompt_character_count": len(prompt_context),
        "source_record_count": len(source_record_ids),
    }
