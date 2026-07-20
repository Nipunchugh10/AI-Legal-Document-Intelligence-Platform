import pytest
from app.services.llm_provider import get_llm_response, get_langchain_llm
from app.agents.base import ContractAnalysisState, build_test_graph

def test_llm_provider_response():
    """
    Verifies that get_llm_response calls Google Gemini API and returns a valid string response.
    """
    prompt = "Reply with exactly the word 'ACKNOWLEDGED'."
    try:
        response = get_llm_response(prompt, temperature=0.0)
        assert isinstance(response, str)
        assert len(response) > 0
    except Exception as e:
        if "429" in str(e) or "quota" in str(e).lower():
            pytest.skip("Skipping live LLM network test due to Gemini API rate limit reset window.")
        else:
            raise e

def test_langchain_llm_instantiation():
    """
    Verifies that get_langchain_llm returns a valid ChatGoogleGenerativeAI object.
    """
    llm = get_langchain_llm(temperature=0.0)
    assert llm is not None
    assert hasattr(llm, "invoke")

def test_contract_analysis_state_structure():
    """
    Verifies that ContractAnalysisState schema contains all expected typed keys.
    """
    state: ContractAnalysisState = {
        "contract_id": 42,
        "raw_text": "Sample NDA contract text.",
        "chunks": ["Sample NDA", "contract text."],
        "document_type": "NDA",
        "metadata": {"author": "Legal Dept"},
        "clauses": {"confidentiality": "High priority"},
        "risks": [{"risk": "Unilateral termination"}],
        "compliance_issues": [],
        "summary": "Standard NDA",
        "messages": [],
        "error": None,
    }
    assert state["contract_id"] == 42
    assert state["document_type"] == "NDA"
    assert len(state["chunks"]) == 2

def test_langgraph_execution_flow():
    """
    Verifies that the LangGraph test state graph compiles and executes end-to-end.
    """
    graph = build_test_graph()
    assert graph is not None
    
    initial_state: ContractAnalysisState = {
        "contract_id": 101,
        "raw_text": "This is a test contract for LangGraph execution.",
        "chunks": [],
        "document_type": None,
        "metadata": {},
        "clauses": {},
        "risks": [],
        "compliance_issues": [],
        "summary": "",
        "messages": [],
        "error": None,
    }
    
    final_state = graph.invoke(initial_state)
    assert final_state["raw_text"] == "This is a test contract for LangGraph execution."
    assert len(final_state["messages"]) == 1
    assert "Extracted text for contract 101" in final_state["messages"][0]["content"]
