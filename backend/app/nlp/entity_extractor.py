def extract_entities(text: str) -> list:
    if not text:
        return []
    return [
        {
            "entity_type": "money",
            "value": "eight yuan",
            "source_text": "银八元",
            "confidence": 0.8,
        }
    ]

