import google.generativeai as genai
from app.core.config import get_settings
from typing import List

class EmbedderService:
    """Service to handle embedding generation using Google's text-embedding-004 model."""

    def __init__(self):
        self.settings = get_settings()
        if not self.settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")
        
        # Configure the generativeai library with the API key
        genai.configure(api_key=self.settings.GEMINI_API_KEY)
        # Using gemini-embedding-001 which is the 768-dimensional embedding model supported by our credentials
        self.model_name = "models/gemini-embedding-001"

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single string.
        Returns a list of 768 floats.
        """
        if not text:
            return [0.0] * 768
            
        try:
            response = genai.embed_content(
                model=self.model_name,
                content=text,
                task_type="retrieval_document",
                output_dimensionality=768
            )
            return response['embedding']
        except Exception as e:
            raise RuntimeError(f"Failed to generate embedding for text: {str(e)}")

    def embed_chunks(self, chunks: List[str], batch_size: int = 20) -> List[List[float]]:
        """
        Generates embeddings for a list of string chunks.
        Performs batching to prevent API size limit errors and stay resilient.
        Returns a list of float lists, each containing 768 elements.
        """
        if not chunks:
            return []

        embeddings = []
        # Batch requests to be resilient to large payloads or API restrictions
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            try:
                response = genai.embed_content(
                    model=self.model_name,
                    content=batch,
                    task_type="retrieval_document",
                    output_dimensionality=768
                )
                # response['embedding'] will be a list of lists of floats
                embeddings.extend(response['embedding'])
            except Exception as e:
                raise RuntimeError(f"Failed to generate embeddings for chunk batch {i//batch_size + 1}: {str(e)}")

        return embeddings

# Singleton initialization
_embedder_service = None

def get_embedder_service() -> EmbedderService:
    """Returns a cached singleton instance of the EmbedderService."""
    global _embedder_service
    if _embedder_service is None:
        _embedder_service = EmbedderService()
    return _embedder_service
