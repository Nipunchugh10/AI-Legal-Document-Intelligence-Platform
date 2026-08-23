import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.knowledge_base_ingester import ingest_knowledge_base
from app.services.vector_store import get_vector_store_service

MOCK_EMBEDDING = [0.1] * 384

@pytest.fixture
def mock_embedder():
    with patch("app.services.embedder.EmbedderService.embed_text") as mock_embed:
        mock_embed.return_value = MOCK_EMBEDDING
        yield mock_embed

def test_knowledge_base_files_exist():
    kb_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "knowledge_base"))
    assert os.path.exists(kb_dir), "Knowledge base directory does not exist."
    files = [f for f in os.listdir(kb_dir) if f.endswith(".md")]
    assert len(files) >= 4, "Expected at least 4 markdown files in knowledge base."
    
    expected_files = [
        "dpdp_compliance_standards.md",
        "indian_contract_act_standards.md",
        "indian_nda_standards.md",
        "indian_service_agreement_standards.md"
    ]
    for ef in expected_files:
        assert ef in files, f"Expected file {ef} was not found."

def test_knowledge_base_ingestion_and_query(mock_embedder):
    vector_store = get_vector_store_service()
    
    # 1. Run ingestion (using mocked embedder to prevent external API calls)
    success = ingest_knowledge_base()
    assert success is True, "Ingestion process failed."
    
    # 2. Test querying from the collection without category filter
    results = vector_store.query_knowledge("consent data subject rights", n_results=3)
    assert len(results) > 0, "Querying the knowledge base returned empty results."
    
    # Check shape of returned dicts
    first_res = results[0]
    assert "id" in first_res
    assert "text" in first_res
    assert "category" in first_res
    assert "document_name" in first_res
    assert "similarity" in first_res
    assert first_res["similarity"] is not None

    # 3. Test querying with a specific category filter (e.g. 'dpdp')
    dpdp_results = vector_store.query_knowledge("consent notice", category="dpdp", n_results=5)
    for res in dpdp_results:
        assert res["category"] == "dpdp", f"Expected category 'dpdp', got '{res['category']}'"
        assert "dpdp" in res["document_name"], f"Expected 'dpdp' in document name, got '{res['document_name']}'"

    # 4. Test querying with another category filter (e.g. 'nda')
    nda_results = vector_store.query_knowledge("arbitration governing law", category="nda", n_results=5)
    for res in nda_results:
        assert res["category"] == "nda", f"Expected category 'nda', got '{res['category']}'"
