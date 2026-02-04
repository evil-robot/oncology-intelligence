"""
Clustering pipeline using UMAP for dimensionality reduction and HDBSCAN for clustering.

Transforms high-dimensional embeddings into 3D coordinates for visualization
and groups semantically similar terms into clusters.
"""

import logging
from typing import Optional
from dataclasses import dataclass

import numpy as np
import umap
import hdbscan
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


@dataclass
class ClusteringResult:
    """Result of the clustering pipeline."""

    # 3D coordinates for each input
    coordinates: np.ndarray  # Shape: (n_samples, 3)

    # Cluster assignments (-1 = noise/outlier)
    labels: np.ndarray  # Shape: (n_samples,)

    # Cluster centroids in 3D space
    centroids: dict[int, np.ndarray]  # cluster_id -> (3,) array

    # Cluster membership probabilities
    probabilities: Optional[np.ndarray] = None

    # Number of clusters found (excluding noise)
    n_clusters: int = 0


class ClusteringPipeline:
    """Pipeline for dimensionality reduction and clustering of embeddings."""

    def __init__(
        self,
        n_components: int = 3,
        n_neighbors: int = 10,
        min_dist: float = 0.5,  # Increased for more spread
        min_cluster_size: int = 5,
        min_samples: int = 3,
        metric: str = "cosine",
        random_state: int = 42,
        spread: float = 2.0,  # Added for more spread
    ):
        """
        Initialize clustering pipeline.

        Args:
            n_components: Output dimensions (3 for visualization)
            n_neighbors: UMAP neighborhood size (larger = more global structure)
            min_dist: UMAP minimum distance (smaller = tighter clusters)
            min_cluster_size: HDBSCAN minimum cluster size
            min_samples: HDBSCAN minimum samples for core points
            metric: Distance metric for both UMAP and HDBSCAN
            random_state: Random seed for reproducibility
        """
        self.n_components = n_components
        self.random_state = random_state

        self.reducer = umap.UMAP(
            n_components=n_components,
            n_neighbors=n_neighbors,
            min_dist=min_dist,
            spread=spread,
            metric=metric,
            random_state=random_state,
        )

        self.clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
            metric="euclidean",  # Use euclidean in reduced space
            cluster_selection_method="eom",
        )

        self.scaler = StandardScaler()

    def fit_transform(
        self,
        embeddings: np.ndarray,
        normalize: bool = True,
    ) -> ClusteringResult:
        """
        Run full clustering pipeline on embeddings.

        Args:
            embeddings: Array of shape (n_samples, embedding_dim)
            normalize: Whether to normalize embeddings before processing

        Returns:
            ClusteringResult with coordinates, labels, and centroids
        """
        logger.info(f"Clustering {len(embeddings)} embeddings")

        if len(embeddings) < 3:
            logger.warning("Too few embeddings for meaningful clustering")
            return ClusteringResult(
                coordinates=np.zeros((len(embeddings), 3)),
                labels=np.zeros(len(embeddings), dtype=int),
                centroids={0: np.zeros(3)},
                n_clusters=1,
            )

        # Normalize if requested
        if normalize:
            embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        # Dimensionality reduction
        logger.info("Running UMAP dimensionality reduction...")
        coordinates = self.reducer.fit_transform(embeddings)

        # Scale coordinates for visualization (centered, reasonable range)
        coordinates = self.scaler.fit_transform(coordinates)

        # Clustering
        logger.info("Running HDBSCAN clustering...")
        self.clusterer.fit(coordinates)
        labels = self.clusterer.labels_
        probabilities = self.clusterer.probabilities_

        # Compute centroids
        centroids = self._compute_centroids(coordinates, labels)

        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        logger.info(f"Found {n_clusters} clusters")

        return ClusteringResult(
            coordinates=coordinates,
            labels=labels,
            centroids=centroids,
            probabilities=probabilities,
            n_clusters=n_clusters,
        )

    def _compute_centroids(
        self,
        coordinates: np.ndarray,
        labels: np.ndarray,
    ) -> dict[int, np.ndarray]:
        """Compute centroid for each cluster."""
        centroids = {}
        unique_labels = set(labels)

        for label in unique_labels:
            if label == -1:  # Skip noise
                continue
            mask = labels == label
            cluster_coords = coordinates[mask]
            centroids[label] = np.mean(cluster_coords, axis=0)

        return centroids

    def assign_to_cluster(
        self,
        new_coordinates: np.ndarray,
        centroids: dict[int, np.ndarray],
    ) -> int:
        """
        Assign new point to nearest existing cluster.

        Args:
            new_coordinates: 3D coordinates of new point
            centroids: Existing cluster centroids

        Returns:
            Cluster ID of nearest cluster
        """
        if not centroids:
            return 0

        min_dist = float("inf")
        nearest_cluster = 0

        for cluster_id, centroid in centroids.items():
            dist = np.linalg.norm(new_coordinates - centroid)
            if dist < min_dist:
                min_dist = dist
                nearest_cluster = cluster_id

        return nearest_cluster

    def transform_new(
        self,
        new_embeddings: np.ndarray,
        normalize: bool = True,
    ) -> np.ndarray:
        """
        Transform new embeddings using fitted UMAP.

        Args:
            new_embeddings: New embeddings to transform
            normalize: Whether to normalize

        Returns:
            3D coordinates for new embeddings
        """
        if normalize:
            new_embeddings = new_embeddings / np.linalg.norm(
                new_embeddings, axis=1, keepdims=True
            )

        coordinates = self.reducer.transform(new_embeddings)
        return self.scaler.transform(coordinates)


# Predefined cluster colors for consistent visualization
CLUSTER_COLORS = [
    "#6366f1",  # Indigo
    "#ec4899",  # Pink
    "#14b8a6",  # Teal
    "#f59e0b",  # Amber
    "#8b5cf6",  # Violet
    "#ef4444",  # Red
    "#22c55e",  # Green
    "#3b82f6",  # Blue
    "#f97316",  # Orange
    "#06b6d4",  # Cyan
    "#a855f7",  # Purple
    "#84cc16",  # Lime
]


def get_cluster_color(cluster_id: int) -> str:
    """Get consistent color for a cluster ID."""
    if cluster_id < 0:
        return "#6b7280"  # Gray for noise/outliers
    return CLUSTER_COLORS[cluster_id % len(CLUSTER_COLORS)]


def generate_cluster_name(terms: list[str], top_n: int = 2) -> str:
    """
    Generate a short, descriptive name for a cluster based on its terms.

    Args:
        terms: List of terms in the cluster
        top_n: Number of terms to include in name

    Returns:
        Generated cluster name (max ~30 chars)
    """
    if not terms:
        return "Unknown"

    # Find common themes/words across terms
    word_counts: dict[str, int] = {}
    for term in terms:
        for word in term.lower().split():
            # Skip common words
            if word not in {'the', 'a', 'an', 'of', 'in', 'for', 'and', 'or', 'with', 'cancer', 'disease', 'syndrome'}:
                word_counts[word] = word_counts.get(word, 0) + 1

    # Get most common meaningful word
    if word_counts:
        top_word = max(word_counts.items(), key=lambda x: x[1])[0]
        # Find shortest term containing this word
        matching_terms = [t for t in terms if top_word in t.lower()]
        if matching_terms:
            best_term = min(matching_terms, key=len)
            if len(best_term) <= 25:
                return best_term.title()

    # Fallback: use shortest term
    shortest = min(terms, key=len)
    if len(shortest) > 25:
        shortest = shortest[:22] + "..."
    return shortest.title()
