"""OpenAI embedding generation for semantic search."""

from typing import Optional

from ..config import get_openai_settings


class Embedder:
    """OpenAI embeddings for semantic search."""

    MODEL = "text-embedding-ada-002"
    DIMENSION = 1536

    def __init__(self):
        """Initialize the embedder."""
        self._client = None

    @property
    def client(self):
        """Lazy-load OpenAI client."""
        if self._client is None:
            settings = get_openai_settings()
            if not settings.api_key:
                raise ValueError(
                    "OPENAI_API_KEY environment variable is required for semantic search"
                )
            from openai import OpenAI
            self._client = OpenAI(api_key=settings.api_key)
        return self._client

    def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        response = self.client.embeddings.create(
            model=self.MODEL,
            input=text,
        )
        return response.data[0].embedding

    def embed_batch(self, texts: list[str], batch_size: int = 100) -> list[list[float]]:
        """Generate embeddings for multiple texts in batches.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call (max 2048 for ada-002)

        Returns:
            List of embeddings in same order as input texts
        """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = self.client.embeddings.create(
                model=self.MODEL,
                input=batch,
            )
            # Sort by index to maintain order
            sorted_data = sorted(response.data, key=lambda x: x.index)
            all_embeddings.extend([d.embedding for d in sorted_data])

        return all_embeddings

    def is_available(self) -> bool:
        """Check if OpenAI embeddings are available."""
        settings = get_openai_settings()
        return settings.api_key is not None


def get_embedder() -> Optional[Embedder]:
    """Get embedder if OpenAI API key is available."""
    embedder = Embedder()
    if embedder.is_available():
        return embedder
    return None
