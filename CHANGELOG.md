# Changelog

## 0.3.0

- Added deterministic K-Means topic colors based on cached local embeddings.
- Added Graph-RAG search with three semantic seed notes and explicit one-hop
  link context.
- Added `build` and `search` CLI subcommands.

## 0.2.0

- Added local MiniLM semantic links with an incremental embedding cache.
- Added graph health metrics, PageRank ranking, and a versioned JSON export.
- Added explicit-versus-semantic edge controls in the interactive graph.
- Added alias, heading, folder-qualified wikilinks, and default directory
  exclusions for common vault metadata and dependency folders.
- Added installable package metadata and a cross-version GitHub Actions smoke
  build.

## 0.1.0

- Added recursive Markdown parsing, directed wikilink graph construction, and
  a self-contained interactive HTML visualization.
