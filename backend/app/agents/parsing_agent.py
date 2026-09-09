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
1. "document_type": The exact type of document (e.g., "Non-Disclosure Agreement (NDA)", "Master Services Agreement (MSA)", "Employment Contract", "Commercial Lease Agreement", "Freelance Consulting Agreement", "Software License", etc.).
2. "party_a": Name or identity of the First Party (e.g., Disclosing Party, Client, Employer, Landlord, Service Provider).
3. "party_b": Name or identity of the Second Party (e.g., Receiving Party, Contractor, Employee, Tenant, Customer).
4. "effective_date": Effective date or commencement date if mentioned, otherwise "Not mentioned".
5. "jurisdiction": Governing law, jurisdiction, or legal venue if mentioned (e.g., "State of Delaware, USA", "New Delhi, India", "California, USA"), otherwise "Not mentioned".
6. "summary": A concise 2-3 sentence executive summary of the document's purpose and key scope.

GUIDELINES FOR ATYPICAL OR COMPLEX CONTRACTS:
- Party Names: Scan the document title, preamble ("by and between..."), recitals, and signature blocks. Look for defined terms such as "Company", "Customer", "Provider", "Lessor", "Lessee", "Consultant", "Executive".
- Effective Date: If not on page 1, check the final signature blocks for execution dates or clauses defining commencement (e.g., "effective upon board approval" or "from the date of handover").
- Governing Law / Jurisdiction: Often found towards the end under headings such as "Governing Law", "Jurisdiction", "Dispute Resolution", "General Provisions", or "Miscellaneous".

FEW-SHOT EXAMPLES:

Example 1 (SaaS Agreement):
Text:
"CLOUD SERVICES MASTER AGREEMENT
This Master Agreement is entered into as of October 15, 2026 by and between CloudSphere Technologies Corp. ('Provider') and Enterprise Global Retail LLC ('Customer').
Section 14. Governing Law. This Agreement will be governed by the laws of the State of Delaware, without regard to conflicts of law principles."
Output:
{
  "document_type": "Master Services Agreement (MSA)",
  "party_a": "CloudSphere Technologies Corp.",
  "party_b": "Enterprise Global Retail LLC",
  "effective_date": "October 15, 2026",
  "jurisdiction": "State of Delaware, USA",
  "summary": "This Master Services Agreement establishes the commercial and legal terms under which CloudSphere Technologies Corp. provides cloud software services to Enterprise Global Retail LLC."
}

Example 2 (Executive Employment Agreement):
Text:
"EXECUTIVE EMPLOYMENT AGREEMENT
Between Vanguard Media Technologies Pvt. Ltd. ('Company') and Dr. Rajesh Sharma ('Executive').
Commencement Date: January 1, 2027.
This agreement shall be subject to the exclusive jurisdiction of the competent courts in New Delhi, India."
Output:
{
  "document_type": "Executive Employment Agreement",
  "party_a": "Vanguard Media Technologies Pvt. Ltd.",
  "party_b": "Dr. Rajesh Sharma",
  "effective_date": "January 1, 2027",
  "jurisdiction": "New Delhi, India",
  "summary": "This Executive Employment Agreement outlines the terms of executive appointment, compensation, and duties between Vanguard Media Technologies Pvt. Ltd. and Dr. Rajesh Sharma."
}

Example 3 (Commercial Lease):
Text:
"INDENTURE OF COMMERCIAL LEASE
Made on August 1, 2026 between Horizon Commercial Realty Trust ('Lessor') and Omni Retail Ventures Ltd. ('Lessee') for Premises at MG Road, Bangalore.
Governing Law: The courts at Bangalore, Karnataka, India shall have exclusive jurisdiction."
Output:
{
  "document_type": "Commercial Lease Agreement",
  "party_a": "Horizon Commercial Realty Trust",
  "party_b": "Omni Retail Ventures Ltd.",
  "effective_date": "August 1, 2026",
  "jurisdiction": "Bangalore, Karnataka, India",
  "summary": "This Commercial Lease Agreement establishes the tenancy rights, obligations, and commercial lease terms between Horizon Commercial Realty Trust and Omni Retail Ventures Ltd. for property in Bangalore."
}

Return ONLY a valid, clean JSON object with keys:
"document_type", "party_a", "party_b", "effective_date", "jurisdiction", "summary".
Do NOT include markdown formatting, backticks, or text before/after the JSON.
"""

def _clean_and_parse_json(text: str) -> Dict[str, Any]:
    """Cleans LLM response text and safely parses it as a JSON dictionary."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\n?```$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            if len(data) > 0 and isinstance(data[0], dict):
                return data[0]
            return {}
        if isinstance(data, dict):
            return data
        return {}
    except json.JSONDecodeError:
        # Fallback 1: Extract outermost curly braces using regex
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            extracted = match.group(0)
            try:
                data = json.loads(extracted)
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                # Fallback 2: Clean trailing commas before closing braces/brackets
                fixed = re.sub(r",\s*([\]}])", r"\1", extracted)
                try:
                    data = json.loads(fixed)
                    if isinstance(data, dict):
                        return data
                except json.JSONDecodeError:
                    pass
        
        logger.error(f"Failed to parse JSON from LLM response: {text[:200]}")
        return {
            "document_type": "Legal Contract",
            "party_a": "Not mentioned",
            "party_b": "Not mentioned",
            "effective_date": "Not mentioned",
            "jurisdiction": "Not mentioned",
            "summary": "Document parsing completed.",
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
            "document_type": "Legal Contract",
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
        llm_response = get_llm_response(prompt, temperature=0.0, contract_id=contract_id)
        parsed_data = _clean_and_parse_json(llm_response)
        
        if not isinstance(parsed_data, dict):
            parsed_data = {}

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
