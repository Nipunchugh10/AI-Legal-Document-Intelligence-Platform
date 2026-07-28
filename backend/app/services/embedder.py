import logging
from typing import List
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

class EmbedderService:
    """Service to handle local embedding generation using ChromaDB's default ONNX all-MiniLM-L6-v2 model."""

    def __init__(self):
        # Initialize default local embedding function (SentenceTransformer/ONNX all-MiniLM-L6-v2)
        try:
            self.ef = embedding_functions.DefaultEmbeddingFunction()
            logger.info("Successfully initialized local ONNX embedding model.")
        except Exception as e:
            logger.error(f"Failed to initialize local ONNX embedding model: {e}")
            raise RuntimeError(f"Failed to initialize local ONNX embedding model: {e}")

    def embed_text(self, text: str) -> List[float]:
        """
        Generate local 384-dimensional embedding for a single string.
        """
        if not text:
            return [0.0] * 384
            
        try:
            # self.ef returns a list of embeddings
            response = self.ef([text])
            vector = response[0]
            if hasattr(vector, "tolist"):
                return vector.tolist()
            return [float(x) for x in vector]
        except Exception as e:
            raise RuntimeError(f"Failed to generate local embedding: {str(e)}")

    def embed_chunks(self, chunks: List[str], batch_size: int = 20) -> List[List[float]]:
        """
        Generates 384-dimensional embeddings for a list of string chunks.
        Performs batching for efficiency.
        """
        if not chunks:
            return []

        embeddings = []
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            try:
                response = self.ef(batch)
                for vector in response:
                    if hasattr(vector, "tolist"):
                        embeddings.append(vector.tolist())
                    else:
                        embeddings.append([float(x) for x in vector])
            except Exception as e:
                raise RuntimeError(f"Failed to generate local embeddings for chunk batch {i//batch_size + 1}: {str(e)}")

        return embeddings

# Singleton initialization
_embedder_service = None

def get_embedder_service() -> EmbedderService:
    """Returns a cached singleton instance of the EmbedderService."""
    global _embedder_service
    if _embedder_service is None:
        _embedder_service = EmbedderService()
    return _embedder_service
