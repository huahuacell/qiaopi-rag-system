from __future__ import annotations

from typing import Any, Mapping

from app.schemas import ConsistencyCheckRequest
from app.validation.consistency_checker import validate_generation_consistency


def run_consistency_check(request: ConsistencyCheckRequest) -> dict[str, Any]:
    evidence_references: list[Mapping[str, Any]] = [
        reference.model_dump()
        for reference in request.evidence_references
    ]
    return {
        "validation_report": validate_generation_consistency(
            task_type=request.task_type,
            input_text=request.input_text,
            generated_text=request.generated_text,
            evidence_references=evidence_references,
            record_id=request.record_id,
        )
    }
