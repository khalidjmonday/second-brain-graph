"""Group note embeddings into topic clusters and assign display colors."""

from collections.abc import Mapping

CLUSTER_COLORS = ("#38BDF8", "#2DD4BF", "#FB7185", "#FBBF24", "#A3E635")
UNCLUSTERED_COLOR = "#94A3B8"


def cluster_note_colors(
    embeddings: Mapping[str, object], note_ids: list[str] | None = None
) -> dict[str, str]:
    """Map note IDs to colors using K-Means over their embedding vectors."""
    all_note_ids = sorted(note_ids if note_ids is not None else embeddings)
    if not embeddings:
        return {note_id: UNCLUSTERED_COLOR for note_id in all_note_ids}

    import numpy as np
    from sklearn.cluster import KMeans

    embedded_ids = sorted(embeddings)
    vectors = np.asarray([embeddings[note_id] for note_id in embedded_ids], dtype=np.float32)
    if vectors.ndim != 2 or not np.isfinite(vectors).all():
        raise ValueError("Note embeddings must be finite, equally sized vectors.")

    # K-Means minimizes within-cluster squared distance to a centroid; cap k
    # at five and at the number of notes so small vaults remain valid.
    unique_count = np.unique(vectors, axis=0).shape[0]
    cluster_count = min(len(embedded_ids), unique_count, len(CLUSTER_COLORS))
    labels = KMeans(n_clusters=cluster_count, random_state=42, n_init=10).fit_predict(
        vectors
    )
    colors = {
        note_id: CLUSTER_COLORS[int(cluster_id)]
        for note_id, cluster_id in zip(embedded_ids, labels)
    }
    colors.update(
        (note_id, UNCLUSTERED_COLOR)
        for note_id in all_note_ids
        if note_id not in colors
    )
    return colors
