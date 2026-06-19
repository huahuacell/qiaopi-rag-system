from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from pathlib import Path
from typing import Any, Mapping

from app import settings
from app.database.repository import (
    fetch_generation_cache,
    insert_generation_log,
    insert_query_log,
    store_generation_cache,
)
from app.llm.prompts import (
    INTERPRETATION_PROMPT_VERSION,
    STYLE_TRANSFER_PROMPT_VERSION,
    build_interpretation_prompt,
    build_style_transfer_prompt,
)
from app.llm.qwen_client import QwenClient, QwenClientError
from app.schemas import (
    GenerationInterpretRequest,
    GenerationStyleTransferRequest,
    PromptPreviewRequest,
)
from app.search.context_builder import (
    build_rag_context,
    build_record_rag_context,
    build_style_context,
)
from app.validation.consistency_checker import validate_generation_consistency
from app.validation.evidence_mapper import map_generated_text_to_evidence


LOCAL_GENERATOR_VERSION = "deterministic-local-v1"


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _evidence_reference(item: Mapping[str, Any]) -> dict[str, str]:
    return {
        "record_id": _text(item.get("record_id")),
        "unit_id": _text(item.get("unit_id")),
        "unit_type": _text(item.get("unit_type")),
        "title_reference": _text(item.get("title_reference")),
        "source_column": _text(item.get("source_column")),
        "evidence_type": _text(item.get("evidence_type")),
        "unit_text": _text(item.get("unit_text")),
    }


def _references_from_contexts(
    contexts: list[Mapping[str, Any]],
) -> list[dict[str, str]]:
    references: list[dict[str, str]] = []
    seen_unit_ids: set[str] = set()
    for context in contexts:
        unit_id = _text(context.get("unit_id"))
        if not unit_id or unit_id in seen_unit_ids:
            continue
        seen_unit_ids.add(unit_id)
        references.append(_evidence_reference(context))
    return references


def _references_from_style_slots(
    style_slots: Mapping[str, list[Mapping[str, Any]]],
) -> list[dict[str, str]]:
    references: list[dict[str, str]] = []
    seen_unit_ids: set[str] = set()
    for examples in style_slots.values():
        for example in examples:
            unit_id = _text(example.get("unit_id"))
            if not unit_id or unit_id in seen_unit_ids:
                continue
            seen_unit_ids.add(unit_id)
            references.append(_evidence_reference(example))
    return references


def _log_generation_request(
    *,
    endpoint: str,
    query: str,
    filters: Mapping[str, Any],
    top_k: int,
    returned_count: int,
) -> None:
    try:
        insert_query_log(
            endpoint=endpoint,
            query=query,
            filters=filters,
            top_k=top_k,
            returned_count=returned_count,
        )
    except Exception:
        return


def _log_generation_call(**values: Any) -> None:
    try:
        insert_generation_log(**values)
    except Exception:
        return


def _validation_report_or_none(
    *,
    task_type: str,
    input_text: str,
    generated_text: str,
    evidence_references: list[Mapping[str, Any]],
    record_id: str | None = None,
) -> dict[str, Any] | None:
    if not generated_text.strip():
        return None
    return validate_generation_consistency(
        task_type=task_type,
        input_text=input_text,
        generated_text=generated_text,
        evidence_references=evidence_references,
        record_id=record_id,
    )


def _rag_context_for_interpretation(
    request: GenerationInterpretRequest,
) -> dict[str, Any]:
    if request.record_id:
        return build_record_rag_context(
            query=request.query,
            record_id=request.record_id,
            top_k=request.top_k,
            filters=request.filters,
            expansion_mode=request.expansion_mode,
        )
    return build_rag_context(
        query=request.query,
        top_k=request.top_k,
        unit_types=[],
        filters=request.filters,
        expansion_mode=request.expansion_mode,
    )


def _index_version() -> str:
    manifest_paths = (
        settings.PROCESSED_DATA_DIR / "qiaopi_build_manifest.json",
        settings.SEMANTIC_FAISS_MANIFEST_PATH,
    )
    for path in manifest_paths:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            continue
        relational = _text(payload.get("relational", {}).get("combined_sha256"))
        vector = _text(
            payload.get("vector", {}).get("corpus_fingerprint")
            or payload.get("corpus_fingerprint")
        )
        manifest_version = _text(
            payload.get("manifest_version") or payload.get("version")
        )
        parts = [
            f"rel:{relational[:16]}" if relational else "",
            f"vec:{vector[:16]}" if vector else "",
            f"manifest:{manifest_version}" if manifest_version else "",
        ]
        version = "|".join(part for part in parts if part)
        if version:
            return version
    return "index-unversioned"


def _cache_identity(
    *,
    task_type: str,
    input_text: str,
    record_id: str | None,
    filters: Mapping[str, Any],
    top_k: int,
    expansion_mode: str,
    evidence_references: list[Mapping[str, Any]],
    generation_backend: str,
    model: str,
    prompt_version: str,
    index_version: str,
) -> tuple[str, str]:
    payload = {
        "task_type": task_type,
        "input_text": input_text.strip(),
        "record_id": record_id or "",
        "filters": filters,
        "top_k": top_k,
        "expansion_mode": expansion_mode,
        "evidence_units": [
            {
                "unit_id": _text(item.get("unit_id")),
                "unit_text_hash": hashlib.sha256(
                    _text(item.get("unit_text")).encode("utf-8")
                ).hexdigest(),
            }
            for item in evidence_references
        ],
        "generation_backend": generation_backend,
        "model": model,
        "prompt_version": prompt_version,
        "index_version": index_version,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    cache_key = hashlib.sha256(encoded).hexdigest()
    return cache_key, cache_key


def _normalize_structured_output(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "generated_text": _text(value.get("generated_text")),
        "summary": _string_list(value.get("summary")),
        "style_notes": _string_list(value.get("style_notes")),
        "warnings": _string_list(value.get("warnings")),
    }


def _local_interpretation(
    input_text: str,
    evidence_references: list[Mapping[str, Any]],
) -> dict[str, Any]:
    evidence_texts = [
        _text(item.get("unit_text"))
        for item in evidence_references[:3]
        if _text(item.get("unit_text"))
    ]
    if evidence_texts:
        generated_text = (
            "【本地降级解读】根据当前可追溯证据，"
            + "；".join(evidence_texts)
            + "。该内容由确定性本地规则整理，未调用 Qwen。"
        )
    else:
        generated_text = (
            f"【本地降级解读】当前问题为“{input_text.strip()}”，"
            "但没有可用的全文证据，无法作出可靠释读。"
        )
    return {
        "generated_text": generated_text,
        "summary": ["确定性本地降级", f"引用证据 {len(evidence_texts)} 条"],
        "style_notes": [],
        "warnings": ["未调用 Qwen；请结合证据与人工复核。"],
    }


def _local_style_transfer(
    plain_text: str,
    evidence_references: list[Mapping[str, Any]],
) -> dict[str, Any]:
    transformed = plain_text.strip()
    replacements = (
        ("母亲，", "慈亲大人膝下："),
        ("母亲您好", "慈亲大人膝下"),
        ("我在", "儿在"),
        ("寄回", "兹寄上"),
        ("请您放心", "伏祈勿念"),
    )
    for source, target in replacements:
        transformed = transformed.replace(source, target)
    if not transformed.startswith("慈亲"):
        transformed = f"【生成草稿·本地降级】{transformed}"
    transformed = f"{transformed}\n此为确定性本地降级草稿，未调用 Qwen。"
    return {
        "generated_text": transformed,
        "summary": ["保留用户输入事实", "未新增金额、人物或地点"],
        "style_notes": ["使用有限的确定性侨批称谓与汇款措辞替换"],
        "warnings": [
            f"未调用 Qwen；仅参考 {len(evidence_references)} 条风格证据，需人工复核。"
        ],
    }


def _execute_generation(
    *,
    task_type: str,
    endpoint: str,
    input_text: str,
    record_id: str | None,
    filters: Mapping[str, Any],
    top_k: int,
    expansion_mode: str,
    messages: list[dict[str, str]],
    evidence_references: list[dict[str, str]],
    prompt_version: str,
    dry_run: bool,
) -> dict[str, Any]:
    started = time.monotonic()
    request_id = str(uuid.uuid4())
    index_version = _index_version()
    configured_reason = settings.qwen_degraded_reason()

    if dry_run:
        backend = "prompt_preview"
        model = "none"
        degraded_reason = "dry_run_requested"
    elif configured_reason:
        backend = "deterministic_local"
        model = LOCAL_GENERATOR_VERSION
        degraded_reason = configured_reason
    else:
        backend = "qwen"
        model = settings.QWEN_MODEL
        degraded_reason = None

    cache_key, input_hash = _cache_identity(
        task_type=task_type,
        input_text=input_text,
        record_id=record_id,
        filters=filters,
        top_k=top_k,
        expansion_mode=expansion_mode,
        evidence_references=evidence_references,
        generation_backend=backend,
        model=model,
        prompt_version=prompt_version,
        index_version=index_version,
    )
    structured_output: dict[str, Any]
    cache_hit = False
    attempt_count = 0
    error_message: str | None = None
    error_type: str | None = None
    cacheable = not dry_run

    if dry_run:
        structured_output = {
            "generated_text": "",
            "summary": [],
            "style_notes": [],
            "warnings": [],
        }
    else:
        cached = fetch_generation_cache(cache_key)
        if cached:
            structured_output = _normalize_structured_output(
                cached["result"].get("structured_output", {})
            )
            backend = _text(cached.get("generation_backend")) or backend
            model = _text(cached.get("model")) or model
            cache_hit = True
        elif backend == "qwen":
            try:
                qwen_result = QwenClient().generate_structured(messages)
                structured_output = _normalize_structured_output(
                    qwen_result.payload
                )
                model = qwen_result.model
                attempt_count = qwen_result.attempt_count
            except QwenClientError as exc:
                backend = "deterministic_local"
                model = LOCAL_GENERATOR_VERSION
                degraded_reason = exc.reason_code
                error_type = exc.reason_code
                error_message = str(exc)
                attempt_count = exc.attempt_count
                cacheable = False
                structured_output = (
                    _local_interpretation(input_text, evidence_references)
                    if task_type == "interpret"
                    else _local_style_transfer(input_text, evidence_references)
                )
        else:
            structured_output = (
                _local_interpretation(input_text, evidence_references)
                if task_type == "interpret"
                else _local_style_transfer(input_text, evidence_references)
            )

    structured_output = _normalize_structured_output(structured_output)
    if cacheable and not cache_hit:
        store_generation_cache(
            cache_key=cache_key,
            task_type=task_type,
            input_hash=input_hash,
            record_id=record_id,
            generation_backend=backend,
            model=model,
            prompt_version=prompt_version,
            index_version=index_version,
            result={"structured_output": structured_output},
        )

    generated_text = structured_output["generated_text"]
    evidence_mapping = (
        map_generated_text_to_evidence(generated_text, evidence_references)
        if generated_text
        else []
    )
    duration_ms = max(0, round((time.monotonic() - started) * 1000))
    status = (
        "preview"
        if backend == "prompt_preview"
        else "degraded"
        if degraded_reason
        else "success"
    )
    _log_generation_call(
        request_id=request_id,
        endpoint=endpoint,
        task_type=task_type,
        generation_backend=backend,
        model=model,
        prompt_version=prompt_version,
        index_version=index_version,
        cache_key=cache_key,
        cache_hit=cache_hit,
        attempt_count=attempt_count,
        status=status,
        degraded_reason=degraded_reason,
        duration_ms=duration_ms,
        evidence_count=len(evidence_references),
        error_type=error_type,
    )
    return {
        "request_id": request_id,
        "generation_backend": backend,
        "model": model,
        "prompt_version": prompt_version,
        "index_version": index_version,
        "cache_hit": cache_hit,
        "cache_key": cache_key,
        "attempt_count": attempt_count,
        "degraded_reason": degraded_reason,
        "generated_text": generated_text,
        "structured_output": structured_output,
        "evidence_mapping": evidence_mapping,
        "dry_run": dry_run,
        "error_message": error_message,
    }


def generate_interpretation(request: GenerationInterpretRequest) -> dict[str, Any]:
    context = _rag_context_for_interpretation(request)
    evidence_references = _references_from_contexts(context["contexts"])
    messages = build_interpretation_prompt(
        query=request.query,
        prompt_context=context["prompt_context"],
        evidence_references=evidence_references,
    )
    generation = _execute_generation(
        task_type="interpret",
        endpoint="/api/generation/interpret",
        input_text=request.query,
        record_id=request.record_id,
        filters=request.filters,
        top_k=request.top_k,
        expansion_mode=request.expansion_mode,
        messages=messages,
        evidence_references=evidence_references,
        prompt_version=INTERPRETATION_PROMPT_VERSION,
        dry_run=request.dry_run,
    )
    _log_generation_request(
        endpoint="/api/generation/interpret",
        query=request.query,
        filters={
            **request.filters,
            **({"record_id": request.record_id} if request.record_id else {}),
        },
        top_k=request.top_k,
        returned_count=len(evidence_references),
    )
    return {
        "task_type": "interpret",
        "query": request.query,
        "record_id": request.record_id,
        "semantic_enabled": context["semantic_enabled"],
        "semantic_quality": context.get("semantic_quality", "disabled"),
        "prompt_context": context["prompt_context"],
        "evidence_references": evidence_references,
        "messages": messages,
        **generation,
        "validation_report": _validation_report_or_none(
            task_type="interpret",
            input_text=request.query,
            generated_text=generation["generated_text"],
            evidence_references=evidence_references,
            record_id=request.record_id,
        ),
    }


def generate_style_transfer(
    request: GenerationStyleTransferRequest,
) -> dict[str, Any]:
    context = build_style_context(
        query=request.plain_text,
        top_k=request.top_k,
        filters=request.filters,
        expansion_mode=request.expansion_mode,
    )
    evidence_references = _references_from_style_slots(context["style_slots"])
    messages = build_style_transfer_prompt(
        plain_text=request.plain_text,
        prompt_context=context["prompt_context"],
        evidence_references=evidence_references,
    )
    generation = _execute_generation(
        task_type="style-transfer",
        endpoint="/api/generation/style-transfer",
        input_text=request.plain_text,
        record_id=None,
        filters=request.filters,
        top_k=request.top_k,
        expansion_mode=request.expansion_mode,
        messages=messages,
        evidence_references=evidence_references,
        prompt_version=STYLE_TRANSFER_PROMPT_VERSION,
        dry_run=request.dry_run,
    )
    _log_generation_request(
        endpoint="/api/generation/style-transfer",
        query=request.plain_text,
        filters=request.filters,
        top_k=request.top_k,
        returned_count=len(evidence_references),
    )
    return {
        "task_type": "style-transfer",
        "plain_text": request.plain_text,
        "semantic_enabled": context["semantic_enabled"],
        "semantic_quality": context.get("semantic_quality", "disabled"),
        "style_slots": context["style_slots"],
        "prompt_context": context["prompt_context"],
        "evidence_references": evidence_references,
        "messages": messages,
        **generation,
        "validation_report": _validation_report_or_none(
            task_type="style-transfer",
            input_text=request.plain_text,
            generated_text=generation["generated_text"],
            evidence_references=evidence_references,
        ),
    }


def preview_prompt(request: PromptPreviewRequest) -> dict[str, Any]:
    if request.task_type == "style-transfer":
        context = build_style_context(
            query=request.input_text,
            top_k=request.top_k,
            filters=request.filters,
            expansion_mode=request.expansion_mode,
        )
        evidence_references = _references_from_style_slots(context["style_slots"])
        messages = build_style_transfer_prompt(
            plain_text=request.input_text,
            prompt_context=context["prompt_context"],
            evidence_references=evidence_references,
        )
        prompt_version = STYLE_TRANSFER_PROMPT_VERSION
    else:
        interpret_request = GenerationInterpretRequest(
            query=request.input_text,
            record_id=request.record_id,
            top_k=request.top_k,
            filters=request.filters,
            expansion_mode=request.expansion_mode,
            dry_run=True,
        )
        context = _rag_context_for_interpretation(interpret_request)
        evidence_references = _references_from_contexts(context["contexts"])
        messages = build_interpretation_prompt(
            query=request.input_text,
            prompt_context=context["prompt_context"],
            evidence_references=evidence_references,
        )
        prompt_version = INTERPRETATION_PROMPT_VERSION

    _log_generation_request(
        endpoint="/api/generation/preview-prompt",
        query=request.input_text,
        filters={
            **request.filters,
            **({"record_id": request.record_id} if request.record_id else {}),
        },
        top_k=request.top_k,
        returned_count=len(evidence_references),
    )
    return {
        "task_type": request.task_type,
        "input_text": request.input_text,
        "prompt_context": context["prompt_context"],
        "messages": messages,
        "evidence_references": evidence_references,
        "prompt_version": prompt_version,
        "index_version": _index_version(),
    }


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_text(item) for item in value if _text(item)]
