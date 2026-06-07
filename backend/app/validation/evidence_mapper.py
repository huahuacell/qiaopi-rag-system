def map_evidence(target_spans: list, evidence: list) -> list:
    mappings = []
    for target_span, evidence_item in zip(target_spans, evidence):
        mappings.append(
            {
                "target_span": target_span,
                "source_field": evidence_item.get("source_field", "unknown"),
                "source_text": evidence_item.get("source_text", ""),
                "reason": "Placeholder evidence mapping",
                "similarity_score": evidence_item.get("similarity_score", 0.0),
            }
        )
    return mappings

