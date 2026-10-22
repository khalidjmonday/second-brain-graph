"""Command-line entry point for the Markdown knowledge graph generator."""

import argparse
import logging
from pathlib import Path
import sys
from collections.abc import Sequence

from analytics import summarize_graph
from exporter import export_graph_json
from graph import build_graph
from parser import parse_markdown_directory
from semantic import DEFAULT_MODEL, find_semantic_links
from visualizer import export_graph

VERSION = "0.2.0"


def main(argv: Sequence[str] | None = None) -> int:
    """Parse command-line arguments and build the interactive graph."""
    argument_parser = argparse.ArgumentParser(
        description=(
            "Generate an interactive Markdown knowledge graph with explicit "
            "wikilinks and optional local semantic suggestions."
        )
    )
    argument_parser.add_argument(
        "directory",
        type=Path,
        help="Directory to scan recursively for .md files.",
    )
    argument_parser.add_argument(
        "--version",
        action="version",
        version=f"Second Brain Graph {VERSION}",
    )
    argument_parser.add_argument(
        "--output",
        type=Path,
        default=Path("index.html"),
        help="HTML output path (default: index.html).",
    )
    argument_parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.75,
        metavar="0..1",
        help="Minimum cosine similarity for an AI link (default: 0.75).",
    )
    argument_parser.add_argument(
        "--cache",
        type=Path,
        help="Embedding cache path (default: <vault>/.second_brain/embeddings.json).",
    )
    argument_parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Sentence Transformers model ID or local model directory (default: {DEFAULT_MODEL}).",
    )
    argument_parser.add_argument(
        "--exclude-dir",
        action="append",
        default=None,
        metavar="NAME",
        help="Directory name to skip; repeat for multiple names. Several cache and VCS folders are excluded by default.",
    )
    argument_parser.add_argument(
        "--no-semantic",
        action="store_true",
        help="Build only explicit wikilinks without loading the embedding model.",
    )
    argument_parser.add_argument(
        "--json-output",
        type=Path,
        help="Also export the graph and analytics as JSON.",
    )
    args = argument_parser.parse_args(argv)
    if not 0.0 <= args.similarity_threshold <= 1.0:
        argument_parser.error("--similarity-threshold must be between 0 and 1")

    root = args.directory.expanduser().resolve()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    try:
        notes = parse_markdown_directory(root, exclude_dirs=args.exclude_dir or ())
    except (NotADirectoryError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if not notes:
        logging.warning("No readable Markdown notes were found under %s", root)
    semantic_links = []
    if not args.no_semantic:
        note_contents = {
            note.path.resolve().relative_to(root).as_posix(): note.content
            for note in notes
        }
        note_paths = {
            note.path.resolve().relative_to(root).as_posix(): note.path
            for note in notes
        }
        cache_path = args.cache or root / ".second_brain" / "embeddings.json"
        try:
            semantic_links = find_semantic_links(
                note_contents,
                note_paths,
                threshold=args.similarity_threshold,
                cache_path=cache_path,
                model_name=args.model,
            )
        except (RuntimeError, OSError, ValueError, KeyError) as error:
            print(f"error: semantic analysis failed: {error}", file=sys.stderr)
            return 2
    graph = build_graph(notes, root, semantic_links=semantic_links)
    graph.graph["semantic_settings"] = {
        "enabled": not args.no_semantic,
        "model": (
            Path(args.model).name if Path(args.model).exists() else args.model
        ) if not args.no_semantic else None,
        "similarity_threshold": (
            args.similarity_threshold if not args.no_semantic else None
        ),
    }
    try:
        output = export_graph(graph, args.output)
        json_output = export_graph_json(graph, args.json_output) if args.json_output else None
    except OSError as error:
        print(f"error: could not write output: {error}", file=sys.stderr)
        return 2

    summary = summarize_graph(graph)
    for warning in graph.graph.get("warnings", []):
        logging.warning("%s", warning)
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
