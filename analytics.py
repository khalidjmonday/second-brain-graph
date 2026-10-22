"""Graph statistics for CLI summaries and machine-readable exports."""

from __future__ import annotations

import networkx as nx


def summarize_graph(graph: nx.DiGraph, *, top_k: int = 8) -> dict:
    """Return deterministic graph-health and note-importance metrics.

    Ranking runs on existing Markdown notes and explicit links only, keeping
    AI suggestions from inflating a note's explicit-link authority score.
    """
    if top_k < 0:
        raise ValueError("top_k cannot be negative.")

    notes = [
        node for node, data in graph.nodes(data=True)
        if data.get("exists", True)
    ]
    note_graph = nx.DiGraph()
    note_graph.add_nodes_from(notes)
    for source, target, data in graph.edges(data=True):
        if data.get("explicit") and source in note_graph and target in note_graph:
            note_graph.add_edge(source, target)

    explicit_count = sum(
        1 for _, _, data in graph.edges(data=True) if data.get("explicit")
    )
    resolved_explicit_count = note_graph.number_of_edges()
    semantic_pairs = {
        frozenset((source, target))
        for source, target, data in graph.edges(data=True)
        if data.get("semantic")
    }
    missing_nodes = [
        node for node, data in graph.nodes(data=True)
        if not data.get("exists", True)
    ]
    unresolved_links = sum(
        1 for source, target in graph.edges()
        if source in note_graph and target in missing_nodes
        and graph.edges[source, target].get("explicit")
    )
    orphans = sorted(node for node in notes if note_graph.degree(node) == 0)
    reciprocal_pairs = sum(
        1 for source, target in note_graph.edges()
        if source < target and note_graph.has_edge(target, source)
    )
    possible_edges = len(notes) * max(0, len(notes) - 1)
    density = resolved_explicit_count / possible_edges if possible_edges else 0.0

    ranks = nx.pagerank(note_graph) if notes else {}
    ranked_notes = sorted(
        notes,
        key=lambda node: (-ranks.get(node, 0.0), str(node).casefold()),
    )[:top_k]
    top_notes = [
        {
            "id": node,
            "title": graph.nodes[node].get("label", node),
            "pagerank": ranks.get(node, 0.0),
            "in_degree": note_graph.in_degree(node),
            "out_degree": note_graph.out_degree(node),
        }
        for node in ranked_notes
    ]

    return {
        "note_count": len(notes),
        "graph_node_count": graph.number_of_nodes(),
        "explicit_wikilink_count": explicit_count,
        "resolved_explicit_wikilink_count": resolved_explicit_count,
        "semantic_connection_count": len(semantic_pairs),
        "unresolved_reference_count": len(missing_nodes),
        "unresolved_wikilink_count": unresolved_links,
        "orphan_count": len(orphans),
        "orphan_notes": [
            {"id": node, "title": graph.nodes[node].get("label", node)}
            for node in orphans
        ],
        "explicit_density": density,
        "reciprocal_wikilink_pair_count": reciprocal_pairs,
        "top_notes_by_pagerank": top_notes,
    }
