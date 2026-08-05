import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from app.agents.base import ContractAnalysisState
from app.services.llm_provider import get_llm_response
from app.agents.parsing_agent import parse_document_node
from app.agents.clause_agent import extract_clauses_node
from app.agents.risk_agent import extract_risks_node
from app.agents.compliance_agent import check_compliance_node
from app.agents.negotiation_agent import negotiation_advisor_node

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM_PROMPT = """You are an expert AI Legal Executive Summarizer.
Your task is to review all the analysis results generated for a contract and produce a clean, professional, plain-English summary report.

Review the following inputs:
1. Document Type & Parties
2. Extracted Clauses
3. Identified Risks (including Suggested Revisions and Negotiation Tips)
4. Compliance Issues

Generate a summary report structured in Markdown covering:
- **Executive Summary**: A brief, high-level summary of the contract's scope and purpose (2-3 sentences).
- **Key Risk Highlights & Negotiation Suggestions**: A summary of the most critical risks identified, outlining high-level negotiation recommendations (citing suggested revisions and tips).
- **Compliance Status**: A quick overview of any compliance deficiencies (e.g. DPDP or Indian Contract Act violations).
- **Actionable Next Steps**: 2-3 concrete recommendations for the user to negotiate or amend before signing.

Keep the tone professional, objective, and easy to read for a non-lawyer.
Return the summary as plain markdown text. Do NOT wrap it in JSON.
"""

def generate_summary_node(state: ContractAnalysisState) -> Dict[str, Any]:
    """
    LangGraph node function: reads parsed metadata, extracted clauses, risks, and compliance issues
    from the graph state, passes them to Gemini LLM to generate an executive report in Markdown.
    """
    contract_id = state.get("contract_id", 0)
    doc_type = state.get("document_type", "Legal Contract")
    metadata = state.get("metadata", {})
    clauses = state.get("clauses", {})
    risks = state.get("risks", [])
    compliance = state.get("compliance_issues", [])

    # Format the inputs for the LLM prompt
    metadata_str = (
        f"Document Type: {doc_type}\n"
        f"Party A (Disclosing/Client/Employer): {metadata.get('party_a', 'Not mentioned')}\n"
        f"Party B (Receiving/Contractor/Employee): {metadata.get('party_b', 'Not mentioned')}\n"
        f"Effective Date: {metadata.get('effective_date', 'Not mentioned')}\n"
        f"Jurisdiction/Governing Law: {metadata.get('jurisdiction', 'Not mentioned')}"
    )
    
    risks_list = []
    for r in risks:
        risk_item_str = f"- [{r.get('severity', 'MEDIUM')}] {r.get('risk_type', 'UNKNOWN')}: {r.get('explanation', '')} (Clause: {r.get('clause_text', '')})"
        if r.get("suggested_revision"):
            risk_item_str += f"\n  * **Suggested Revision:** {r.get('suggested_revision')}"
        if r.get("negotiation_tip"):
            risk_item_str += f"\n  * **Negotiation Tip:** {r.get('negotiation_tip')}"
        risks_list.append(risk_item_str)
    risks_str = "\n".join(risks_list) if risks_list else "No major risks identified."

    comp_list = []
    for c in compliance:
        comp_list.append(f"- [{c.get('severity', 'MEDIUM')}] {c.get('issue_type', 'UNKNOWN')} in {c.get('clause_type', 'unknown')}: {c.get('explanation', '')}")
    comp_str = "\n".join(comp_list) if comp_list else "No compliance issues identified."

    prompt = (
        f"{SUMMARY_SYSTEM_PROMPT}\n\n"
        f"--- ANALYSIS INPUTS FOR CONTRACT {contract_id} ---\n\n"
        f"--- METADATA & PARTIES ---\n"
        f"{metadata_str}\n\n"
        f"--- IDENTIFIED RISKS ---\n"
        f"{risks_str}\n\n"
        f"--- COMPLIANCE ISSUES ---\n"
        f"{comp_str}\n\n"
        f"Please write the executive summary report in clean Markdown format now."
    )

    try:
        summary_report = get_llm_response(prompt, temperature=0.2, contract_id=contract_id)
        return {
            "summary": summary_report.strip(),
            "messages": state.get("messages", []) + [{"role": "system", "content": "Executive summary generated successfully."}]
        }
    except Exception as e:
        logger.error(f"Error in generate_summary_node for contract {contract_id}: {str(e)}")
        return {
            "summary": "Failed to generate executive summary report.",
            "error": str(e),
            "messages": state.get("messages", []) + [{"role": "system", "content": f"Summary generation node error: {str(e)}"}]
        }

def error_node(state: ContractAnalysisState) -> Dict[str, Any]:
    """
    Error node function: populates the error state when text content is missing.
    """
    return {
        "error": "No contract content available for analysis.",
        "messages": state.get("messages", []) + [{"role": "system", "content": "Analysis halted: empty document text."}]
    }

def check_text_exists(state: ContractAnalysisState) -> str:
    """
    Conditional routing function: checks if raw_text is present in state.
    """
    raw_text = state.get("raw_text", "")
    if not raw_text or not raw_text.strip():
        return "error_node"
    return "parse_document"

def build_analysis_workflow():
    """
    Constructs and compiles the full contract analysis orchestrator LangGraph.
    """
    builder = StateGraph(ContractAnalysisState)
    
    # Add nodes
    builder.add_node("parse_document", parse_document_node)
    builder.add_node("extract_clauses", extract_clauses_node)
    builder.add_node("extract_risks", extract_risks_node)
    builder.add_node("negotiation_advisor", negotiation_advisor_node)
    builder.add_node("check_compliance", check_compliance_node)
    builder.add_node("generate_summary", generate_summary_node)
    builder.add_node("error_node", error_node)
    
    # Add conditional edge from START
    builder.add_conditional_edges(
        START,
        check_text_exists,
        {
            "error_node": "error_node",
            "parse_document": "parse_document"
        }
    )
    
    # Add sequential edges
    builder.add_edge("parse_document", "extract_clauses")
    builder.add_edge("extract_clauses", "extract_risks")
    builder.add_edge("extract_risks", "negotiation_advisor")
    builder.add_edge("negotiation_advisor", "check_compliance")
    builder.add_edge("check_compliance", "generate_summary")
    
    # Add terminal edges
    builder.add_edge("generate_summary", END)
    builder.add_edge("error_node", END)
    
    return builder.compile()
