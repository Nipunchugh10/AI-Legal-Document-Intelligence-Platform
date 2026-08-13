import json
import re
import logging
from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END
from app.agents.base import ContractAnalysisState
from app.services.llm_provider import get_llm_response

logger = logging.getLogger(__name__)

RISK_SYSTEM_PROMPT = """You are an Elite Senior Attorney & Legal Risk Analysis Agent.
Your task is to analyze contract text using the IRAC (Issue, Rule, Application, Conclusion) legal reasoning framework and classify findings into a 3-Tier Traffic Light Flagging System:

1. "RED_FLAG" (Critical / Fatal Exposure — DO NOT SIGN WITHOUT NEGOTIATING):
   - Uncapped liabilities, broad indemnity carve-outs, illegal post-employment non-compete covenants (e.g. void under Section 27 Contract Act), one-sided termination forfeiture, automatic pre-existing IP surrenders, unilateral agreement modification, cross-default accelerations, defective title exposure.

2. "YELLOW_FLAG" (Small Concerns — VERIFY WITH LAWYER BEFORE SIGNING):
   - Mild ambiguities, missing notice period details, unindexed rent escalations, vague force majeure or pandemic clauses, seat vs venue arbitration ambiguities, long notice periods (>90 days), subjective performance KPIs.

3. "GREEN_FLAG" (Protective & Standard Market Terms — NO ISSUE / FAVORABLE):
   - Capped liability (e.g., 1x contract value), mutual indemnities, standard 4-tier confidentiality exclusions, clear 30-day exit notices, statutory compliance guarantees, balanced IP carve-outs.

For each item evaluated, return a structured object with:
- "flag_category": Exactly one of "RED_FLAG", "YELLOW_FLAG", or "GREEN_FLAG".
- "risk_type": Category identifier (e.g., "UNLIMITED_LIABILITY", "ONE_SIDED_TERMINATION", "AUTOMATIC_RENEWAL", "BROAD_IP_ASSIGNMENT", "UNILATERAL_MODIFICATION", "EXCESSIVE_PENALTIES", "BROAD_CONFIDENTIALITY", "STATUTORY_NON_COMPLIANCE", "PROTECTIVE_STANDARD").
- "severity": "HIGH" for RED_FLAG, "MEDIUM" for YELLOW_FLAG, "LOW" for GREEN_FLAG.
- "clause_text": Exact quote or relevant text snippet from the document.
- "explanation": Plain-English breakdown explaining why this is a Red Flag, Yellow Concern, or Green Protection.
- "suggestion": Exact action or redline counter-draft recommendation for negotiating with opposing counsel or confirming with a lawyer.

Return ONLY a valid, clean JSON object with a single key "risks" containing a list of risk items.
Do NOT include markdown formatting, backticks (like ```json), or text before/after the JSON.
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

    prompt = f"{RISK_SYSTEM_PROMPT}\n\n{context_header}\n---\n{context}\n---"

    try:
        llm_response = get_llm_response(prompt, temperature=0.0, contract_id=contract_id)
        parsed_data = _clean_and_parse_json(llm_response)
        risks_list = parsed_data.get("risks", [])

        validated_risks = []
        for risk in risks_list:
            flag_cat = risk.get("flag_category")
            severity = risk.get("severity", "MEDIUM")
            if not flag_cat:
                if severity == "HIGH":
                    flag_cat = "RED_FLAG"
                elif severity == "LOW":
                    flag_cat = "GREEN_FLAG"
                else:
                    flag_cat = "YELLOW_FLAG"

            validated_risks.append({
                "flag_category": flag_cat,
                "risk_type": risk.get("risk_type", "UNKNOWN"),
                "severity": severity,
                "clause_text": risk.get("clause_text", "Not mentioned"),
                "explanation": risk.get("explanation", "Potential finding detected."),
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
