"""Embedding service for generating vector embeddings using Nomic model."""

import gc
import logging
from typing import List, Union

import psutil
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings using nomic-embed-text-v1.5 model.

    Features:
    - 768-dimensional embeddings
    - Adaptive batch sizing based on available RAM
    - Memory monitoring and garbage collection
    - Efficient batch processing
    """

    def __init__(
        self,
        model_name: str = "nomic-ai/nomic-embed-text-v1.5",
        min_batch_size: int = 8,
        max_batch_size: int = 128,
        memory_threshold_mb: int = 500,
    ):
        """Initialize the embedding service.

        Args:
            model_name: Name of the sentence-transformers model to use
            min_batch_size: Minimum batch size for processing
            max_batch_size: Maximum batch size for processing
            memory_threshold_mb: Memory threshold in MB for adaptive batching
        """
        self.model_name = model_name
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.memory_threshold_mb = memory_threshold_mb
        self.model = None
        self.embedding_dimension = 768  # nomic-embed-text-v1.5 dimension

        logger.info(f"Initializing EmbeddingService with model: {model_name}")

    def load_model(self) -> None:
        """Load the embedding model into memory."""
        if self.model is not None:
            logger.info("Model already loaded")
            return

        logger.info(f"Loading model: {self.model_name}")
        try:
            # trust_remote_code is required for nomic models
            self.model = SentenceTransformer(
                self.model_name,
                trust_remote_code=True
            )
            logger.info(f"Model loaded successfully. Embedding dimension: {self.embedding_dimension}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def get_available_memory_mb(self) -> float:
        """Get available system memory in MB.

        Returns:
            Available memory in megabytes
        """
        memory = psutil.virtual_memory()
        available_mb = memory.available / (1024 * 1024)
        return available_mb

    def calculate_batch_size(self) -> int:
        """Calculate optimal batch size based on available RAM.

        Returns:
            Optimal batch size between min_batch_size and max_batch_size
        """
        available_mb = self.get_available_memory_mb()

        # If we have plenty of memory, use max batch size
        if available_mb > 2 * self.memory_threshold_mb:
            return self.max_batch_size

        # If memory is tight, use min batch size
        if available_mb < self.memory_threshold_mb:
            return self.min_batch_size

        # Scale linearly between min and max based on available memory
        ratio = (available_mb - self.memory_threshold_mb) / self.memory_threshold_mb
        batch_size = int(self.min_batch_size + ratio * (self.max_batch_size - self.min_batch_size))

        # Clamp to min/max bounds
        return max(self.min_batch_size, min(self.max_batch_size, batch_size))

    def embed_texts(self, texts: Union[str, List[str]], batch_size: int = None) -> List[List[float]]:
        """Generate embeddings for one or more texts.

        Args:
            texts: Single text string or list of text strings
            batch_size: Optional batch size override. If None, uses adaptive sizing.

        Returns:
            List of embedding vectors (each vector is 768 dimensions)
        """
        # Ensure model is loaded
        if self.model is None:
            self.load_model()

        # Normalize input to list
        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            return []

        # Determine batch size
        if batch_size is None:
            batch_size = self.calculate_batch_size()

        logger.info(f"Generating embeddings for {len(texts)} texts with batch size {batch_size}")

        embeddings = []
        total_batches = (len(texts) + batch_size - 1) // batch_size

        for batch_idx in range(0, len(texts), batch_size):
            batch_texts = texts[batch_idx:batch_idx + batch_size]
            current_batch_num = (batch_idx // batch_size) + 1

            logger.debug(f"Processing batch {current_batch_num}/{total_batches} ({len(batch_texts)} texts)")

            # Generate embeddings for this batch
            batch_embeddings = self.model.encode(
                batch_texts,
                convert_to_numpy=True,
                show_progress_bar=False,
                normalize_embeddings=True  # Normalize for cosine similarity
            )

            # Convert numpy arrays to lists
            embeddings.extend([embedding.tolist() for embedding in batch_embeddings])

            # Memory management: garbage collect after each batch
            if current_batch_num < total_batches:
                gc.collect()

                # Log memory usage
                available_mb = self.get_available_memory_mb()
                logger.debug(f"Available memory after batch {current_batch_num}: {available_mb:.1f} MB")

        logger.info(f"Generated {len(embeddings)} embeddings successfully")
        return embeddings

    def embed_single(self, text: str) -> List[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (768 dimensions)
        """
        embeddings = self.embed_texts([text])
        return embeddings[0] if embeddings else []

    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this service.

        Returns:
            Embedding dimension (768 for nomic-embed-text-v1.5)
        """
        return self.embedding_dimension

    def unload_model(self) -> None:
        """Unload the model from memory to free resources."""
        if self.model is not None:
            logger.info("Unloading model from memory")
            self.model = None
            gc.collect()
            logger.info("Model unloaded successfully")
