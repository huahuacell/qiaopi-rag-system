from app.database.repository import count_rows, fetch_chart_items


def _origin_places() -> list[dict]:
    return fetch_chart_items(
        table_name="qiaopi_metadata_records",
        label_expression="origin_place",
        where_clause="WHERE origin_place IS NOT NULL AND origin_place <> ''",
        limit=8,
    )


def _destination_places() -> list[dict]:
    return fetch_chart_items(
        table_name="qiaopi_metadata_records",
        label_expression="destination_place",
        where_clause="WHERE destination_place IS NOT NULL AND destination_place <> ''",
        limit=8,
    )


def _kinship_distribution() -> list[dict]:
    return fetch_chart_items(
        table_name="qiaopi_entity_mentions",
        label_expression="COALESCE(NULLIF(normalized_text, ''), entity_text)",
        where_clause="WHERE entity_type = 'kinship'",
        limit=8,
    )


def _money_distribution() -> list[dict]:
    return fetch_chart_items(
        table_name="qiaopi_amount_mentions",
        label_expression="COALESCE(NULLIF(amount_text, ''), raw_text)",
        where_clause=(
            "WHERE COALESCE(NULLIF(amount_text, ''), raw_text) "
            "IS NOT NULL"
        ),
        limit=8,
    )


def _year_distribution() -> list[dict]:
    return fetch_chart_items(
        table_name="qiaopi_metadata_records",
        label_expression="CAST((date_year / 10) * 10 AS TEXT) || 's'",
        where_clause="WHERE date_year IS NOT NULL",
        group_expression="(date_year / 10)",
        order_expression="(date_year / 10)",
    )


def get_dashboard_stats() -> dict:
    return {
        "total_records": count_rows("qiaopi_metadata_records"),
        "text_records": count_rows("qiaopi_text_records"),
        "origin_places": _origin_places(),
        "destination_places": _destination_places(),
        "kinship_distribution": _kinship_distribution(),
        "money_distribution": _money_distribution(),
        "timeline": _year_distribution(),
    }


def get_dashboard_distributions() -> dict:
    return {
        "top_places": _origin_places(),
        "relationship_distribution": _kinship_distribution(),
        "year_distribution": _year_distribution(),
    }
