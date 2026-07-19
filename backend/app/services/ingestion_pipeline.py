import logging
from sqlalchemy.orm import Session
from app.models.contract import Contract
from app.models.analysis import Analysis
from app.services.pdf_extractor import extract_pdf_text
from app.services.chunker import chunk_text
from app.services.embedder import get_embedder_service
from app.services.vector_store import get_vector_store_service

logger = logging.getLogger(__name__)

async def ingest_contract(contract_id: int, db: Session) -> dict:
    """
    Executes the end-to-end contract ingestion pipeline:
    1. Extracts raw text from the contract PDF.
    2. Cleans and chunks the text into token-sized segments.
    3. Generates 768-dimensional embeddings for the chunks using Google GenAI.
    4. Persists the chunks and embeddings into the local ChromaDB vector database.
    5. Stores metadata and chunks in PostgreSQL for structured queries.
    6. Updates contract status to 'ingested' (or 'failed' if any step fails).
    """
    # 1. Retrieve contract
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        logger.error(f"Ingestion failed: Contract {contract_id} not found.")
        raise ValueError(f"Contract {contract_id} not found.")

    logger.info(f"[*] Starting ingestion pipeline for contract {contract_id} ({contract.filename})")
    
    # Update status to 'processing' to prevent concurrent ingestion runs
    contract.status = "processing"
    db.commit()

    try:
        # --- Step 1: Text Extraction ---
        logger.info(f"[*] Ingestion step 1/4: Extracting text from {contract.upload_path}")
        extracted = extract_pdf_text(contract.upload_path)
        raw_text = extracted.get("text", "")
        if not raw_text:
            raise ValueError("No text could be extracted from the PDF contract.")

        # Save raw text analysis record
        raw_analysis = db.query(Analysis).filter(
            Analysis.contract_id == contract_id,
            Analysis.analysis_type == "raw_text"
        ).first()

        raw_result_json = {
            "text": raw_text,
            "page_count": extracted.get("page_count", 0),
            "is_scanned": extracted.get("is_scanned", False),
            "strategy": extracted.get("strategy", "pymupdf")
        }

        if raw_analysis:
            raw_analysis.result_json = raw_result_json
        else:
            raw_analysis = Analysis(
                contract_id=contract_id,
                analysis_type="raw_text",
                result_json=raw_result_json
            )
            db.add(raw_analysis)
        db.commit()

        # --- Step 2: Text Chunking & Preprocessing ---
        logger.info("[*] Ingestion step 2/4: Chunking and preprocessing text")
        chunks = chunk_text(raw_text, chunk_size=1000, chunk_overlap=200)
        if not chunks:
            raise ValueError("Chunking resulted in 0 text chunks.")

        # Save chunk analysis record
        chunks_analysis = db.query(Analysis).filter(
            Analysis.contract_id == contract_id,
            Analysis.analysis_type == "chunks"
        ).first()

        chunks_result_json = {
            "chunk_count": len(chunks),
            "chunks": chunks,
            "chunk_size": 1000,
            "chunk_overlap": 200
        }

        if chunks_analysis:
            chunks_analysis.result_json = chunks_result_json
        else:
            chunks_analysis = Analysis(
                contract_id=contract_id,
                analysis_type="chunks",
                result_json=chunks_result_json
            )
            db.add(chunks_analysis)
        db.commit()

        # --- Step 3: Embedding Generation ---
        logger.info(f"[*] Ingestion step 3/4: Generating embeddings for {len(chunks)} chunks")
        embedder = get_embedder_service()
        embeddings = embedder.embed_chunks(chunks)

        # --- Step 4: Vector Store Persistence ---
        logger.info(f"[*] Ingestion step 4/4: Persisting chunks/embeddings to ChromaDB")
        vector_store = get_vector_store_service()
        
        # Clear out any stale embeddings for this contract first (makes pipeline idempotent)
        vector_store.delete_contract_chunks(contract_id)
        
        # Add new embeddings
        vector_store.add_contract_chunks(
            contract_id=contract_id,
            chunks=chunks,
            embeddings=embeddings
        )

        # --- Pipeline Completion ---
        contract.status = "ingested"
        db.commit()
        logger.info(f"[+] Ingestion pipeline completed successfully for contract {contract_id}!")
        return {"status": "success", "chunk_count": len(chunks)}

    except Exception as e:
        logger.exception(f"[-] Ingestion pipeline failed for contract {contract_id}: {str(e)}")
        contract.status = "failed"
        db.commit()
        raise e
