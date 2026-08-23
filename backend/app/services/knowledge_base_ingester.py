import os
import logging
from app.services.chunker import chunk_text
from app.services.embedder import get_embedder_service
from app.services.vector_store import get_vector_store_service

logger = logging.getLogger(__name__)

# Configure basic logging to see progress when run directly
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def ingest_knowledge_base() -> bool:
    """
    Reads markdown documents from the knowledge_base directory,
    chunks them, generates embeddings, and saves them to ChromaDB.
    """
    kb_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "knowledge_base"))
    if not os.path.exists(kb_dir):
        logger.error(f"Knowledge base directory not found at: {kb_dir}")
        return False

    vector_store = get_vector_store_service()
    embedder = get_embedder_service()

    # Clear previous knowledge base entries to ensure a fresh ingest
    logger.info("Clearing previous legal knowledge base collection...")
    try:
        vector_store.delete_all_knowledge()
    except Exception as e:
        logger.warning(f"Could not clear collection: {e}")

    files = [f for f in os.listdir(kb_dir) if f.endswith(".md")]
    if not files:
        logger.warning("No markdown files found in the knowledge base directory.")
        return False

    logger.info(f"Found {len(files)} files to ingest: {files}")

    for filename in files:
        filepath = os.path.join(kb_dir, filename)
        document_name = os.path.splitext(filename)[0]

        # Determine category based on filename prefix
        if "dpdp" in document_name:
            category = "dpdp"
        elif "contract_act" in document_name:
            category = "indian_contract_act"
        elif "service" in document_name:
            category = "service_agreement"
        elif "nda" in document_name:
            category = "nda"
        else:
            category = "general"

        logger.info(f"Ingesting {filename} as category '{category}'...")

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Split into chunks (default 1000 size, 200 overlap)
            chunks = chunk_text(content)
            if not chunks:
                logger.warning(f"No text extracted or chunked from {filename}. Skipping.")
                continue

            logger.info(f"Generated {len(chunks)} chunks for {filename}.")

            # Generate embeddings
            # Generate embeddings in batch to minimize API requests and avoid rate limits (15 RPM)
            logger.info(f"Generating embeddings for {len(chunks)} chunks in batch...")
            embeddings = embedder.embed_chunks(chunks)

            # Store in ChromaDB
            vector_store.add_knowledge_chunks(
                document_name=document_name,
                category=category,
                chunks=chunks,
                embeddings=embeddings
            )
            logger.info(f"Successfully ingested {filename} into vector store.")

        except Exception as e:
            logger.error(f"Error ingesting {filename}: {e}", exc_info=True)
            return False

    logger.info("Knowledge base ingestion complete!")
    return True

if __name__ == "__main__":
    ingest_knowledge_base()
