from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import asyncio


class QdrantRepository:
    def __init__(self, url: str = "http://localhost:6333", model_name: str = "all-MiniLM-L6-v2"):
        self.qdrant_client = QdrantClient(
            url=url
        )
        self.model = SentenceTransformer(model_name)

    def similarity_search(self, collection_name: str, search_query: str, limit: int = 10):
        """Realiza una búsqueda de similitud en Qdrant."""
        query_vector = self._encode_query(search_query)
        results = self.qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit
        )
        return results

    async def similarity_search_async(self, collection_name: str, search_query: str, limit: int = 10):
        """Versión asíncrona de similarity_search usando un hilo para no bloquear el bucle de eventos."""
        return await asyncio.to_thread(self.similarity_search, collection_name, search_query, limit)
    
    def _encode_query(self, query: str):
        """Convierte una consulta de texto a un vector para búsqueda."""
        return self.model.encode(query).tolist()