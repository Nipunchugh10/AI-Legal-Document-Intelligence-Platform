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

# Ensure dynamically registered test routes take precedence over catch-all SPA handler
app.router.routes.insert(0, app.router.routes.pop())
app.router.routes.insert(0, app.router.routes.pop())


def test_global_exception_handler(caplog):
    """
    Verifies that unhandled exceptions are caught by the global exception handler,
    logged with standard formatting, and return a clean 500 internal server error.
    Also verifies that standard HTTPExceptions are passed through.
    """
    # 1. Unhandled exception
    with caplog.at_level(logging.ERROR):
        response = client.get("/test-error", headers={"Accept": "application/json"})
        assert response.status_code == 500
        assert response.json() == {"error": "Internal server error"}
        assert "Unhandled error: Simulated unexpected database connection failure" in caplog.text or any(
            "Unhandled error: Simulated unexpected database connection failure" in r.getMessage() for r in caplog.records
        )

    # 2. Handled HTTPException
    response = client.get("/test-http-error", headers={"Accept": "application/json"})
    assert response.status_code == 403
    assert response.json() == {"detail": "Simulated Forbidden Error"}


@patch("app.services.llm_provider._generate_with_model_cascade")
def test_llm_gemini_success(mock_gemini_cascade, caplog):
    """
    Verifies that a successful Gemini LLM call logs the request starting,
    the serving provider (Gemini), the contract ID, and returns the response.
    """
    mock_gemini_cascade.return_value = "Gemini response text"

    with caplog.at_level(logging.INFO):
        response = get_llm_response("Test prompt", contract_id=999)
        
        assert response == "Gemini response text"
        
        # Verify start logs
        assert "Starting LLM request for contract_id=999" in caplog.text or any(
            "Starting LLM request for contract_id=999" in r.getMessage() for r in caplog.records
        )
        # Verify success logs specifying provider=Gemini and contract_id=999
        assert "LLM call served by provider=Gemini for contract_id=999" in caplog.text or any(
            "LLM call served by provider=Gemini for contract_id=999" in r.getMessage() for r in caplog.records
        )


@patch("app.services.llm_provider._generate_with_model_cascade")
def test_llm_gemini_failure(mock_gemini_cascade, caplog):
    """
    Verifies that when Gemini LLM call fails completely (all fallbacks exhausted),
    the exception is logged and propagated up.
    """
    mock_gemini_cascade.side_effect = Exception("Simulated API failure")

    with pytest.raises(Exception) as exc_info:
        get_llm_response("Test prompt", contract_id=999)
    
    assert "Simulated API failure" in str(exc_info.value)
    
    with caplog.at_level(logging.ERROR):
        assert "All Gemini LLM models failed for contract_id=999: Simulated API failure" in caplog.text or any(
            "All Gemini LLM models failed for contract_id=999: Simulated API failure" in r.getMessage() for r in caplog.records
        )
