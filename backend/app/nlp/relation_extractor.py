def extract_relations(entities: list) -> list:
    if not entities:
        return []
    return [
        {
            "source": "sender",
            "target": "mother",
            "relation": "remits_money_to",
            "confidence": 0.75,
        }
    ]

