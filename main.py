"""Command-line interface for building and searching a Markdown graph."""

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from analytics import summarize_graph
from clustering import cluster_note_colors
from exporter import export_graph_json
from graph import build_graph
from parser import parse_markdown_directory
from search import search_graph
from semantic import DEFAULT_MODEL, find_semantic_links, get_note_embeddings
from visualizer import export_graph

VERSION = "0.3.0"
LOGGER = logging.getLogger(__name__)
DEFAULT_DIRECTORY = Path("demo_notes")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and search a local Markdown knowledge graph."
    )
    parser.add_argument(
        "--version", action="version", version=f"Second Brain Graph {VERSION}"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser(
        "build", help="embed, cluster, and render Markdown notes"
    )
    build.add_argument("directory", nargs="?", type=Path, default=DEFAULT_DIRECTORY)
    build.add_argument("--output", type=Path, default=Path("index.html"))
    build.add_argument("--json-output", type=Path)
    build.add_argument("--similarity-threshold", type=float, default=0.75, metavar="0..1")
    build.add_argument("--cache", type=Path)
    build.add_argument("--model", default=DEFAULT_MODEL)
    build.add_argument("--exclude-dir", action="append", default=None, metavar="NAME")
    build.add_argument(
        "--no-semantic",
        action="store_true",
        help="skip embeddings, clustering, and semantic links (for lightweight builds)",
    )

    search = commands.add_parser(
        "search", help="retrieve semantic seeds and linked context"
    )
    search.add_argument("query", help="text to search for")
    search.add_argument("--directory", type=Path, default=DEFAULT_DIRECTORY)
    search.add_argument("--cache", type=Path)
    search.add_argument("--model", default=DEFAULT_MODEL)
    search.add_argument("--exclude-dir", action="append", default=None, metavar="NAME")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the selected build or Graph-RAG retrieval command."""
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "build" and not 0.0 <= args.similarity_threshold <= 1.0:
        parser.error("--similarity-threshold must be between 0 and 1")

    root = args.directory.expanduser().resolve()
    cache_path = args.cache or root / ".second_brain" / "embeddings.json"
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    try:
        notes = parse_markdown_directory(root, exclude_dirs=args.exclude_dir or ())
        note_contents = {
            note.path.resolve().relative_to(root).as_posix(): note.content for note in notes
        }
        note_paths = {
            note.path.resolve().relative_to(root).as_posix(): note.path for note in notes
        }

        if args.command == "search":
            graph = build_graph(notes, root)
            result = search_graph(
                args.query,
                note_contents,
                note_paths,
                graph,
                cache_path=cache_path,
                model_name=args.model,
            )
            if not result.seeds:
                print("No non-empty notes are available to search.")
                return 0
            print("Seed notes (semantic similarity):")
            for note_id, score in result.seeds:
                title = graph.nodes[note_id].get("label", note_id)
                print(f"  {title} [{note_id}]  {score:.1%}")
                neighbors = result.context[note_id]
                if neighbors:
                    print("    Explicit-link context:")
                    for neighbor in neighbors:
                        title = graph.nodes[neighbor].get("label", neighbor)
                        print(f"      {title} [{neighbor}]")
                else:
                    print("    Explicit-link context: none")
            return 0

        if not notes:
            LOGGER.warning("No readable Markdown notes were found under %s", root)
        embeddings = {}
        semantic_links = []
        cluster_colors = {}
        if not args.no_semantic:
            embeddings = get_note_embeddings(
                note_contents,
                note_paths,
                cache_path=cache_path,
                model_name=args.model,
            )
            cluster_colors = cluster_note_colors(
                embeddings, note_ids=list(note_contents)
            )
            semantic_links = find_semantic_links(
                note_contents,
                note_paths,
                threshold=args.similarity_threshold,
                cache_path=cache_path,
                model_name=args.model,
                embeddings=embeddings,
            )

        graph = build_graph(
            notes, root, semantic_links=semantic_links, cluster_colors=cluster_colors
        )
        graph.graph["semantic_settings"] = {
            "enabled": not args.no_semantic,
            "model": args.model if not args.no_semantic else None,
            "similarity_threshold": (
                args.similarity_threshold if not args.no_semantic else None
            ),
        }
        output = export_graph(graph, args.output)
        json_output = export_graph_json(graph, args.json_output) if args.json_output else None
    except (
        NotADirectoryError,
        OSError,
        RuntimeError,
        ValueError,
        KeyError,
        ImportError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    summary = summarize_graph(graph)
    for warning in graph.graph.get("warnings", []):
        LOGGER.warning("%s", warning)
    print(
        f"Created {output}\n"
        f"  Notes: {summary['note_count']}\n"
        f"  Explicit wikilinks: {summary['explicit_wikilink_count']}\n"
        f"  Semantic connections: {summary['semantic_connection_count']}\n"
        f"  Unresolved references: {summary['unresolved_reference_count']}\n"
        f"  Orphan notes: {summary['orphan_count']}\n"
        f"  Explicit graph density: {summary['explicit_density']:.3f}"
    )
    if json_output:
        print(f"JSON export: {json_output}")
    if summary["top_notes_by_pagerank"]:
        print("Most central notes:")
        for item in summary["top_notes_by_pagerank"][:5]:
            print(f"  {item['title']} (PageRank {item['pagerank']:.3f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
