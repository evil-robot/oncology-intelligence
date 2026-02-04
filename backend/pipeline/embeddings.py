"""
Embedding generation using OpenAI's text-embedding-3-small.

Generates semantic embeddings for search terms and content to enable
clustering and similarity search.
"""

import logging
from typing import Optional
import numpy as np
from openai import OpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmbeddingGenerator:
    """Generate embeddings using OpenAI's embedding models."""

    def __init__(
        self,
        model: str = None,
        dimensions: int = None,
    ):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = model or settings.embedding_model
        self.dimensions = dimensions or settings.embedding_dimensions

    def embed_text(self, text: str) -> Optional[list[float]]:
        """
        Generate embedding for a single text string.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dimensions,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding for '{text[:50]}...': {e}")
            return None

    def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 100,
    ) -> list[Optional[list[float]]]:
        """
        Generate embeddings for multiple texts with batching.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call

        Returns:
            List of embeddings (None for failed items)
        """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            logger.info(f"Embedding batch {i // batch_size + 1}, size {len(batch)}")

            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                    dimensions=self.dimensions,
                )

                # Extract embeddings in order
                batch_embeddings = [None] * len(batch)
                for item in response.data:
                    batch_embeddings[item.index] = item.embedding

                all_embeddings.extend(batch_embeddings)

            except Exception as e:
                logger.error(f"Error embedding batch starting at {i}: {e}")
                all_embeddings.extend([None] * len(batch))

        return all_embeddings

    def embed_term_with_context(self, term: str, category: str = None) -> Optional[list[float]]:
        """
        Generate embedding for a search term with category context.

        Adding context improves embedding quality for short queries.

        Args:
            term: Search term
            category: Optional category for context

        Returns:
            Embedding vector
        """
        if category:
            contextualized = f"Pediatric oncology search query about {category}: {term}"
        else:
            contextualized = f"Pediatric oncology search query: {term}"

        return self.embed_text(contextualized)


def compute_centroid(embeddings: list[list[float]]) -> list[float]:
    """
    Compute centroid (mean) of multiple embeddings.

    Args:
        embeddings: List of embedding vectors

    Returns:
        Centroid embedding vector
    """
    if not embeddings:
        raise ValueError("Cannot compute centroid of empty list")

    arr = np.array(embeddings)
    centroid = np.mean(arr, axis=0)
    return centroid.tolist()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """
    Compute cosine similarity between two embeddings.

    Args:
        a: First embedding vector
        b: Second embedding vector

    Returns:
        Cosine similarity score (0-1)
    """
    a_arr = np.array(a)
    b_arr = np.array(b)

    dot_product = np.dot(a_arr, b_arr)
    norm_a = np.linalg.norm(a_arr)
    norm_b = np.linalg.norm(b_arr)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def find_nearest_cluster(
    embedding: list[float],
    cluster_centroids: dict[int, list[float]],
    threshold: float = 0.5,
) -> Optional[int]:
    """
    Find the nearest cluster for an embedding.

    Args:
        embedding: Embedding vector to classify
        cluster_centroids: Dict mapping cluster_id to centroid embedding
        threshold: Minimum similarity threshold

    Returns:
        Cluster ID or None if no cluster meets threshold
    """
    best_cluster = None
    best_similarity = threshold

    for cluster_id, centroid in cluster_centroids.items():
        similarity = cosine_similarity(embedding, centroid)
        if similarity > best_similarity:
            best_similarity = similarity
            best_cluster = cluster_id

    return best_cluster
