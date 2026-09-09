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
   - Uncapped liabilities, broad unilateral indemnities, illegal post-employment non-compete covenants (e.g. void under Section 27 Indian Contract Act), one-sided termination forfeiture, automatic pre-existing IP surrenders, unilateral agreement modification, cross-default accelerations, defective title exposure.

2. "YELLOW_FLAG" (Small Concerns — VERIFY WITH LAWYER BEFORE SIGNING):
   - Mild ambiguities, missing notice period details, unindexed rent escalations, vague force majeure clauses, seat vs venue arbitration ambiguities, long notice periods (>60 days), subjective performance KPIs.

3. "GREEN_FLAG" (Protective & Standard Market Terms — NO ISSUE / FAVORABLE):
   - Capped liability (e.g., 1x annual contract value), mutual indemnities, standard 4-tier confidentiality exclusions, clear 30-day exit notices, statutory compliance guarantees, balanced IP carve-outs.

FEW-SHOT EXAMPLES:

Example 1 (RED_FLAG - Unlimited Liability & Unilateral Indemnity):
Input Clause:
"Service Provider shall indemnify, defend, and hold harmless Client against any and all claims, losses, and damages without limitation. In no event shall Client be liable for any indirect, consequential, or punitive damages."
Output Risk Object:
{
  "flag_category": "RED_FLAG",
  "risk_type": "UNLIMITED_LIABILITY",
  "severity": "HIGH",
  "clause_text": "Service Provider shall indemnify, defend, and hold harmless Client against any and all claims, losses, and damages without limitation. In no event shall Client be liable for any indirect, consequential, or punitive damages.",
  "explanation": "IRAC Analysis - Issue: Uncapped unilateral liability and one-sided waiver of consequential damages. Rule: Commercial contracts should maintain mutual liability caps and reciprocal consequential damage waivers. Application: Service Provider faces unlimited financial catastrophe for third-party claims while Client caps its own exposure completely. Conclusion: Highly dangerous asymmetrical risk allocation.",
  "suggestion": "Replace with: 'Each party's maximum aggregate liability under this Agreement shall be capped at the total fees paid or payable by Client in the twelve (12) months preceding the claim. Neither party shall be liable for indirect, incidental, or consequential damages, and indemnification obligations shall be mutual.'"
}

Example 2 (YELLOW_FLAG - Extended Notice Period & Lack of Convenience Termination):
Input Clause:
"Contractor may only terminate this Agreement upon ninety (90) days prior written notice, and only in the event of Client's uncured material breach. Client may terminate at any time."
Output Risk Object:
{
  "flag_category": "YELLOW_FLAG",
  "risk_type": "ONE_SIDED_TERMINATION",
  "severity": "MEDIUM",
  "clause_text": "Contractor may only terminate this Agreement upon ninety (90) days prior written notice, and only in the event of Client's uncured material breach. Client may terminate at any time.",
  "explanation": "IRAC Analysis - Issue: Disproportionately long 90-day notice and lack of mutual termination for convenience. Rule: Standard consulting contracts provide 30-day mutual termination for convenience. Application: Contractor is locked in for three months with no exit right even if project conditions deteriorate. Conclusion: Medium commercial impediment requiring negotiation.",
  "suggestion": "Negotiate: 'Either party may terminate this Agreement for convenience upon thirty (30) days prior written notice, provided that Client pays Contractor for all work completed up to the termination effective date.'"
}

Example 3 (GREEN_FLAG - Protective Standard Confidentiality):
Input Clause:
"Confidential Information does not include information that: (a) is or becomes publicly known through no breach; (b) was already in recipient's rightful possession; (c) is independently developed without reference to the disclosing party's information; or (d) is required to be disclosed by law or court order."
Output Risk Object:
{
  "flag_category": "GREEN_FLAG",
  "risk_type": "PROTECTIVE_STANDARD",
  "severity": "LOW",
  "clause_text": "Confidential Information does not include information that: (a) is or becomes publicly known through no breach; (b) was already in recipient's rightful possession; (c) is independently developed without reference to the disclosing party's information; or (d) is required to be disclosed by law or court order.",
  "explanation": "IRAC Analysis - Issue: Scope of non-disclosure exceptions. Rule: Industry-standard 4-tier carve-out protects recipient from undue liability. Application: Clearly excludes public, pre-existing, independently developed, and legally mandated disclosures. Conclusion: Balanced, highly protective standard market terms.",
  "suggestion": "Clause conforms to best practice legal standards. No revision required."
}

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

    cleaned_fixed = re.sub(r",\s*([\]}])", r"\1", cleaned)

    try:
        data = json.loads(cleaned_fixed)
        if isinstance(data, list):
            return {"risks": data}
        if isinstance(data, dict):
            if "risks" in data:
                return data
            if "flag_category" in data or "risk_type" in data:
                return {"risks": [data]}
            return data
        return {"risks": []}
    except json.JSONDecodeError:
        # Fallback 1: match array
        array_match = re.search(r"\[.*\]", cleaned_fixed, re.DOTALL)
        if array_match:
            try:
                data = json.loads(array_match.group(0))
                if isinstance(data, list):
                    return {"risks": data}
            except json.JSONDecodeError:
                pass

        # Fallback 2: match outermost JSON object
        match = re.search(r"\{.*\}", cleaned_fixed, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                if isinstance(data, dict):
                    if "risks" in data:
                        return data
                    if "flag_category" in data or "risk_type" in data:
                        return {"risks": [data]}
                    return data
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
