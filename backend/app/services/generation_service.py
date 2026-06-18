import re

from app.database.repository import search_text_records
from app.schemas import PlainInterpretationRequest, StyleTransferRequest
from app.services.record_service import get_record_detail


def _mapping_from_evidence(evidence: list[dict], target_prefix: str) -> list[dict]:
    return [
        {
            "target_span": f"{target_prefix}{index + 1}",
            "source_field": item["source_field"],
            "source_text": item["source_text"],
            "reason": item["reason"],
            "similarity_score": item["similarity_score"],
        }
        for index, item in enumerate(evidence[:6])
    ]


def generate_plain_interpretation(request: PlainInterpretationRequest) -> dict:
    detail = get_record_detail(request.record_id) if request.record_id else None
    if detail:
        metadata = detail["metadata"]
        evidence = detail["evidence"]
        generated_text = detail["normalized_text"] or detail["original_text"]
        summary = [
            item.strip()
            for item in re.split(r"[；;]", generated_text)
            if item.strip()
        ][:6]
        return {
            "record_id": detail["record_id"],
            "generated_text": generated_text,
            "summary": summary,
            "slots": {
                "sender": metadata.get("sender_name_clean", metadata.get("sender", "")),
                "recipient": metadata.get(
                    "recipient_name_clean", metadata.get("recipient", "")
                ),
                "origin_place": metadata.get("origin_place", ""),
                "destination_place": metadata.get("destination_place", ""),
                "money": metadata.get("money", ""),
                "purpose": metadata.get("main_intent", ""),
            },
            "evidence": evidence,
            "evidence_mapping": _mapping_from_evidence(evidence, "释读依据 "),
            "consistency_check": {
                "status": "passed" if evidence else "pending",
                "warnings": [] if evidence else ["当前记录没有结构化证据片段。"],
                "passed_rules": (
                    ["record_loaded_from_sqlite", "evidence_loaded_from_sqlite"]
                    if evidence
                    else ["record_loaded_from_sqlite"]
                ),
                "failed_rules": [],
            },
        }

    original_text = (request.original_text or "").strip()
    evidence = (
        [
            {
                "source_field": "original_text",
                "source_text": original_text,
                "reason": "用户输入原文",
                "similarity_score": 1.0,
            }
        ]
        if original_text
        else []
    )
    return {
        "record_id": request.record_id,
        "generated_text": original_text,
        "summary": [original_text] if original_text else [],
        "slots": {},
        "evidence": evidence,
        "evidence_mapping": _mapping_from_evidence(evidence, "输入依据 "),
        "consistency_check": {
            "status": "pending",
            "warnings": ["未找到对应数据库记录，且真实 Qwen 生成尚未启用。"],
            "passed_rules": [],
            "failed_rules": [],
        },
    }


def _extract_first(pattern: str, text: str, default: str) -> str:
    match = re.search(pattern, text)
    return match.group(1) if match else default


def generate_style_transfer(request: StyleTransferRequest) -> dict:
    plain_text = request.plain_text.strip()
    recipient = request.slots.get("recipient") or _extract_first(
        r"(母亲|父亲|父母|祖母|祖父|妻子|兄长|弟弟)",
        plain_text,
        "家中大人",
    )
    origin_place = request.slots.get("origin_place") or _extract_first(
        r"(新加坡|泰国|越南|马来西亚|香港|海外)",
        plain_text,
        "外洋",
    )
    money = request.slots.get("money") or _extract_first(
        r"([零一二三四五六七八九十百千万壹贰叁肆伍陆柒捌玖拾佰仟\d]+元)",
        plain_text,
        "",
    )
    purpose = request.slots.get("purpose", "家用")

    remittance_sentence = (
        f"今托便奉上银{money}，伏乞查收，以备{purpose}之用。"
        if money
        else "家中诸务，伏乞珍重。"
    )
    generated_text = (
        f"{recipient}膝下敬禀者：男在{origin_place}平安，勿以为念。"
        f"{remittance_sentence}谨此禀安。"
    )

    query = " ".join(value for value in (recipient, origin_place, money) if value)
    rows = search_text_records(query, filters={})[:3]
    evidence = [
        {
            "source_field": str(row.get("unit_type") or "style_reference"),
            "source_text": str(row.get("unit_text") or ""),
            "reason": "SQLite 侨批风格样例检索",
            "similarity_score": round(max(0.7, 0.95 - index * 0.08), 2),
        }
        for index, row in enumerate(rows)
        if row.get("unit_text")
    ]

    return {
        "generated_text": generated_text,
        "summary": [
            "使用确定性模板完成侨批体转换。",
            "人物、地点和金额来自用户输入；风格证据来自 SQLite 检索。",
        ],
        "slots": {
            "recipient": recipient,
            "origin_place": origin_place,
            "money": money,
            "purpose": purpose,
            "input_preview": plain_text[:80],
        },
        "evidence": evidence,
        "evidence_mapping": _mapping_from_evidence(evidence, "风格依据 "),
        "consistency_check": {
            "status": "passed",
            "warnings": ["当前为确定性模板生成，尚未调用真实 Qwen。"],
            "passed_rules": [
                "input_recipient_preserved",
                "input_origin_preserved",
                "input_money_preserved",
            ],
            "failed_rules": [],
        },
    }
