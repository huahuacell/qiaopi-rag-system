from __future__ import annotations

from typing import Any, Mapping

from app.database.repository import insert_query_log
from app.llm.prompts import build_interpretation_prompt, build_style_transfer_prompt
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
from app import settings
from app.validation.consistency_checker import validate_generation_consistency


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


def _references_from_contexts(contexts: list[Mapping[str, Any]]) -> list[dict[str, str]]:
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


def _generate_or_preview(
    *,
    messages: list[dict[str, str]],
    dry_run: bool,
) -> tuple[str, bool, str | None]:
    if dry_run:
        return "", True, None

    try:
        return (
            QwenClient().generate_chat_completion(messages),
            False,
            None,
        )
    except QwenClientError as exc:
        return "", True, str(exc)


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


def _rag_context_for_interpretation(request: GenerationInterpretRequest) -> dict[str, Any]:
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


def generate_interpretation(request: GenerationInterpretRequest) -> dict[str, Any]:
    context = _rag_context_for_interpretation(request)
    evidence_references = _references_from_contexts(context["contexts"])
    messages = build_interpretation_prompt(
        query=request.query,
        prompt_context=context["prompt_context"],
        evidence_references=evidence_references,
    )
    generated_text, effective_dry_run, error_message = _generate_or_preview(
        messages=messages,
        dry_run=request.dry_run,
    )
    _log_generation_request(
        endpoint="/api/generation/interpret",
        query=request.query,
        filters={**request.filters, **({"record_id": request.record_id} if request.record_id else {})},
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
        "generated_text": generated_text,
        "evidence_references": evidence_references,
        "model": settings.QWEN_MODEL,
        "dry_run": effective_dry_run,
        "messages": messages,
        "error_message": error_message,
        "validation_report": _validation_report_or_none(
            task_type="interpret",
            input_text=request.query,
            generated_text=generated_text,
            evidence_references=evidence_references,
            record_id=request.record_id,
        ),
    }


def generate_style_transfer(request: GenerationStyleTransferRequest) -> dict[str, Any]:
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
    generated_text, effective_dry_run, error_message = _generate_or_preview(
        messages=messages,
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
        "generated_text": generated_text,
        "evidence_references": evidence_references,
        "model": settings.QWEN_MODEL,
        "dry_run": effective_dry_run,
        "messages": messages,
        "error_message": error_message,
        "validation_report": _validation_report_or_none(
            task_type="style-transfer",
            input_text=request.plain_text,
            generated_text=generated_text,
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

    _log_generation_request(
        endpoint="/api/generation/preview-prompt",
        query=request.input_text,
        filters={**request.filters, **({"record_id": request.record_id} if request.record_id else {})},
        top_k=request.top_k,
        returned_count=len(evidence_references),
    )
    return {
        "task_type": request.task_type,
        "input_text": request.input_text,
        "prompt_context": context["prompt_context"],
        "messages": messages,
        "evidence_references": evidence_references,
    }
