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
Your task is to analyze the contract clauses and raw text against statutory legal benchmarks and standards (specifically Indian contract law, the Indian Copyright Act, and the DPDP Act 2023).
You must identify compliance issues and categorize them into:

1. "MISSING_REQUIRED_CLAUSE": Mandatory or standard market clauses that are omitted. Examples:
   - For NDAs: missing standard 4-tier exclusions (public domain, prior possession, independent development, compelled disclosure), finite term of confidentiality, or clear arbitration seat under the Arbitration and Conciliation Act, 1996.
   - For Service/Consulting Agreements: missing written copyright assignment specifying rights, duration, and territorial extent under Section 19 of the Copyright Act, 1957; missing payment cure or notice periods.
   - For contracts processing personal data: missing grievance redressal or contact details of a Data Protection Officer (DPO) as required by the DPDP Act 2023.

2. "POTENTIALLY_ILLEGAL_TERM": Terms that violate statutory provisions or are void ab initio under Indian law. Examples:
   - Post-termination non-compete restrictions: Under Section 27 of the Indian Contract Act, 1872, any agreement restraining someone from exercising a lawful profession, trade, or business is void ab initio.
   - Punitive liquidated damages or excessive late interest (>2% per month or >24% per year), which violate Section 74 of the Indian Contract Act as unenforceable penalties.
   - One-sided exculpatory clauses indemnifying a party against its own gross negligence, fraud, or willful misconduct.
   - Restraints on legal proceedings or shortening statutory limitation periods (void under Section 28 of the Indian Contract Act).

3. "DPDP_COMPLIANCE_ISSUE": Data protection deficiencies under the Digital Personal Data Protection (DPDP) Act, 2023. Examples:
   - Broad, vague, or unconditional consent clauses for processing personal data without purpose limitation (violates Section 6).
   - Missing "Right to Erasure" or data destruction instructions for the data processor upon termination or withdrawal of consent.
   - Missing data breach notification procedures (mandated under Section 8) or lack of a 7–15 day grievance redressal mechanism with DPO contact details.

FEW-SHOT EXAMPLES:

Example 1 (POTENTIALLY_ILLEGAL_TERM - Section 27 Non-Compete):
Input Clause:
"For a period of two (2) years following termination of employment, Executive shall not directly or indirectly engage in, work for, or consult with any competitor in India."
Output Issue Object:
{
  "issue_type": "POTENTIALLY_ILLEGAL_TERM",
  "clause_type": "employment_restrictive_covenant",
  "severity": "HIGH",
  "explanation": "Under Section 27 of the Indian Contract Act, 1872, any agreement by which anyone is restrained from exercising a lawful profession, trade or business is void ab initio. Post-termination non-compete covenants are strictly unenforceable in Indian courts (Percept D'Mark v. Zaheer Khan; Niranjan Shankar Golikari v. Century Spg).",
  "recommendation": "Delete the post-termination non-compete clause entirely. If protection of proprietary interests is needed, replace with a reasonable non-solicitation of clients/employees and strict confidentiality covenant, which are permissible under Indian law."
}

Example 2 (MISSING_REQUIRED_CLAUSE - Section 19 Copyright Act IP Assignment):
Input Clause:
"Contractor agrees that all deliverables and work product created during this engagement shall belong exclusively to Client."
Output Issue Object:
{
  "issue_type": "MISSING_REQUIRED_CLAUSE",
  "clause_type": "intellectual_property",
  "severity": "MEDIUM",
  "explanation": "Section 19 of the Indian Copyright Act, 1957 requires that an assignment of copyright must specify the work, the rights assigned, the duration of assignment, and the territorial extent. If duration is not stated, it defaults to 5 years; if territorial extent is not stated, it is deemed to apply only within India.",
  "recommendation": "Revise the IP assignment clause to explicitly specify: (1) worldwide territorial scope, (2) perpetual/irrevocable duration, (3) explicit waiver of moral rights, and (4) waiver of rights under Section 19(4) regarding lapse if not exercised within 1 year."
}

Example 3 (DPDP_COMPLIANCE_ISSUE - Missing Erasure & Grievance Redressal):
Input Clause:
"Client shall provide Customer personal data to Service Provider for processing. Service Provider may retain records as necessary for business archives."
Output Issue Object:
{
  "issue_type": "DPDP_COMPLIANCE_ISSUE",
  "clause_type": "data_privacy",
  "severity": "HIGH",
  "explanation": "Under the Digital Personal Data Protection (DPDP) Act, 2023, data processing must be bound by purpose limitation, provide Data Principals with rights to correction and erasure upon withdrawal of consent, enforce mandatory breach notifications, and specify grievance redressal officer details.",
  "recommendation": "Add a dedicated Data Protection Addendum (DPA) specifying: (1) processing strictly for defined purpose, (2) duty to securely erase personal data upon contract termination, (3) prompt reporting of personal data breaches to Client, and (4) contact details of the Data Protection Officer (DPO) for grievance redressal within 15 days."
}

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

    cleaned_fixed = re.sub(r",\s*([\]}])", r"\1", cleaned)

    try:
        data = json.loads(cleaned_fixed)
        if isinstance(data, list):
            return {"compliance_issues": data}
        if isinstance(data, dict):
            if "compliance_issues" in data:
                return data
            if "issue_type" in data:
                return {"compliance_issues": [data]}
            return data
        return {"compliance_issues": []}
    except json.JSONDecodeError:
        # Fallback 1: match bare JSON array
        array_match = re.search(r"\[.*\]", cleaned_fixed, re.DOTALL)
        if array_match:
            try:
                data = json.loads(array_match.group(0))
                if isinstance(data, list):
                    return {"compliance_issues": data}
            except json.JSONDecodeError:
                pass

        # Fallback 2: match outermost JSON object
        match = re.search(r"\{.*\}", cleaned_fixed, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                if isinstance(data, dict):
                    if "compliance_issues" in data:
                        return data
                    if "issue_type" in data:
                        return {"compliance_issues": [data]}
                    return data
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
