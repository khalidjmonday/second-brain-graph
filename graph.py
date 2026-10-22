"""Build a directed graph from parsed Markdown notes."""

from collections.abc import Iterable, Mapping
from pathlib import Path, PurePosixPath

import networkx as nx

from parser import MarkdownNote
from semantic import SemanticLink


def build_graph(
    notes: list[MarkdownNote],
    root: Path,
    semantic_links: Iterable[SemanticLink] = (),
    cluster_colors: Mapping[str, str] | None = None,
) -> nx.DiGraph:
    """Create a node for every note and a directed edge for every wikilink.

    Existing links resolve case-insensitively by note filename (without the
    ``.md`` extension). If multiple files have the same stem, the first path
    in sorted scan order is selected. Unresolved links become placeholder
    nodes with ``exists=False``, preserving references to future notes.
    """
    root = root.expanduser().resolve()
    graph = nx.DiGraph()

    # Filename lookup supports ordinary [[Note]] links. Relative-path lookup
    # lets duplicate note titles be targeted unambiguously with [[folder/Note]].
    notes_by_name: dict[str, Path] = {}
    notes_by_path: dict[str, Path] = {}
    paths_by_name: dict[str, list[Path]] = {}
    for note in notes:
        notes_by_name.setdefault(note.path.stem.casefold(), note.path)
        paths_by_name.setdefault(note.path.stem.casefold(), []).append(note.path)
        relative = _relative_id(note.path, root)
        notes_by_path[PurePosixPath(relative).with_suffix("").as_posix().casefold()] = note.path

    # Add all files first, including isolated notes that have no links.
    for note in notes:
        node_id = _relative_id(note.path, root)
        graph.add_node(
            node_id,
            label=note.path.stem,
            # Keep generated HTML and JSON portable and avoid leaking the
            # user's absolute filesystem location into shareable artifacts.
            path=node_id,
            exists=True,
            color=(cluster_colors or {}).get(node_id),
        )

    # Each directed edge means "source note links to destination note".
    # DiGraph naturally represents repeated links between a pair as one edge.
    for note in notes:
        source_id = _relative_id(note.path, root)
        for link_name in note.links:
            normalized_target = PurePosixPath(link_name).as_posix().casefold()
            target_key = (
                normalized_target.removesuffix(".md")
            )
            # Explicit paths win. A stem lookup remains the convenient default.
            target_path = notes_by_path.get(target_key) or notes_by_name.get(
                PurePosixPath(target_key).stem.casefold()
            )
            if "/" not in target_key and len(paths_by_name.get(target_key, ())) > 1:
                graph.graph.setdefault("warnings", []).append(
                    f"Ambiguous wikilink [[{link_name}]] from {source_id}; "
                    f"resolved to {notes_by_name[target_key].relative_to(root).as_posix()}. "
                    "Use a folder-qualified wikilink to choose a different note."
                )
            if target_path is None:
                # Prefix the ID to prevent collisions with real file paths.
                # casefold() also groups unresolved spelling variants together.
                target_id = f"missing:{target_key}"
                graph.add_node(
                    target_id,
                    label=PurePosixPath(link_name).stem,
                    exists=False,
                )
            else:
                target_id = _relative_id(target_path, root)
            graph.add_edge(source_id, target_id, explicit=True, semantic=False)

    # Similarity is symmetric. Store both directions in the DiGraph so the
    # visual network stays navigable, while retaining the one-pair score.
    # If a wikilink already occupies either directed edge, merge attributes;
    # the visualizer keeps that explicit edge solid and brightly colored.
    for link in semantic_links:
        if (
            link.source not in graph
            or link.target not in graph
            or not graph.nodes[link.source].get("exists", True)
            or not graph.nodes[link.target].get("exists", True)
        ):
            continue
        for source_id, target_id in (
            (link.source, link.target),
            (link.target, link.source),
        ):
            graph.add_edge(source_id, target_id)
            graph.edges[source_id, target_id].update(
                explicit=graph.edges[source_id, target_id].get("explicit", False),
                semantic=True,
                similarity=float(link.similarity),
            )

    return graph


def _relative_id(path: Path, root: Path) -> str:
    """Return a stable, portable ID relative to the scanned directory."""
    return path.resolve().relative_to(root).as_posix()
