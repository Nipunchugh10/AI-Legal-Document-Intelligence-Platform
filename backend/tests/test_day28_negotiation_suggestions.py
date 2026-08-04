import sys
import os
import pytest
from unittest.mock import patch
from app.agents.negotiation_agent import negotiation_advisor_node
from app.agents.workflow import build_analysis_workflow
from app.agents.base import ContractAnalysisState

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock LLM response specifically for negotiation advisor
MOCK_NEGOTIATION_RESPONSE = """
[
  {
    "risk_type": "UNLIMITED_LIABILITY",
    "clause_text": "The contractor shall have unlimited liability for any claims.",
    "suggested_revision": "Notwithstanding the above, the total liability of either party shall not exceed the total fees paid under this agreement.",
    "negotiation_tip": "Frame this as standard commercial risk balancing."
  }
]
"""

def test_negotiation_advisor_node_adds_suggestions():
    initial_risks = [
        {
            "risk_type": "UNLIMITED_LIABILITY",
            "severity": "HIGH",
            "clause_text": "The contractor shall have unlimited liability for any claims.",
            "explanation": "Unlimited liability is a high risk.",
            "suggestion": "Cap the liability."
        },
        {
            "risk_type": "LOW_RISK_EXAMPLE",
            "severity": "LOW",
            "clause_text": "Standard governing law clause.",
            "explanation": "No issue.",
            "suggestion": "None."
        }
    ]

    initial_state: ContractAnalysisState = {
        "contract_id": 123,
        "raw_text": "Dummy text.",
        "chunks": [],
        "document_type": None,
        "metadata": {},
        "clauses": {},
        "risks": initial_risks,
        "compliance_issues": [],
        "summary": "",
        "messages": [],
        "error": None
    }

    with patch("app.agents.negotiation_agent.get_llm_response") as mock_llm:
        mock_llm.return_value = MOCK_NEGOTIATION_RESPONSE

        final_state = negotiation_advisor_node(initial_state)
        
        # Verify that HIGH risk got suggested_revision and negotiation_tip
        high_risk = next(r for r in final_state["risks"] if r["risk_type"] == "UNLIMITED_LIABILITY")
        assert high_risk.get("suggested_revision") == "Notwithstanding the above, the total liability of either party shall not exceed the total fees paid under this agreement."
        assert high_risk.get("negotiation_tip") == "Frame this as standard commercial risk balancing."

        # Verify that LOW risk did not get suggested_revision (as it wasn't requested from the LLM)
        low_risk = next(r for r in final_state["risks"] if r["risk_type"] == "LOW_RISK_EXAMPLE")
        assert low_risk.get("suggested_revision") is None

def test_negotiation_advisor_node_skipped_on_no_high_medium_risks():
    initial_risks = [
        {
            "risk_type": "LOW_RISK_1",
            "severity": "LOW",
            "clause_text": "Clause text.",
            "explanation": "Explanation.",
            "suggestion": "Suggestion."
        }
    ]

    initial_state: ContractAnalysisState = {
        "contract_id": 123,
        "raw_text": "Dummy text.",
        "chunks": [],
        "document_type": None,
        "metadata": {},
        "clauses": {},
        "risks": initial_risks,
        "compliance_issues": [],
        "summary": "",
        "messages": [],
        "error": None
    }

    with patch("app.agents.negotiation_agent.get_llm_response") as mock_llm:
        final_state = negotiation_advisor_node(initial_state)
        
        # LLM should not be called because there are no HIGH/MEDIUM risks
        mock_llm.assert_not_called()
        assert final_state["risks"] == initial_risks
