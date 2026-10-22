"""Create cached, local semantic connections between Markdown notes.

The module only compares note content. It neither edits files nor calls a
remote embedding API; Sentence Transformers downloads the model once and runs
inference locally after that.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL = "all-MiniLM-L6-v2"
CACHE_VERSION = 1


@dataclass(frozen=True)
class SemanticLink:
    """A symmetric similarity relation, emitted once per note pair."""

    source: str
    target: str
    similarity: float


def find_semantic_links(
    note_contents: Mapping[str, str],
    note_paths: Mapping[str, Path],
    *,
    threshold: float = 0.75,
    cache_path: Path = Path(".second_brain/embeddings.json"),
    model_name: str = DEFAULT_MODEL,
    batch_size: int = 32,
) -> list[SemanticLink]:
    """Embed changed notes and return pairs whose cosine score meets threshold.

    ``note_contents`` and ``note_paths`` use the same stable note IDs. A cache
    entry is reused only when the model, file timestamp, file size, and content
    digest match, so edits are caught even on filesystems with coarse clocks.
    Empty notes are skipped because their embeddings carry no useful meaning.
    """
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("Similarity threshold must be between 0 and 1.")
    if batch_size < 1:
        raise ValueError("batch_size must be a positive integer.")

    # Normalize and sort keys so pair order and cache writes are deterministic.
    contents = {
        str(note_id): content
        for note_id, content in sorted(note_contents.items(), key=lambda item: item[0])
        if isinstance(content, str) and content.strip()
    }
    if not contents:
        _write_cache(cache_path, model_name, {})
        return []

    # Keep importing the parser and graph builder lightweight when users run
    # with --no-semantic. NumPy is needed only for actual vector operations.
    try:
        import numpy as np
    except ImportError as error:
        raise RuntimeError(
            "Semantic linking needs NumPy. Install project dependencies with: "
            "python -m pip install -r requirements.txt"
        ) from error

    cache = _read_cache(cache_path, model_name)
    cached_notes: dict[str, dict] = cache["notes"]
    fingerprints: dict[str, dict] = {}
    vectors: dict[str, np.ndarray] = {}
    changed_ids: list[str] = []

    for note_id, content in contents.items():
        path = note_paths.get(note_id)
        if path is None:
            raise KeyError(f"No Markdown file path supplied for note {note_id!r}.")
        fingerprint = _fingerprint(Path(path), content)
        fingerprints[note_id] = fingerprint
        cached = cached_notes.get(note_id)
        if cached and cached.get("fingerprint") == fingerprint:
            try:
                vector = np.asarray(cached["embedding"], dtype=np.float32)
                if vector.ndim == 1 and vector.size and np.isfinite(vector).all():
                    vectors[note_id] = _normalize(vector)
                    continue
            except (KeyError, TypeError, ValueError):
                pass
        changed_ids.append(note_id)

    if changed_ids:
        # Delay importing the heavyweight ML stack until embeddings are needed.
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise RuntimeError(
                "Semantic linking needs sentence-transformers. Install project "
                "dependencies with: python -m pip install -r requirements.txt"
            ) from error

        model = SentenceTransformer(model_name)
        encoded = model.encode(
            [contents[note_id] for note_id in changed_ids],
            batch_size=batch_size,
            show_progress_bar=len(changed_ids) > batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        encoded = np.asarray(encoded, dtype=np.float32)
        if encoded.ndim == 1:
            encoded = encoded.reshape(1, -1)
        if encoded.shape[0] != len(changed_ids):
            raise RuntimeError("Embedding model returned an unexpected number of vectors.")
        if not np.isfinite(encoded).all():
            raise RuntimeError("Embedding model returned non-finite values.")
        for note_id, vector in zip(changed_ids, encoded):
            vectors[note_id] = _normalize(vector)

    # Persist only current files, dropping stale cache entries for deleted notes.
    cache_notes = {
        note_id: {
            "fingerprint": fingerprints[note_id],
            "embedding": vectors[note_id].astype(float).tolist(),
        }
        for note_id in contents
    }
    _write_cache(cache_path, model_name, cache_notes)

    # Since each vector is normalized, a dot product is cosine similarity.
    # Compare one row at a time to avoid allocating an N-by-N matrix.
    note_ids = list(contents)
    semantic_links: list[SemanticLink] = []
    for left_index, source in enumerate(note_ids[:-1]):
        left = vectors[source]
        for target in note_ids[left_index + 1 :]:
            right = vectors[target]
            if left.shape != right.shape:
                raise RuntimeError(
                    "Cached embedding dimensions do not match. Clear the embedding cache."
                )
            score = float(np.clip(np.dot(left, right), -1.0, 1.0))
            if score >= threshold:
                semantic_links.append(
                    SemanticLink(source=source, target=target, similarity=score)
                )
    return semantic_links


def _fingerprint(path: Path, content: str) -> dict[str, int | float | str]:
    """Return a cheap-to-check file signature plus a collision-resistant digest."""
    try:
        stat = path.stat()
    except OSError as error:
        raise OSError(f"Cannot inspect Markdown file for semantic cache: {path}") from error
    return {
        "mtime": os.path.getmtime(path),
        "mtime_ns": stat.st_mtime_ns,
        "size": stat.st_size,
        "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
    }


def _normalize(vector):
    """Normalize a vector and safely map a zero vector to zeros."""
    import numpy as np

    vector = np.asarray(vector, dtype=np.float32)
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        return vector
    return vector / norm


def _read_cache(cache_path: Path, model_name: str) -> dict:
    """Load a compatible JSON cache; treat missing/corrupt files as empty."""
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        if (
            payload.get("version") == CACHE_VERSION
            and payload.get("model") == model_name
            and isinstance(payload.get("notes"), dict)
        ):
            return payload
    except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
        pass
    return {"version": CACHE_VERSION, "model": model_name, "notes": {}}


def _write_cache(cache_path: Path, model_name: str, notes: dict) -> None:
    """Write JSON atomically so an interrupted run cannot corrupt the cache."""
    cache_path = cache_path.expanduser().resolve()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": CACHE_VERSION,
        "model": model_name,
        "notes": notes,
    }
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=cache_path.parent,
            prefix=f"{cache_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_name = temporary_file.name
            json.dump(payload, temporary_file, ensure_ascii=False, separators=(",", ":"))
        os.replace(temporary_name, cache_path)
    finally:
        if temporary_name and os.path.exists(temporary_name):
            os.unlink(temporary_name)
