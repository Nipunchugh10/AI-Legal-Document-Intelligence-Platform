"""
Embeddings and Vector Database Integration Tests
------------------------------------------------
Tests EmbedderService (text-embedding-004) and VectorStoreService (ChromaDB) end-to-end.
"""

import sys
import os
import shutil

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import get_settings
from app.services.embedder import get_embedder_service
from app.services.vector_store import get_vector_store_service

TEST_CHROMA_DIR = "./test_chroma_data"
TEST_CONTRACT_ID = 99999
TEST_CHUNKS = [
    "The Service Provider agrees to design and develop a fully functional e-commerce website for the Client's business.",
    "The total project fee is INR 85,000. Payment shall be made in three installments.",
    "The Service Provider agrees to keep confidential all information shared by the Client in connection with this project."
]

def setup_test_environment():
    """Overrides ChromaDB persist directory to avoid polluting development data."""
    settings = get_settings()
    # Set to test path
    settings.CHROMA_PERSIST_DIR = TEST_CHROMA_DIR
    # Clean up test dir if it exists
    if os.path.exists(TEST_CHROMA_DIR):
        shutil.rmtree(TEST_CHROMA_DIR)

def cleanup_test_environment():
    """Removes the test ChromaDB directory."""
    if os.path.exists(TEST_CHROMA_DIR):
        try:
            shutil.rmtree(TEST_CHROMA_DIR)
        except Exception as e:
            print(f"\n[!] Note: Could not completely remove test directory {TEST_CHROMA_DIR} due to file locks: {e}")

def test_embedder_service():
    """Verify that EmbedderService returns 768-dimension vectors using Google GenAI API."""
    embedder = get_embedder_service()
    
    # 1. Single text embedding
    vector = embedder.embed_text("Hello legal AI platform")
    assert isinstance(vector, list)
    assert len(vector) == 768
    assert all(isinstance(val, float) for val in vector)

    # 2. Batch chunk embedding
    vectors = embedder.embed_chunks(["Chunk number one", "Chunk number two"])
    assert isinstance(vectors, list)
    assert len(vectors) == 2
    assert len(vectors[0]) == 768
    assert len(vectors[1]) == 768

def test_vector_store_operations():
    """Verify storing, querying, and deleting chunks from ChromaDB."""
    embedder = get_embedder_service()
    vector_store = get_vector_store_service()

    # Generate test embeddings
    embeddings = embedder.embed_chunks(TEST_CHUNKS)

    # 1. Add chunks to ChromaDB
    vector_store.add_contract_chunks(
        contract_id=TEST_CONTRACT_ID,
        chunks=TEST_CHUNKS,
        embeddings=embeddings
    )

    # 2. Query contract chunks (semantic search)
    # Search for payment-related chunk
    query_results = vector_store.query_contract_chunks(
        contract_id=TEST_CONTRACT_ID,
        query_text="How much is the cost or payment fee?",
        n_results=1
    )

    assert len(query_results) == 1
    result = query_results[0]
    assert result["contract_id"] == TEST_CONTRACT_ID
    assert "project fee" in result["text"]
    assert result["similarity"] > 0.0  # Cosine similarity is positive for related text

    # Search for confidentiality chunk
    query_results_conf = vector_store.query_contract_chunks(
        contract_id=TEST_CONTRACT_ID,
        query_text="confidential non-disclosure terms",
        n_results=1
    )
    assert "confidential" in query_results_conf[0]["text"]

    # 3. Check isolation: search under a different contract ID
    isolated_results = vector_store.query_contract_chunks(
        contract_id=11111,
        query_text="payment fee",
        n_results=1
    )
    assert len(isolated_results) == 0

    # 4. Delete contract chunks
    vector_store.delete_contract_chunks(contract_id=TEST_CONTRACT_ID)

    # Verify query returns empty results
    post_delete_results = vector_store.query_contract_chunks(
        contract_id=TEST_CONTRACT_ID,
        query_text="project fee",
        n_results=1
    )
    assert len(post_delete_results) == 0


if __name__ == "__main__":
    print("=" * 70)
    print(" Running Embedder and Vector Store Test Suite")
    print("=" * 70)

    try:
        setup_test_environment()

        print("[*] Running: test_embedder_service...")
        test_embedder_service()
        print("[+] Success!")

        print("[*] Running: test_vector_store_operations...")
        test_vector_store_operations()
        print("[+] Success!")

        cleanup_test_environment()
        print("\n" + "=" * 70)
        print(" ALL EMBEDDER & VECTOR STORE TESTS PASSED! [OK]")
        print("=" * 70)
    except AssertionError as e:
        import traceback
        print(f"\n[-] TEST ASSERTION FAILURE:")
        traceback.print_exc()
        cleanup_test_environment()
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"\n[-] TEST ERROR:")
        traceback.print_exc()
        cleanup_test_environment()
        sys.exit(1)
