import chromadb
from app.core.config import get_settings
from app.services.embedder import get_embedder_service
from typing import List, Dict, Any, Optional

class VectorStoreService:
    """Service to handle vector database operations using local ChromaDB client."""

    def __init__(self):
        self.settings = get_settings()
        self.embedder = get_embedder_service()
        
        # Initialize local persistent client pointing to the configured directory
        self.client = chromadb.PersistentClient(path=self.settings.CHROMA_PERSIST_DIR)
        
        # Get or create the core collection for storing contract text chunks
        self.collection = self.client.get_or_create_collection(
            name="contract_chunks",
            metadata={"hnsw:space": "cosine"}
        )

        # Get or create the collection for storing legal knowledge chunks (Day 24)
        self.knowledge_collection = self.client.get_or_create_collection(
            name="legal_knowledge",
            metadata={"hnsw:space": "cosine"}
        )

    def add_contract_chunks(
        self,
        contract_id: int,
        chunks: List[str],
        embeddings: List[List[float]],
    ) -> None:
        """
        Store a batch of contract text chunks and their pre-computed embeddings in ChromaDB.
        Adds metadata fields to allow filtering by contract_id and tracking chunk index.
        """
        if not chunks or not embeddings:
            return
        
        if len(chunks) != len(embeddings):
            raise ValueError("The number of chunks must match the number of embeddings.")

        ids = [f"contract_{contract_id}_chunk_{idx}" for idx in range(len(chunks))]
        metadatas = [{"contract_id": contract_id, "chunk_index": idx} for idx in range(len(chunks))]

        # Add to collection
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas
        )

    def delete_contract_chunks(self, contract_id: int) -> None:
        """
        Delete all text chunks and embeddings associated with a specific contract ID.
        This is crucial for cleanup when deleting a contract or re-ingesting it.
        """
        self.collection.delete(where={"contract_id": contract_id})

    def query_contract_chunks(
        self,
        contract_id: int,
        query_text: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Perform a semantic similarity search across a specific contract's chunks.
        Generates the query embedding, applies contract_id metadata filtering,
        and returns a sorted list of matching chunks with similarity scores.
        """
        # 1. Generate query embedding
        query_embedding = self.embedder.embed_text(query_text)

        # 2. Query collection with a metadata filter to isolate this user's contract
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where={"contract_id": contract_id}
        )

        # 3. Format results into list of dictionaries
        formatted_results = []
        if results and "documents" in results and results["documents"]:
            # Chroma returns nested lists since we can pass multiple query embeddings
            documents = results["documents"][0]
            ids = results["ids"][0]
            metadatas = results["metadatas"][0]
            # Distances represent cosine distance (lower is closer/more similar)
            distances = results["distances"][0] if "distances" in results else [0.0] * len(documents)

            for idx in range(len(documents)):
                formatted_results.append({
                    "id": ids[idx],
                    "text": documents[idx],
                    "chunk_index": metadatas[idx].get("chunk_index"),
                    "contract_id": metadatas[idx].get("contract_id"),
                    # Cosine similarity = 1 - cosine distance
                    "similarity": 1.0 - distances[idx]
                })

        return formatted_results

    def add_knowledge_chunks(
        self,
        document_name: str,
        category: str,
        chunks: List[str],
        embeddings: List[List[float]],
    ) -> None:
        """
        Store a batch of legal knowledge chunks and their pre-computed embeddings in ChromaDB.
        Adds metadata fields to allow filtering by category and document_name.
        """
        if not chunks or not embeddings:
            return
        
        if len(chunks) != len(embeddings):
            raise ValueError("The number of chunks must match the number of embeddings.")

        ids = [f"knowledge_{document_name}_chunk_{idx}" for idx in range(len(chunks))]
        metadatas = [{"document_name": document_name, "category": category, "chunk_index": idx} for idx in range(len(chunks))]

        self.knowledge_collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas
        )

    def delete_knowledge_by_document(self, document_name: str) -> None:
        """Delete all chunks and embeddings associated with a specific knowledge document."""
        self.knowledge_collection.delete(where={"document_name": document_name})

    def delete_all_knowledge(self) -> None:
        """Delete all records in the legal_knowledge collection."""
        self.client.delete_collection(name="legal_knowledge")
        self.knowledge_collection = self.client.get_or_create_collection(
            name="legal_knowledge",
            metadata={"hnsw:space": "cosine"}
        )

    def query_knowledge(
        self,
        query_text: str,
        category: Optional[str] = None,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Perform a similarity search across the legal knowledge collection.
        Optionally filters results by category.
        """
        query_embedding = self.embedder.embed_text(query_text)

        where_filter = {}
        if category:
            where_filter = {"category": category}

        results = self.knowledge_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter if where_filter else None
        )

        formatted_results = []
        if results and "documents" in results and results["documents"]:
            documents = results["documents"][0]
            ids = results["ids"][0]
            metadatas = results["metadatas"][0]
            distances = results["distances"][0] if "distances" in results else [0.0] * len(documents)

            for idx in range(len(documents)):
                formatted_results.append({
                    "id": ids[idx],
                    "text": documents[idx],
                    "chunk_index": metadatas[idx].get("chunk_index"),
                    "category": metadatas[idx].get("category"),
                    "document_name": metadatas[idx].get("document_name"),
                    "similarity": 1.0 - distances[idx]
                })

        return formatted_results

# Singleton initialization
_vector_store_service = None

def get_vector_store_service() -> VectorStoreService:
    """Returns a cached singleton instance of the VectorStoreService."""
    global _vector_store_service
    if _vector_store_service is None:
        _vector_store_service = VectorStoreService()
    return _vector_store_service
