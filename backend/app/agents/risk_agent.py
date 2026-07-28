import json
import re
import logging
from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END
from app.agents.base import ContractAnalysisState
from app.services.llm_provider import get_llm_response

logger = logging.getLogger(__name__)

RISK_SYSTEM_PROMPT = """You are an expert AI Legal Risk Assessment Agent.
Your task is to analyze the contract text or extracted clauses and identify key risk factors for the user.
For each clause/document text provided, evaluate if it poses any of the following risks:

1. "UNLIMITED_LIABILITY": Check if there is no cap on damages, if liability is unlimited or uncapped, or if the cap is unreasonably high.
2. "ONE_SIDED_TERMINATION": Check if only one party has the right to terminate for convenience, or if notice periods or termination penalties are highly one-sided.
3. "AUTOMATIC_RENEWAL": Check if the contract auto-renews without reasonable prior notice (e.g., auto-renews unless a notice is given, with a short window).
4. "BROAD_IP_ASSIGNMENT": Check if intellectual property assignment is overly broad (e.g., transferring ownership of all ideas, tools, or pre-existing code, even those unrelated to the project).
5. "UNILATERAL_MODIFICATION": Check if one party has the right to modify the agreement's terms, fees, or specifications unilaterally without mutual written agreement.
6. "EXCESSIVE_PENALTIES": Check if there are disproportionate late fees (e.g., extremely high interest rates like >2% per month), penalty charges, or severe default clauses.
7. "BROAD_CONFIDENTIALITY": Check if confidential information is defined too broadly (e.g., covering information publicly available, or lacking standard exclusions).

For each risk identified, return a structured risk item containing:
- "risk_type": The exact risk category identifier (must be exactly one of the seven listed above: "UNLIMITED_LIABILITY", "ONE_SIDED_TERMINATION", "AUTOMATIC_RENEWAL", "BROAD_IP_ASSIGNMENT", "UNILATERAL_MODIFICATION", "EXCESSIVE_PENALTIES", "BROAD_CONFIDENTIALITY").
- "severity": The severity level ("HIGH", "MEDIUM", or "LOW").
- "clause_text": The relevant text snippet from the contract where the risk is located.
- "explanation": A clear, plain-English explanation of why this poses a risk to the user.
- "suggestion": A concrete, actionable negotiation or mitigation recommendation.

Return ONLY a valid, clean JSON object with a single key "risks" containing a list of risk items.
Do NOT include markdown formatting, backticks (like ```json), or text before/after the JSON.

If no risks are identified, return:
{
  "risks": []
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
        
        logger.error(f"Failed to parse JSON from LLM response for risks: {text[:200]}")
        return {
            "risks": []
        }

def extract_risks_node(state: ContractAnalysisState) -> Dict[str, Any]:
    """
    LangGraph node function: analyzes extracted clauses in state (or falls back to raw_text),
    calls Gemini LLM to identify and assess legal risks, and populates state.risks.
    """
    contract_id = state.get("contract_id", 0)
    clauses = state.get("clauses", {})
    raw_text = state.get("raw_text", "")

    # 1. Format context for the LLM
    clauses_input = []
    if clauses:
        for clause_type, details in clauses.items():
            if details.get("present"):
                clauses_input.append(
                    f"Clause Type: {clause_type}\n"
                    f"Text: {details.get('text')}\n"
                    f"Location: {details.get('location')}\n"
                )

    if clauses_input:
        context = "\n".join(clauses_input)
        context_header = "EXTRACTED CLAUSES FOR RISK ASSESSMENT:"
    else:
        logger.info(f"No active clauses in state for contract {contract_id}. Falling back to raw_text.")
        context = raw_text[:15000] if raw_text else ""
        context_header = "CONTRACT TEXT FOR RISK ASSESSMENT (fallback):"

    if not context:
        return {
            "risks": [],
            "messages": state.get("messages", []) + [{"role": "system", "content": "Risk assessment failed: no text content available."}],
            "error": "No contract content available for risk assessment."
        }

    # 2. Call Gemini LLM
    prompt = f"{RISK_SYSTEM_PROMPT}\n\n{context_header}\n---\n{context}\n---"

    try:
        llm_response = get_llm_response(prompt, temperature=0.0)
        parsed_data = _clean_and_parse_json(llm_response)
        risks_list = parsed_data.get("risks", [])

        # Validate that each risk item has all the expected fields
        validated_risks = []
        for risk in risks_list:
            validated_risks.append({
                "risk_type": risk.get("risk_type", "UNKNOWN"),
                "severity": risk.get("severity", "MEDIUM"),
                "clause_text": risk.get("clause_text", "Not mentioned"),
                "explanation": risk.get("explanation", "Potential risk detected."),
                "suggestion": risk.get("suggestion", "Review this clause carefully with a legal representative.")
            })

        return {
            "risks": validated_risks,
            "messages": state.get("messages", []) + [
                {
                    "role": "system",
                    "content": f"Risk assessment completed. Identified {len(validated_risks)} risk flags."
                }
            ]
        }
    except Exception as e:
        logger.error(f"Error in extract_risks_node for contract {contract_id}: {str(e)}")
        return {
            "risks": [],
            "error": str(e),
            "messages": state.get("messages", []) + [{"role": "system", "content": f"Risk assessment node error: {str(e)}"}],
        }

def build_risk_graph():
    """
    Constructs the LangGraph state graph for the Risk Assessment Agent (Agent 3).
    """
    builder = StateGraph(ContractAnalysisState)
    builder.add_node("extract_risks", extract_risks_node)
    builder.add_edge(START, "extract_risks")
    builder.add_edge("extract_risks", END)
    
    return builder.compile()
