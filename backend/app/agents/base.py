from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, START, END

class ContractAnalysisState(TypedDict):
    """
    Shared state schema passed across all LangGraph nodes in the legal analysis pipeline.
    """
    contract_id: int
    raw_text: str
    chunks: List[str]
    document_type: Optional[str]
    metadata: Dict[str, Any]
    clauses: Dict[str, Any]
    risks: List[Dict[str, Any]]
    compliance_issues: List[Dict[str, Any]]
    summary: str
    messages: List[Dict[str, Any]]
    error: Optional[str]


def extract_text_node(state: ContractAnalysisState) -> Dict[str, Any]:
    """
    Minimal test node: returns existing raw text or placeholder message in state.
    """
    contract_id = state.get("contract_id", 0)
    raw_text = state.get("raw_text", "")
    
    if not raw_text:
        raw_text = f"Sample legal contract text for contract ID {contract_id}."
    
    return {
        "raw_text": raw_text,
        "messages": state.get("messages", []) + [{"role": "system", "content": f"Extracted text for contract {contract_id}"}]
    }


def build_test_graph():
    """
    Constructs a minimal test LangGraph StateGraph (START -> extract_text_node -> END).
    Used to verify LangGraph workflow setup and state transition logic.
    """
    builder = StateGraph(ContractAnalysisState)
    builder.add_node("extract_text", extract_text_node)
    builder.add_edge(START, "extract_text")
    builder.add_edge("extract_text", END)
    
    return builder.compile()
