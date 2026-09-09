import json
import re
import logging
from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END
from app.agents.base import ContractAnalysisState
from app.services.llm_provider import get_llm_response
from app.services.vector_store import get_vector_store_service

logger = logging.getLogger(__name__)

CLAUSE_SYSTEM_PROMPT = """You are an expert AI Legal Clause Extractor.
Your task is to analyze the provided contract text and extract specific legal clauses.
The target clause types to identify are:
1. "payment_terms" (payment schedules, invoice details, fee milestones, late payment interest, reimbursement, tax terms; often found under "Fees", "Compensation", "Consideration", "Billing", or "Schedule A")
2. "termination_clauses" (conditions for ending the contract, notice periods, cure windows, termination for cause/convenience; often under "Term & Expiry", "Default", "Remedies", "Cancellation")
3. "liability_clauses" (limitations of liability, damage caps, consequential/indirect damage waivers, exclusions to caps; often under "Limitation of Damages", "Risk Allocation")
4. "confidentiality_clauses" (non-disclosure obligations, definition of confidential information, standard 4 carve-outs, return/destruction; often under "Non-Disclosure", "Proprietary Data")
5. "intellectual_property_clauses" (ownership of work product, IP assignment, licensing, moral rights waivers, pre-existing IP reservations; often under "Work Made for Hire", "Proprietary Rights")
6. "dispute_resolution_clauses" (arbitration seat/venue, mediation, escalation to executives, exclusive court jurisdiction; often under "Disputes", "Arbitration", "Governing Law & Forum")
7. "governing_law_clauses" (applicable state/country law governing the contract interpretation; often under "Applicable Law", "Jurisdiction", "Miscellaneous")
8. "renewal_clauses" (initial term length, automatic evergreen renewal, notice window to cancel renewal, fee escalations on renewal; often under "Term", "Duration", "Extension")
9. "indemnification_clauses" (obligations to indemnify, defend, or hold harmless, scope of indemnified claims, third-party claim defense; often under "Indemnity", "Defense of Claims")

EXTRACTION & BOUNDARY RULES:
- If the clause is present, extract the COMPLETE and EXACT text of the clause as it appears in the contract, including any carve-outs, qualifications, or sub-clauses. Specify its approximate location ("beginning", "middle", or "end").
- Non-standard headings: Do not rely solely on exact section titles. A termination provision inside a section titled "Section 9: Term and Default" must be extracted as "termination_clauses". Payment schedules in "Exhibit B" must be extracted as "payment_terms".
- If the clause is NOT present in the contract, set "present" to false, and "text" and "location" to "Not mentioned".

FEW-SHOT EXAMPLES:

Example 1 (Termination Clause buried in "Term and Default"):
Text:
"Section 8. Term and Default. This Agreement shall commence on the Effective Date and remain in effect for two (2) years. Either party may terminate this Agreement immediately upon written notice if the other party breaches any material term and fails to cure such breach within thirty (30) days of receiving written notice thereof. In addition, Customer may terminate for convenience upon sixty (60) days prior written notice."
Output clause item:
{
  "clause_type": "termination_clauses",
  "present": true,
  "text": "Section 8. Term and Default. This Agreement shall commence on the Effective Date and remain in effect for two (2) years. Either party may terminate this Agreement immediately upon written notice if the other party breaches any material term and fails to cure such breach within thirty (30) days of receiving written notice thereof. In addition, Customer may terminate for convenience upon sixty (60) days prior written notice.",
  "location": "middle"
}

Example 2 (Milestone-based Payment Terms in "Fees & Invoicing"):
Text:
"Section 4. Fees and Payment. Client shall pay Contractor $15,000 in three equal milestones: 33% upon signing, 33% upon beta delivery, and 34% upon final acceptance. Invoices are payable net-30 days from receipt. Overdue balances shall accrue interest at 1.5% per month."
Output clause item:
{
  "clause_type": "payment_terms",
  "present": true,
  "text": "Section 4. Fees and Payment. Client shall pay Contractor $15,000 in three equal milestones: 33% upon signing, 33% upon beta delivery, and 34% upon final acceptance. Invoices are payable net-30 days from receipt. Overdue balances shall accrue interest at 1.5% per month.",
  "location": "beginning"
}

Return ONLY a valid, clean JSON object with a single key "clauses" containing a list of clause objects. Each clause object must have the following keys:
- "clause_type": the type of clause (must be exactly one of the nine listed above)
- "present": true if found, false otherwise
- "text": the exact clause text extracted from the document, or "Not mentioned" if not found
- "location": approximate location ("beginning", "middle", "end", or "Not mentioned")

Do NOT include markdown formatting, backticks (like ```json), or text before/after the JSON.
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
            return {"clauses": data}
        if isinstance(data, dict):
            if "clauses" in data:
                return data
            if "clause_type" in data:
                return {"clauses": [data]}
            return data
        return {"clauses": []}
    except json.JSONDecodeError:
        # Fallback 1: search for JSON array if model returned a bare list
        array_match = re.search(r"\[.*\]", cleaned_fixed, re.DOTALL)
        if array_match:
            try:
                data = json.loads(array_match.group(0))
                if isinstance(data, list):
                    return {"clauses": data}
            except json.JSONDecodeError:
                pass

        # Fallback 2: search for outermost JSON object with regex
        match = re.search(r"\{.*\}", cleaned_fixed, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                if isinstance(data, dict):
                    if "clauses" in data:
                        return data
                    if "clause_type" in data:
                        return {"clauses": [data]}
                    return data
            except json.JSONDecodeError:
                pass

        logger.error(f"Failed to parse JSON from LLM response for clauses: {text[:200]}")
        return {
            "clauses": []
        }

def extract_clauses_node(state: ContractAnalysisState) -> Dict[str, Any]:
    """
    LangGraph node function: retrieves relevant contract chunks using RAG,
    passes them to Gemini LLM to extract clauses, and updates state.clauses.
    """
    contract_id = state.get("contract_id", 0)
    raw_text = state.get("raw_text", "")
    
    # 1. Define a single consolidated query for RAG to minimize API embedding requests
    rag_query = (
        "payment terms billing invoicing fee, termination exit end notice, limitation of liability cap damages, "
        "confidentiality non-disclosure proprietary, intellectual property IP ownership patents copyrights, "
        "dispute resolution arbitration litigation, governing law jurisdiction, renewal auto-renew, indemnification hold harmless"
    )

    # 2. Query Vector Store for chunks (fetch top 12 chunks to cover the main clauses)
    retrieved_chunks = {}
    vector_store = get_vector_store_service()
    
    try:
        results = vector_store.query_contract_chunks(contract_id, rag_query, n_results=12)
        for res in results:
            chunk_idx = res.get("chunk_index")
            chunk_text = res.get("text")
            if chunk_idx is not None and chunk_text:
                retrieved_chunks[chunk_idx] = chunk_text
    except Exception as e:
        logger.warning(f"Error querying chunks for RAG (contract {contract_id}): {e}")

    # 3. Consolidate context
    if not retrieved_chunks:
        logger.info(f"No chunks retrieved from vector store for contract {contract_id}. Falling back to raw_text substring.")
        if raw_text:
            context = raw_text[:15000]
        else:
            context = ""
    else:
        # Sort chunks by index to maintain document order
        sorted_indices = sorted(retrieved_chunks.keys())
        context_parts = []
        for idx in sorted_indices:
            context_parts.append(f"--- Document Section (Chunk {idx}) ---\n{retrieved_chunks[idx]}")
        context = "\n\n".join(context_parts)

    if not context:
        return {
            "clauses": {},
            "messages": state.get("messages", []) + [{"role": "system", "content": "Clause extraction failed: no text content available."}],
            "error": "No contract content available for clause extraction."
        }

    # 4. Prepare prompt & call LLM
    prompt = f"{CLAUSE_SYSTEM_PROMPT}\n\nLEGAL DOCUMENT TEXT:\n---\n{context}\n---"
    
    target_clause_types = [
        "payment_terms",
        "termination_clauses",
        "liability_clauses",
        "confidentiality_clauses",
        "intellectual_property_clauses",
        "dispute_resolution_clauses",
        "governing_law_clauses",
        "renewal_clauses",
        "indemnification_clauses"
    ]

    try:
        llm_response = get_llm_response(prompt, temperature=0.0, contract_id=contract_id)
        parsed_data = _clean_and_parse_json(llm_response)
        
        if isinstance(parsed_data, list):
            extracted_clauses = parsed_data
        elif isinstance(parsed_data, dict):
            extracted_clauses = parsed_data.get("clauses", [])
        else:
            extracted_clauses = []
        
        # Format the output dict as clauses map
        clauses_map = {}
        if isinstance(extracted_clauses, list):
            for clause in extracted_clauses:
                if isinstance(clause, dict):
                    clause_type = clause.get("clause_type")
                    if clause_type:
                        clauses_map[clause_type] = {
                            "text": str(clause.get("text", "Not mentioned")),
                            "location": str(clause.get("location", "Not mentioned")),
                            "present": bool(clause.get("present", False))
                        }

        # Handle any missing target clause types by populating them as Not Mentioned
        for target_type in target_clause_types:
            if target_type not in clauses_map:
                clauses_map[target_type] = {
                    "text": "Not mentioned",
                    "location": "Not mentioned",
                    "present": False
                }

        return {
            "clauses": clauses_map,
            "messages": state.get("messages", []) + [
                {
                    "role": "system",
                    "content": f"Clause extraction completed. Extracted {sum(1 for c in clauses_map.values() if c['present'])} active clauses."
                }
            ]
        }
    except Exception as e:
        logger.error(f"Error in extract_clauses_node for contract {contract_id}: {str(e)}")
        # Construct failure state
        fallback_clauses = {
            target_type: {
                "text": "Not mentioned",
                "location": "Not mentioned",
                "present": False
            } for target_type in target_clause_types
        }
        return {
            "clauses": fallback_clauses,
            "error": str(e),
            "messages": state.get("messages", []) + [{"role": "system", "content": f"Clause extraction node error: {str(e)}"}],
        }

def build_clause_graph():
    """
    Constructs the LangGraph state graph for the Clause Detection Agent (Agent 2).
    """
    builder = StateGraph(ContractAnalysisState)
    builder.add_node("extract_clauses", extract_clauses_node)
    builder.add_edge(START, "extract_clauses")
    builder.add_edge("extract_clauses", END)
    
    return builder.compile()
