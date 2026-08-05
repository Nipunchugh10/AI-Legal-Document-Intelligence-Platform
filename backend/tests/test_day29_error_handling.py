import pytest
import logging
from unittest.mock import patch
from fastapi.testclient import TestClient
from fastapi import HTTPException
from app.main import app
from app.services.llm_provider import get_llm_response

client = TestClient(app, raise_server_exceptions=False)

# Setup a test route to trigger unhandled exception
@app.get("/test-error")
def trigger_unhandled_error():
    raise ValueError("Simulated unexpected database connection failure")

@app.get("/test-http-error")
def trigger_http_error():
    raise HTTPException(status_code=403, detail="Simulated Forbidden Error")

def test_global_exception_handler(caplog):
    """
    Verifies that unhandled exceptions are caught by the global exception handler,
    logged with standard formatting, and return a clean 500 internal server error.
    Also verifies that standard HTTPExceptions are passed through.
    """
    # 1. Unhandled exception
    with caplog.at_level(logging.ERROR):
        response = client.get("/test-error")
        assert response.status_code == 500
        assert response.json() == {"error": "Internal server error"}
        assert any("Unhandled error: Simulated unexpected database connection failure" in record.message for record in caplog.records)

    # 2. Handled HTTPException
    response = client.get("/test-http-error")
    assert response.status_code == 403
    assert response.json() == {"detail": "Simulated Forbidden Error"}


@patch("app.services.llm_provider._call_gemini_with_retry")
def test_llm_gemini_success(mock_gemini_retry, caplog):
    """
    Verifies that a successful Gemini LLM call logs the request starting,
    the serving provider (Gemini), the contract ID, and returns the response.
    """
    mock_gemini_retry.return_value = "Gemini response text"

    with caplog.at_level(logging.INFO):
        response = get_llm_response("Test prompt", contract_id=999)
        
        assert response == "Gemini response text"
        
        # Verify start logs
        assert any("Starting LLM request for contract_id=999" in record.message for record in caplog.records)
        # Verify success logs specifying provider=Gemini and contract_id=999
        assert any("LLM call served by provider=Gemini for contract_id=999" in record.message for record in caplog.records)


@patch("app.services.llm_provider._call_gemini_with_retry")
def test_llm_gemini_failure(mock_gemini_retry, caplog):
    """
    Verifies that when Gemini LLM call fails completely (all retries exhausted),
    the exception is logged and propagated up.
    """
    mock_gemini_retry.side_effect = Exception("Simulated API failure")

    with pytest.raises(Exception) as exc_info:
        get_llm_response("Test prompt", contract_id=999)
    
    assert "Simulated API failure" in str(exc_info.value)
    
    with caplog.at_level(logging.ERROR):
        assert any("Primary LLM API call (Gemini) failed: Simulated API failure" in record.message for record in caplog.records)
