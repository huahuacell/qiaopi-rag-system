def keyword_rank(query: str, records: list) -> list:
    normalized_query = query.lower().strip()
    if not normalized_query:
        return records
    return [
        record
        for record in records
        if normalized_query in " ".join(str(value) for value in record.values()).lower()
    ]

