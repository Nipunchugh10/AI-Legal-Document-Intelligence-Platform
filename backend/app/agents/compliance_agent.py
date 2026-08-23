import json
import re
import logging
from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END
from app.agents.base import ContractAnalysisState
from app.services.llm_provider import get_llm_response
from app.services.vector_store import get_vector_store_service

logger = logging.getLogger(__name__)

COMPLIANCE_SYSTEM_PROMPT = """You are an expert AI Legal Compliance Agent.
Your task is to analyze the contract clauses and raw text against the provided legal benchmarks and standards (specifically Indian contract laws and the DPDP Act 2023).
You must identify compliance issues and categorize them into:

1. "MISSING_REQUIRED_CLAUSE": Check if there are mandatory or highly recommended clauses that are missing. Examples:
   - For NDAs: missing standard exclusions (public domain, prior possession, independent development, compelled disclosure), term of confidentiality, or clear arbitration mechanisms under the Arbitration and Conciliation Act, 1996.
   - For Service Agreements: missing copyright assignment writing/territory/duration under Section 19 of the Copyright Act 1957, payment terms, or notice periods.
   - For any agreement processing personal data: missing grievance redressal or contact details of a Data Protection Officer (DPO) as required by DPDP.
2. "POTENTIALLY_ILLEGAL_TERM": Check for terms that violate statutory provisions or are void under Indian law. Examples:
   - Post-termination non-compete restrictions (restraint of trade under Section 27 of the Indian Contract Act, 1872 is void).
   - Punitive late fees/interest (>2% per month or >24% per year, which violate Section 74 penalty limits).
   - One-sided indemnity clauses where a party indemnifies the other for the other's own negligence or misconduct.
   - Waiving the right to data breach notifications (prohibited under DPDP Act).
3. "DPDP_COMPLIANCE_ISSUE": Check for data protection issues under the Digital Personal Data Protection (DPDP) Act, 2023. Examples:
   - Unconditional, broad, or vague consent clauses for processing personal data without a clear purpose.
   - Missing "Right to Erasure" or data deletion instructions for the data processor upon termination or withdrawal of consent.
   - Missing data breach notification requirements or grievance redressal mechanism (must resolve complaints within 7-15 business days).

For each compliance issue found, return a structured issue item containing:
- "issue_type": Must be exactly one of: "MISSING_REQUIRED_CLAUSE", "POTENTIALLY_ILLEGAL_TERM", "DPDP_COMPLIANCE_ISSUE".
- "clause_type": The type of clause associated with the issue (e.g., "dispute_resolution", "confidentiality", "intellectual_property", "data_privacy", "payment_terms", "indemnification", etc.).
- "severity": The severity level ("HIGH", "MEDIUM", or "LOW").
- "explanation": A clear, professional, plain-English explanation of the compliance issue, detailing what benchmark/law it violates or falls short of.
- "recommendation": A concrete, actionable recommendation on how to revise the contract to achieve compliance (e.g., specific language to add or delete).

Return ONLY a valid, clean JSON object with a single key "compliance_issues" containing a list of compliance issue items.
Do NOT include markdown formatting, backticks (like ```json), or text before/after the JSON.

If no compliance issues are found, return:
{
  "compliance_issues": []
}
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
        
        logger.error(f"Failed to parse JSON from LLM response for compliance: {text[:200]}")
        return {
            "compliance_issues": []
        }

def check_compliance_node(state: ContractAnalysisState) -> Dict[str, Any]:
    """
    LangGraph node function: retrieves relevant legal standards from the legal_knowledge vector store,
    compares contract clauses in state against retrieved standards using Gemini LLM,
    and populates state.compliance_issues.
    """
    contract_id = state.get("contract_id", 0)
    clauses = state.get("clauses", {})
    document_type = state.get("document_type", "")
    raw_text = state.get("raw_text", "")

    # 1. Determine document type category to query the correct knowledge base file
    doc_type_lower = (document_type or "").lower()
    specific_category = "general"
    specific_query = ""
    
    if "nda" in doc_type_lower or "disclosure" in doc_type_lower:
        specific_category = "nda"
        specific_query = "NDA confidentiality scope exclusions term duration arbitration conciliation act governing law seat"
    elif "service" in doc_type_lower or "freelance" in doc_type_lower or "consult" in doc_type_lower:
        specific_category = "service_agreement"
        specific_query = "Intellectual property assignment copyright act Section 19 royalty payment terms TDS GST notice period"
    
    # 2. Retrieve relevant legal standards from ChromaDB using RAG
    vector_store = get_vector_store_service()
    retrieved_standards = []
    
    # Fetch general Indian contract standards
    try:
        results = vector_store.query_knowledge(
            query_text="Indian contract act essentials restraint of trade non-compete indemnity liquidated damages penalty interest rate",
            category="indian_contract_act",
            n_results=4
        )
        retrieved_standards.extend(results)
    except Exception as e:
        logger.warning(f"Error querying indian_contract_act standards: {e}")

    # Fetch DPDP standards
    try:
        results = vector_store.query_knowledge(
            query_text="DPDP Act 2023 consent notice data fiduciary engagement processor rights access correction erasure DPO breach notification grievance redressal",
            category="dpdp",
            n_results=4
        )
        retrieved_standards.extend(results)
    except Exception as e:
        logger.warning(f"Error querying dpdp standards: {e}")

    # Fetch specific contract category standards if applicable
    if specific_query and specific_category != "general":
        try:
            results = vector_store.query_knowledge(
                query_text=specific_query,
                category=specific_category,
                n_results=4
            )
            retrieved_standards.extend(results)
        except Exception as e:
            logger.warning(f"Error querying specific {specific_category} standards: {e}")

    # 3. Consolidate standards context
    standards_parts = []
    for idx, std in enumerate(retrieved_standards):
        doc_name = std.get("document_name", "Unknown Document")
        cat = std.get("category", "general")
        text = std.get("text", "")
        standards_parts.append(
            f"--- Legal Standard {idx+1} [Source: {doc_name}, Category: {cat}] ---\n"
            f"{text}"
        )
    
    standards_context = "\n\n".join(standards_parts)

    # 4. Format contract clauses context
    clauses_parts = []
    if clauses and isinstance(clauses, dict):
        for c_type, details in clauses.items():
            if isinstance(details, dict) and details.get("present"):
                clauses_parts.append(
                    f"Clause Type: {c_type}\n"
                    f"Text: {details.get('text')}\n"
                    f"Location: {details.get('location')}\n"
                )
    
    if clauses_parts:
        contract_context = "\n".join(clauses_parts)
        context_header = "EXTRACTED CLAUSES FOR COMPLIANCE CHECK:"
    else:
        logger.info(f"No clauses found in state for compliance checking (contract {contract_id}). Using raw_text substring.")
        contract_context = raw_text[:15000] if raw_text else ""
        context_header = "CONTRACT TEXT FOR COMPLIANCE CHECK (fallback):"

    if not contract_context:
        return {
            "compliance_issues": [],
            "messages": state.get("messages", []) + [{"role": "system", "content": "Compliance check failed: no text content available."}],
            "error": "No contract content available for compliance checking."
        }

    # 5. Build full prompt and get LLM response
    prompt = (
        f"{COMPLIANCE_SYSTEM_PROMPT}\n\n"
        f"DOCUMENT TYPE: {document_type or 'Unknown'}\n\n"
        f"--- {context_header} ---\n"
        f"{contract_context}\n\n"
        f"--- RETRIEVED LEGAL COMPLIANCE STANDARDS & BENCHMARKS ---\n"
        f"{standards_context}\n\n"
        f"Please perform the compliance analysis now."
    )

    try:
        llm_response = get_llm_response(prompt, temperature=0.0, contract_id=contract_id)
        parsed_data = _clean_and_parse_json(llm_response)
        
        if isinstance(parsed_data, list):
            issues_list = parsed_data
        elif isinstance(parsed_data, dict):
            issues_list = parsed_data.get("compliance_issues", [])
        else:
            issues_list = []

        # Validate structured fields
        validated_issues = []
        if isinstance(issues_list, list):
            for issue in issues_list:
                if isinstance(issue, dict):
                    validated_issues.append({
                        "issue_type": str(issue.get("issue_type", "UNKNOWN")),
                        "clause_type": str(issue.get("clause_type", "unknown")),
                        "severity": str(issue.get("severity", "MEDIUM")),
                        "explanation": str(issue.get("explanation", "Compliance issue identified.")),
                        "recommendation": str(issue.get("recommendation", "Review and revise the clause to follow best practice standards."))
                    })

        return {
            "compliance_issues": validated_issues,
            "messages": state.get("messages", []) + [
                {
                    "role": "system",
                    "content": f"Compliance check completed. Identified {len(validated_issues)} issues."
                }
            ]
        }
    except Exception as e:
        logger.error(f"Error in check_compliance_node for contract {contract_id}: {str(e)}")
        return {
            "compliance_issues": [],
            "error": str(e),
            "messages": state.get("messages", []) + [{"role": "system", "content": f"Compliance node error: {str(e)}"}],
        }

def build_compliance_graph():
    """
    Constructs the LangGraph state graph for the Compliance Agent (Agent 4).
    """
    builder = StateGraph(ContractAnalysisState)
    builder.add_node("check_compliance", check_compliance_node)
    builder.add_edge(START, "check_compliance")
    builder.add_edge("check_compliance", END)
    
    return builder.compile()
