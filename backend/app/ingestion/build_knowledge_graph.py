from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.graph.graph_builder import build_knowledge_graph as build_sqlite_knowledge_graph
from app.graph.graph_repository import SUPPORTED_EDGE_TYPES, SUPPORTED_NODE_TYPES
def build_knowledge_graph(db_path: Path | None = None) -> dict[str, Any]:
    return build_sqlite_knowledge_graph(db_path)


def print_build_stats(stats: dict[str, Any]) -> None:
    for warning in stats.get("warnings", []):
        print(f"Warning: {warning}")

    print("Knowledge graph build complete.")
    node_distribution = stats.get("node_type_distribution", {})
    for node_type in SUPPORTED_NODE_TYPES:
        print(f"{node_type} node count: {node_distribution.get(node_type, 0)}")

    print(f"edge count: {stats.get('edge_count', 0)}")
    print()
    print("edge type distribution:")
    edge_distribution = stats.get("edge_type_distribution", {})
    for edge_type in SUPPORTED_EDGE_TYPES:
        print(f"{edge_type}: {edge_distribution.get(edge_type, 0)}")


def main() -> None:
    stats = build_knowledge_graph()
    print_build_stats(stats)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
