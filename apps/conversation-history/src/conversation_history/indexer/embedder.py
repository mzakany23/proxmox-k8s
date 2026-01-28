"""OpenAI embedding generation."""

import asyncio
from typing import TYPE_CHECKING

from openai import AsyncOpenAI

from ..config import settings

if TYPE_CHECKING:
    pass


class Embedder:
    """Generates embeddings using OpenAI API."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.embedding_model
        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("OpenAI API key not configured")
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        response = await self.client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding

    async def embed_batch(
        self, texts: list[str], batch_size: int = 100
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts in batches."""
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = await self.client.embeddings.create(
                model=self.model,
                input=batch,
            )
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

            # Rate limiting - small delay between batches
            if i + batch_size < len(texts):
                await asyncio.sleep(0.1)

        return all_embeddings
