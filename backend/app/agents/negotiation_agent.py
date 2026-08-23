import logging
import json
from typing import Dict, Any, List
from app.agents.base import ContractAnalysisState
from app.services.llm_provider import get_llm_response

logger = logging.getLogger(__name__)

NEGOTIATION_ADVISOR_PROMPT = """You are an expert Legal Negotiation Advisor.
Your task is to review a list of identified legal risks in a contract and provide:
1. `suggested_revision`: Specific, concrete redline contract text that the user can copy-paste to replace or amend the risky clause. Make it legally sound and balanced (protecting the user's interests while keeping it reasonable).
2. `negotiation_tip`: Contextual tactical advice on how the user should frame this during negotiations (e.g. "Frame this as a standard industry practice, not as distrust.").

Review the following risks:
{risks_json}

Provide your suggestions in a structured JSON list matching this format:
[
  {{
    "risk_type": "RISK_TYPE_HERE",
    "clause_text": "EXACT_CLAUSE_TEXT_HERE",
    "suggested_revision": "Redlined clause text...",
    "negotiation_tip": "Tactical advice..."
  }}
]

Important:
- Only generate suggestions for risks with HIGH or MEDIUM severity.
- Ensure the JSON is valid and strictly matches the keys.
- Return ONLY the raw JSON array. Do NOT wrap the response in markdown blocks like ```json or ```.
"""

def negotiation_advisor_node(state: ContractAnalysisState) -> Dict[str, Any]:
    """
    LangGraph node: For each HIGH and MEDIUM risk, calls Gemini LLM to generate
    specific redline revision suggestions and negotiation tips.
    """
    contract_id = state.get("contract_id", 0)
    risks = state.get("risks", [])

    # Filter for HIGH and MEDIUM severity risks
    target_risks = [
        r for r in risks 
        if r.get("severity") in ("HIGH", "MEDIUM")
    ]

    if not target_risks:
        logger.info(f"No HIGH or MEDIUM risks found for contract {contract_id}. Skipping negotiation advisor.")
        return {
            "risks": risks,
            "messages": state.get("messages", []) + [{"role": "system", "content": "Negotiation advisor skipped: no high or medium risks."}]
        }

    # Format target risks for LLM prompt
    risks_to_send = []
    for r in target_risks:
        risks_to_send.append({
            "risk_type": r.get("risk_type"),
            "severity": r.get("severity"),
            "clause_text": r.get("clause_text"),
            "explanation": r.get("explanation"),
            "suggestion": r.get("suggestion")
        })

    risks_json_str = json.dumps(risks_to_send, indent=2)
    prompt = NEGOTIATION_ADVISOR_PROMPT.format(risks_json=risks_json_str)

    try:
        response_text = get_llm_response(prompt, temperature=0.1, contract_id=contract_id)
        
        # Clean response text if model wrapped it in markdown code blocks
        clean_text = response_text.strip()
        if clean_text.startswith("```"):
            lines = clean_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            clean_text = "\n".join(lines).strip()

        advice_list = json.loads(clean_text)
        
        # Create lookup map for suggestions based on risk_type + clause_text
        advice_map = {}
        for item in advice_list:
            key = (item.get("risk_type"), item.get("clause_text"))
            advice_map[key] = {
                "suggested_revision": item.get("suggested_revision"),
                "negotiation_tip": item.get("negotiation_tip")
            }

        # Update matching risks in-place
        updated_risks = []
        for r in risks:
            key = (r.get("risk_type"), r.get("clause_text"))
            if key in advice_map:
                advice = advice_map[key]
                r["suggested_revision"] = advice.get("suggested_revision") or r.get("suggested_revision")
                r["negotiation_tip"] = advice.get("negotiation_tip") or r.get("negotiation_tip")
            updated_risks.append(r)

        return {
            "risks": updated_risks,
            "messages": state.get("messages", []) + [{"role": "system", "content": f"Negotiation suggestions added to {len(advice_list)} risks."}]
        }

    except Exception as e:
        logger.error(f"Error in negotiation_advisor_node: {str(e)}")
        # In case of LLM/JSON failure, fallback to copying original suggestions to avoid crashing
        updated_risks = []
        for r in risks:
            if r.get("severity") in ("HIGH", "MEDIUM"):
                r["suggested_revision"] = r.get("suggested_revision") or r.get("suggestion")
                r["negotiation_tip"] = r.get("negotiation_tip") or "Discuss this clause with counsel to align terms."
            updated_risks.append(r)

        return {
            "risks": updated_risks,
            "messages": state.get("messages", []) + [{"role": "system", "content": f"Negotiation advisor fallback applied: {str(e)}"}]
        }
