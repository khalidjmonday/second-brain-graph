"""Retrieve semantically relevant notes and their explicit-link context."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import networkx as nx

from semantic import DEFAULT_MODEL, get_note_embeddings


@dataclass(frozen=True)
class SearchResult:
    """Nearest note seeds and their explicit first-degree context."""

    seeds: tuple[tuple[str, float], ...]
    context: Mapping[str, tuple[str, ...]]


def search_graph(
    query: str,
    note_contents: Mapping[str, str],
    note_paths: Mapping[str, Path],
    graph: nx.DiGraph,
    *,
    cache_path: Path,
    model_name: str = DEFAULT_MODEL,
    top_k: int = 3,
) -> SearchResult:
    """Find top semantic seeds, then gather each seed's explicit neighbors."""
    if not query.strip():
        raise ValueError("Search query cannot be empty.")
    if top_k < 1:
        raise ValueError("top_k must be a positive integer.")
    if not any(
        isinstance(text, str) and text.strip() for text in note_contents.values()
    ):
        return SearchResult(seeds=(), context={})

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise RuntimeError(
            "Graph search needs sentence-transformers. Install dependencies with: "
            "python -m pip install -r requirements.txt"
        ) from error
    import numpy as np

    # Reuse one local model instance for changed notes and the query vector.
    model = SentenceTransformer(model_name)
    embeddings = get_note_embeddings(
        note_contents,
        note_paths,
        cache_path=cache_path,
        model_name=model_name,
        model=model,
    )
    if not embeddings:
        return SearchResult(seeds=(), context={})

    query_vector = np.asarray(
        model.encode(query, convert_to_numpy=True, normalize_embeddings=True),
        dtype=np.float32,
    ).reshape(-1)
    scores = []
    for note_id, vector in embeddings.items():
        if vector.shape != query_vector.shape:
            raise RuntimeError("Query and note embedding dimensions do not match.")
        scores.append((note_id, float(np.dot(query_vector, vector))))
    seeds = tuple(sorted(scores, key=lambda item: (-item[1], item[0]))[:top_k])

    context: dict[str, tuple[str, ...]] = {}
    for seed_id, _ in seeds:
        # A DiGraph's neighbors() gives successors only. Check both incoming
        # and outgoing explicit edges to retrieve the full one-hop neighborhood.
        neighbors = set(graph.successors(seed_id)) | set(graph.predecessors(seed_id))
        context[seed_id] = tuple(
            sorted(
                neighbor
                for neighbor in neighbors
                if graph.nodes[neighbor].get("exists", True)
                and (
                    (
                        graph.has_edge(seed_id, neighbor)
                        and graph.edges[seed_id, neighbor].get("explicit", False)
                    )
                    or (
                        graph.has_edge(neighbor, seed_id)
                        and graph.edges[neighbor, seed_id].get("explicit", False)
                    )
                )
            )
        )
    return SearchResult(seeds=seeds, context=context)
