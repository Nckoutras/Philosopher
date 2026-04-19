from openai import AsyncOpenAI
from config import config

_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)


class EmbeddingClient:

    async def embed(self, text: str) -> list[float]:
        text = text.replace("\n", " ").strip()[:8000]
        response = await _client.embeddings.create(
            input=text,
            model=config.EMBEDDING_MODEL,
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        cleaned = [t.replace("\n", " ").strip()[:8000] for t in texts]
        response = await _client.embeddings.create(
            input=cleaned,
            model=config.EMBEDDING_MODEL,
        )
        return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]


embedding_client = EmbeddingClient()
