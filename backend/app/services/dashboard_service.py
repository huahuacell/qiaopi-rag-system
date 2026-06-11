from __future__ import annotations

from app.database.repository import (
    fetch_dashboard_distributions,
    fetch_dashboard_stats,
)


def get_dashboard_stats() -> dict:
    return fetch_dashboard_stats()


def get_dashboard_distributions() -> dict:
    return fetch_dashboard_distributions()
