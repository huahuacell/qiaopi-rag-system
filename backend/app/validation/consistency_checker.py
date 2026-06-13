from __future__ import annotations

from typing import Any, Mapping

from app.database.repository import (
    fetch_evidence_spans,
    fetch_retrieval_units,
    fetch_text_record,
)
from app.validation.fact_extractor import (
    canonical_amounts,
    canonical_places,
    extract_facts,
)


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _check(name: str, status: str, message: str) -> dict[str, str]:
    return {"name": name, "status": status, "message": message}


def _coverage(evidence_references: list[Mapping[str, Any]]) -> dict[str, Any]:
    unit_types = sorted(
        {
            _text(reference.get("unit_type"))
            for reference in evidence_references
            if _text(reference.get("unit_type"))
        }
    )
    return {
        "has_evidence_references": bool(evidence_references),
        "evidence_count": len(evidence_references),
        "covered_unit_types": unit_types,
    }


def _risk_level(
    *,
    unsupported_new_facts: list[str],
    missing_required_facts: list[str],
    evidence_references: list[Mapping[str, Any]],
) -> str:
    high_markers = ("金额", "日期", "姓名", "地点")
    if any(any(marker in fact for marker in high_markers) for fact in unsupported_new_facts):
        return "high"
    if unsupported_new_facts or missing_required_facts:
        return "medium"
    if not evidence_references:
        return "medium"
    return "low"


def _style_transfer_report(
    *,
    input_text: str,
    generated_text: str,
    evidence_references: list[Mapping[str, Any]],
) -> dict[str, Any]:
    input_facts = extract_facts(input_text)
    generated_facts = extract_facts(generated_text)
    checks: list[dict[str, str]] = []
    preserved_facts: list[str] = []
    missing_required_facts: list[str] = []
    unsupported_new_facts: list[str] = []
    possible_hallucinations: list[str] = []

    if "母亲" in input_text:
        if any(term in generated_text for term in ("母亲", "慈亲", "大人", "膝下")):
            preserved_facts.append("母亲称谓已保留为亲属/尊称表达")
            checks.append(_check("kinship_consistency", "pass", "输入中的母亲称谓在生成文本中以亲属尊称形式保留。"))
        else:
            missing_required_facts.append("缺少母亲相关称谓")
            checks.append(_check("kinship_consistency", "fail", "输入包含母亲，但生成文本未保留母亲/慈亲/大人/膝下等称谓。"))

    input_places = set(input_facts["place_concepts"])
    generated_places = set(generated_facts["place_concepts"])
    if "新加坡" in input_places:
        if "新加坡" in generated_places:
            preserved_facts.append("新加坡地点已以允许别名保留")
            checks.append(_check("place_consistency", "pass", "输入地点新加坡在生成文本中以新加坡/星洲/叻/叻埠/石叻等允许别名保留。"))
        else:
            missing_required_facts.append("缺少新加坡或其允许别名")
            checks.append(_check("place_consistency", "fail", "输入包含新加坡，但生成文本未出现允许地点别名。"))
    extra_places = sorted(generated_places - input_places)
    if extra_places:
        unsupported_new_facts.extend(f"新增 unsupported 地点：{place}" for place in extra_places)
        checks.append(_check("new_place_check", "fail", f"生成文本出现输入未提供的地点：{'、'.join(extra_places)}。"))

    input_amounts = set(input_facts["amount_values"])
    generated_amounts = set(generated_facts["amount_values"])
    if input_amounts:
        if input_amounts.issubset(generated_amounts):
            preserved_facts.append("输入金额已保留")
            checks.append(_check("amount_consistency", "pass", "输入金额在生成文本中以等值中文金额形式保留。"))
        else:
            missing = sorted(input_amounts - generated_amounts)
            missing_required_facts.extend(f"缺少输入金额：{amount}元" for amount in missing)
            checks.append(_check("amount_consistency", "fail", f"生成文本未保留输入金额：{'、'.join(missing)}元。"))
    extra_amounts = sorted(generated_amounts - input_amounts)
    if extra_amounts:
        unsupported_new_facts.extend(f"新增 unsupported 金额：{amount}元" for amount in extra_amounts)
        checks.append(_check("new_amount_check", "fail", f"生成文本出现输入未提供的金额：{'、'.join(extra_amounts)}元。"))

    input_dates = set(input_facts["date_terms"])
    generated_dates = set(generated_facts["date_terms"])
    extra_dates = sorted(generated_dates - input_dates)
    if extra_dates:
        unsupported_new_facts.extend(f"新增 unsupported 日期：{date}" for date in extra_dates)
        checks.append(_check("new_date_check", "fail", f"生成文本出现输入未提供的具体日期：{'、'.join(extra_dates)}。"))
    else:
        checks.append(_check("new_date_check", "pass", "生成文本未新增具体日期。"))

    if not input_facts["person_terms"] and generated_facts["person_terms"]:
        names = "、".join(generated_facts["person_terms"])
        unsupported_new_facts.append(f"新增 unsupported 姓名：{names}")
        checks.append(_check("new_name_check", "fail", f"用户未提供姓名，但生成文本出现具体姓名：{names}。"))
    else:
        checks.append(_check("new_name_check", "pass", "生成文本未新增具体姓名。"))

    if "弟弟" in input_text and any(term in input_text for term in ("读书", "学习", "勤奋")):
        if any(term in generated_text for term in ("弟", "胞弟", "读书", "勤学", "向学", "用功")):
            preserved_facts.append("弟弟读书嘱托已保留")
            checks.append(_check("study_instruction_consistency", "pass", "弟弟读书嘱托在生成文本中以劝学表达保留。"))
        else:
            missing_required_facts.append("缺少弟弟读书/勤学嘱托")
            checks.append(_check("study_instruction_consistency", "fail", "输入包含弟弟读书嘱托，但生成文本未保留相关表达。"))

    if generated_facts["remittance_terms"]:
        checks.append(_check("remittance_expression", "pass", "生成文本包含寄款/查收相关表达。"))
    elif input_facts["amount_values"]:
        missing_required_facts.append("缺少寄款/查收表达")
        checks.append(_check("remittance_expression", "warn", "输入包含金额，但生成文本缺少寄款或查收表达。"))

    if "生成" in generated_text and any(term in generated_text for term in ("草稿", "解读", "内容")):
        checks.append(_check("generated_label", "pass", "生成文本明确标注为生成内容。"))
    else:
        possible_hallucinations.append("生成文本未明确标注为生成草稿")
        checks.append(_check("generated_label", "warn", "生成文本未明确标注为生成草稿，展示时需由接口或前端标注。"))

    if evidence_references:
        checks.append(_check("evidence_reference_check", "pass", "已返回证据引用。"))
    else:
        checks.append(_check("evidence_reference_check", "warn", "未提供证据引用，可信度降低。"))

    risk_level = _risk_level(
        unsupported_new_facts=unsupported_new_facts,
        missing_required_facts=missing_required_facts,
        evidence_references=evidence_references,
    )
    return {
        "is_consistent": risk_level != "high" and not missing_required_facts,
        "risk_level": risk_level,
        "summary": "规则校验完成：生成文本与输入事实基本一致。" if risk_level == "low" else "规则校验发现需要人工复核的事实风险。",
        "preserved_facts": preserved_facts,
        "possible_hallucinations": possible_hallucinations,
        "missing_required_facts": missing_required_facts,
        "unsupported_new_facts": unsupported_new_facts,
        "evidence_coverage": _coverage(evidence_references),
        "checks": checks,
    }


def _source_text_for_interpretation(
    record_id: str | None,
    evidence_references: list[Mapping[str, Any]],
) -> str:
    parts: list[str] = []
    if record_id:
        record = fetch_text_record(record_id)
        if record:
            parts.extend(
                _text(record.get(field_name))
                for field_name in (
                    "title_reference",
                    "sender",
                    "recipient",
                    "date_text",
                    "body_clean",
                    "body_core",
                    "main_intent",
                    "place_mentions_normalized",
                    "retrieval_keywords",
                    "rag_summary_text",
                )
            )
        parts.extend(_text(item.get("evidence_text")) for item in fetch_evidence_spans(record_id))
        parts.extend(_text(item.get("unit_text")) for item in fetch_retrieval_units(record_id))
    parts.extend(_text(reference.get("unit_text")) for reference in evidence_references)
    return "\n".join(part for part in parts if part)


def _interpretation_report(
    *,
    generated_text: str,
    evidence_references: list[Mapping[str, Any]],
    record_id: str | None,
) -> dict[str, Any]:
    source_facts = extract_facts(_source_text_for_interpretation(record_id, evidence_references))
    generated_facts = extract_facts(generated_text)
    checks: list[dict[str, str]] = []
    unsupported_new_facts: list[str] = []
    missing_required_facts: list[str] = []
    possible_hallucinations: list[str] = []
    preserved_facts: list[str] = []

    source_amounts = set(source_facts["amount_values"])
    generated_amounts = set(generated_facts["amount_values"])
    extra_amounts = sorted(generated_amounts - source_amounts)
    if extra_amounts:
        unsupported_new_facts.extend(f"新增 unsupported 金额：{amount}元" for amount in extra_amounts)
        checks.append(_check("amount_support_check", "fail", f"解释文本出现证据未支持的金额：{'、'.join(extra_amounts)}元。"))
    else:
        checks.append(_check("amount_support_check", "pass", "解释文本未新增证据外金额。"))
    if source_facts["remittance_terms"] and not generated_facts["remittance_terms"]:
        missing_required_facts.append("源证据包含汇款/查收信息，但解释未提及")
        checks.append(_check("remittance_coverage", "warn", "源证据包含汇款或查收信息，解释文本未明显提及。"))
    elif source_facts["remittance_terms"]:
        preserved_facts.append("源证据中的汇款信息已覆盖")
        checks.append(_check("remittance_coverage", "pass", "解释文本覆盖了源证据中的汇款/查收信息。"))

    source_places = set(source_facts["place_concepts"])
    extra_places = sorted(set(generated_facts["place_concepts"]) - source_places)
    if extra_places:
        unsupported_new_facts.extend(f"新增 unsupported 地点：{place}" for place in extra_places)
        checks.append(_check("place_support_check", "fail", f"解释文本出现证据未支持的地点：{'、'.join(extra_places)}。"))
    else:
        checks.append(_check("place_support_check", "pass", "解释文本未新增证据外地点。"))

    source_dates = set(source_facts["date_terms"])
    extra_dates = sorted(set(generated_facts["date_terms"]) - source_dates)
    if extra_dates:
        unsupported_new_facts.extend(f"新增 unsupported 日期：{date}" for date in extra_dates)
        checks.append(_check("date_support_check", "fail", f"解释文本出现证据未支持的日期：{'、'.join(extra_dates)}。"))
    else:
        checks.append(_check("date_support_check", "pass", "解释文本未新增证据外日期。"))

    if generated_facts["person_terms"] and source_facts["person_terms"]:
        extra_names = sorted(set(generated_facts["person_terms"]) - set(source_facts["person_terms"]))
    else:
        extra_names = generated_facts["person_terms"] if not source_facts["person_terms"] else []
    if extra_names:
        unsupported_new_facts.extend(f"新增 unsupported 姓名：{name}" for name in extra_names)
        checks.append(_check("person_support_check", "fail", f"解释文本出现证据未支持的姓名：{'、'.join(extra_names)}。"))
    else:
        checks.append(_check("person_support_check", "pass", "解释文本未新增证据外姓名。"))

    if evidence_references:
        checks.append(_check("evidence_reference_check", "pass", "已返回证据引用。"))
    else:
        checks.append(_check("evidence_reference_check", "warn", "未提供证据引用，解释可信度降低。"))

    if not source_facts["amount_values"]:
        possible_hallucinations.append("源证据金额不足时，解释中的金额需人工复核")

    risk_level = _risk_level(
        unsupported_new_facts=unsupported_new_facts,
        missing_required_facts=missing_required_facts,
        evidence_references=evidence_references,
    )
    return {
        "is_consistent": risk_level != "high",
        "risk_level": risk_level,
        "summary": "解释文本通过规则式证据一致性检查。" if risk_level == "low" else "解释文本存在需人工复核的证据一致性风险。",
        "preserved_facts": preserved_facts,
        "possible_hallucinations": possible_hallucinations,
        "missing_required_facts": missing_required_facts,
        "unsupported_new_facts": unsupported_new_facts,
        "evidence_coverage": _coverage(evidence_references),
        "checks": checks,
    }


def validate_generation_consistency(
    *,
    task_type: str,
    input_text: str,
    generated_text: str,
    evidence_references: list[Mapping[str, Any]],
    record_id: str | None = None,
) -> dict[str, Any]:
    if task_type == "style-transfer":
        return _style_transfer_report(
            input_text=input_text,
            generated_text=generated_text,
            evidence_references=evidence_references,
        )
    return _interpretation_report(
        generated_text=generated_text,
        evidence_references=evidence_references,
        record_id=record_id,
    )


def check_generation_consistency(slots: dict, evidence: list) -> dict:
    report = validate_generation_consistency(
        task_type="style-transfer",
        input_text=" ".join(str(value) for value in slots.values()),
        generated_text=" ".join(str(value) for value in slots.values()),
        evidence_references=evidence,
    )
    return {
        "status": "passed" if report["is_consistent"] else "warning",
        "warnings": report["possible_hallucinations"],
        "passed_rules": [
            check["name"]
            for check in report["checks"]
            if check["status"] == "pass"
        ],
        "failed_rules": [
            check["name"]
            for check in report["checks"]
            if check["status"] == "fail"
        ],
    }
