"""Export graph data in a stable JSON schema for reuse and analysis."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile

import networkx as nx

from analytics import summarize_graph


JSON_SCHEMA_VERSION = "1.0"


def export_graph_json(graph: nx.DiGraph, output_path: Path) -> Path:
    """Write nodes, typed links, and graph metrics as UTF-8 JSON atomically."""
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    nodes = [
        {
            "id": str(node_id),
            "title": str(attributes.get("label", node_id)),
            "path": attributes.get("path"),
            "exists": attributes.get("exists", True),
        }
        for node_id, attributes in sorted(graph.nodes(data=True), key=lambda pair: str(pair[0]))
    ]
    edges = []
    for source, target, attributes in sorted(
        graph.edges(data=True), key=lambda edge: (str(edge[0]), str(edge[1]))
    ):
        explicit = bool(attributes.get("explicit", False))
        semantic = bool(attributes.get("semantic", False))
        edge_type = (
            "explicit+semantic" if explicit and semantic
            else "explicit" if explicit
            else "semantic" if semantic
            else "unknown"
        )
        edges.append(
            {
                "source": str(source),
                "target": str(target),
                "type": edge_type,
                "explicit": explicit,
                "semantic": semantic,
                "similarity": attributes.get("similarity"),
                "explicit_directional": explicit,
            }
        )

    document = {
        "schema_version": JSON_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "semantic_settings": graph.graph.get("semantic_settings", {}),
        "summary": summarize_graph(graph),
        "nodes": nodes,
        "edges": edges,
    }
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output_path.parent,
            prefix=f"{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = temporary_file.name
            json.dump(document, temporary_file, ensure_ascii=False, indent=2)
            temporary_file.write("\n")
        os.replace(temporary_path, output_path)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)
    return output_path
