import json
import re
import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from app.agents.base import ContractAnalysisState
from app.services.llm_provider import get_llm_response

logger = logging.getLogger(__name__)

PARSING_SYSTEM_PROMPT = """You are an expert AI Legal Document Classification and Parsing Agent.
Your task is to analyze text extracted from a legal contract/document and return a structured JSON response identifying the core parameters of the document.

Analyze the document carefully and extract:
1. "document_type": The exact type of document (e.g., "Non-Disclosure Agreement (NDA)", "Master Services Agreement", "Freelance Agreement", "Employment Contract", "Residential Lease Agreement", "Software License", etc.).
2. "party_a": Name or identity of the First Party (e.g., Disclosing Party, Client, Employer, Landlord).
3. "party_b": Name or identity of the Second Party (e.g., Receiving Party, Contractor, Employee, Tenant).
4. "effective_date": Effective date or commencement date if mentioned, otherwise "Not mentioned".
5. "jurisdiction": Governing law, jurisdiction, or legal venue if mentioned, otherwise "Not mentioned".
6. "summary": A concise 2-3 sentence executive summary of the document's purpose and key scope.

Return ONLY a valid, clean JSON object with keys:
"document_type", "party_a", "party_b", "effective_date", "jurisdiction", "summary".
Do NOT include markdown formatting, backticks, or text before/after the JSON.
"""

def _clean_and_parse_json(text: str) -> Dict[str, Any]:
    """Cleans LLM response text and parses it as a JSON dictionary."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\n?```$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback: search for JSON object with regex
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        
        logger.error(f"Failed to parse JSON from LLM response: {text[:200]}")
        return {
            "document_type": "Unknown Document",
            "party_a": "Not mentioned",
            "party_b": "Not mentioned",
            "effective_date": "Not mentioned",
            "jurisdiction": "Not mentioned",
            "summary": "Document parsing completed with raw text analysis.",
        }

def parse_document_node(state: ContractAnalysisState) -> Dict[str, Any]:
    """
    LangGraph node function: analyzes state.raw_text using Gemini LLM and populates
    document_type, metadata, summary, and messages.
    """
    raw_text = state.get("raw_text", "")
    contract_id = state.get("contract_id", 0)
    
    if not raw_text:
        return {
            "document_type": "Unknown Document",
            "metadata": {
                "party_a": "Not mentioned",
                "party_b": "Not mentioned",
                "effective_date": "Not mentioned",
                "jurisdiction": "Not mentioned",
            },
            "summary": "No raw text available for parsing.",
            "error": f"Contract ID {contract_id} has no raw text.",
            "messages": state.get("messages", []) + [{"role": "system", "content": "Parsing failed: no raw text"}],
        }

    # Truncate text if extremely long to keep context focused
    sample_text = raw_text[:12000]
    prompt = f"{PARSING_SYSTEM_PROMPT}\n\nLEGAL DOCUMENT TEXT:\n---\n{sample_text}\n---"

    try:
        llm_response = get_llm_response(prompt, temperature=0.0)
        parsed_data = _clean_and_parse_json(llm_response)
        
        doc_type = parsed_data.get("document_type", "Legal Contract")
        metadata = {
            "party_a": parsed_data.get("party_a", "Not mentioned"),
            "party_b": parsed_data.get("party_b", "Not mentioned"),
            "effective_date": parsed_data.get("effective_date", "Not mentioned"),
            "jurisdiction": parsed_data.get("jurisdiction", "Not mentioned"),
        }
        summary = parsed_data.get("summary", "Parsing complete.")

        return {
            "document_type": doc_type,
            "metadata": metadata,
            "summary": summary,
            "messages": state.get("messages", []) + [
                {
                    "role": "system",
                    "content": f"Document parsing completed. Type: {doc_type}, Parties: {metadata['party_a']} & {metadata['party_b']}",
                }
            ],
        }
    except Exception as e:
        logger.error(f"Error in parse_document_node for contract {contract_id}: {str(e)}")
        return {
            "document_type": "Unclassified Legal Document",
            "metadata": {
                "party_a": "Not mentioned",
                "party_b": "Not mentioned",
                "effective_date": "Not mentioned",
                "jurisdiction": "Not mentioned",
            },
            "summary": f"Document parsing encountered an issue: {str(e)}",
            "error": str(e),
            "messages": state.get("messages", []) + [{"role": "system", "content": f"Parsing node error: {str(e)}"}],
        }

def build_parsing_graph():
    """
    Constructs the LangGraph state graph for the Document Parsing Agent (Agent 1).
    """
    builder = StateGraph(ContractAnalysisState)
    builder.add_node("parse_document", parse_document_node)
    builder.add_edge(START, "parse_document")
    builder.add_edge("parse_document", END)
    
    return builder.compile()
