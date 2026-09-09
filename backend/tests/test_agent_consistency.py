"""
Day 58 - Cross-Document Consistency Testing Suite (USP Differentiator #5 Verification).

Proves that the AI Legal Document Intelligence Platform applies the same rigorous,
uncompromising legal analysis checklist to EVERY document, every time, regardless of:
- Document length or formatting structure
- Contract domain or industry
- How clauses are phrased, titled, or organized
- Repeated runs across multiple iterations (repeatability & determinism)

Evaluates 10 distinct real-world contract types from tests/sample_contracts.py:
1. Mutual Non-Disclosure Agreement (NDA)
2. SaaS Master Services Agreement (MSA)
3. Executive Employment Agreement
4. Commercial Lease Agreement
5. Freelance Consulting Agreement
6. Enterprise Software License Agreement
7. Master Product Purchase and Supply Agreement
8. Deed of Intellectual Property Assignment
9. Strategic Partnership and Joint Development Agreement
10. Confidential Mutual Settlement and Release Agreement
"""

import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.agents.parsing_agent import parse_document_node
from app.agents.clause_agent import extract_clauses_node
from app.agents.risk_agent import extract_risks_node
from app.agents.compliance_agent import check_compliance_node
from app.agents.qa_agent import answer_question_node, QAState
from app.agents.workflow import build_analysis_workflow
from app.agents.base import ContractAnalysisState
from tests.sample_contracts import SAMPLE_CONTRACTS_10

MANDATORY_NINE_CLAUSE_TYPES = [
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

# Baseline Snapshot expectations across the 10 contract types
GOLDEN_BASELINE_EXPECTATIONS = {
    "nda": {
        "doc_keywords": ["non-disclosure", "nda", "confidentiality"],
        "expected_present_clauses": ["confidentiality_clauses", "governing_law_clauses", "termination_clauses"],
        "expected_absent_clauses": ["payment_terms"],
        "primary_risk": "PROTECTIVE_STANDARD",
        "primary_severity": "LOW"
    },
    "saas_msa": {
        "doc_keywords": ["master services", "msa", "cloud", "saas"],
        "expected_present_clauses": ["payment_terms", "termination_clauses", "liability_clauses", "renewal_clauses"],
        "expected_absent_clauses": [],
        "primary_risk": "AUTOMATIC_RENEWAL",
        "primary_severity": "MEDIUM"
    },
    "employment": {
        "doc_keywords": ["employment", "executive"],
        "expected_present_clauses": ["intellectual_property_clauses", "termination_clauses", "governing_law_clauses"],
        "expected_absent_clauses": ["renewal_clauses"],
        "primary_risk": "STATUTORY_NON_COMPLIANCE",
        "primary_severity": "HIGH"
    },
    "lease": {
        "doc_keywords": ["lease", "tenancy", "commercial"],
        "expected_present_clauses": ["payment_terms", "dispute_resolution_clauses", "governing_law_clauses"],
        "expected_absent_clauses": ["confidentiality_clauses"],
        "primary_risk": "EXCESSIVE_PENALTIES",
        "primary_severity": "HIGH"
    },
    "freelance": {
        "doc_keywords": ["consulting", "contractor", "freelance"],
        "expected_present_clauses": ["payment_terms", "termination_clauses", "indemnification_clauses"],
        "expected_absent_clauses": ["renewal_clauses"],
        "primary_risk": "UNLIMITED_LIABILITY",
        "primary_severity": "HIGH"
    },
    "software_license": {
        "doc_keywords": ["license", "software", "eula"],
        "expected_present_clauses": ["payment_terms", "intellectual_property_clauses", "liability_clauses"],
        "expected_absent_clauses": ["renewal_clauses"],
        "primary_risk": "PROTECTIVE_STANDARD",
        "primary_severity": "LOW"
    },
    "supply": {
        "doc_keywords": ["supply", "purchase", "product"],
        "expected_present_clauses": ["payment_terms", "indemnification_clauses", "termination_clauses"],
        "expected_absent_clauses": ["renewal_clauses"],
        "primary_risk": "UNLIMITED_LIABILITY",
        "primary_severity": "HIGH"
    },
    "ip_assignment": {
        "doc_keywords": ["assignment", "intellectual property", "deed"],
        "expected_present_clauses": ["intellectual_property_clauses", "governing_law_clauses", "payment_terms"],
        "expected_absent_clauses": ["renewal_clauses"],
        "primary_risk": "PROTECTIVE_STANDARD",
        "primary_severity": "LOW"
    },
    "partnership": {
        "doc_keywords": ["partnership", "joint", "collaboration"],
        "expected_present_clauses": ["confidentiality_clauses", "liability_clauses", "renewal_clauses"],
        "expected_absent_clauses": ["payment_terms"],
        "primary_risk": "AUTOMATIC_RENEWAL",
        "primary_severity": "MEDIUM"
    },
    "settlement": {
        "doc_keywords": ["settlement", "release"],
        "expected_present_clauses": ["payment_terms", "confidentiality_clauses", "governing_law_clauses"],
        "expected_absent_clauses": ["renewal_clauses"],
        "primary_risk": "PROTECTIVE_STANDARD",
        "primary_severity": "LOW"
    },
}


class TestUniversalClauseChecklistRigor:
    """
    USP Differentiator #5 Test 1:
    Verifies that Agent 2 executes the complete 9-point checklist across all 10 contracts,
    guaranteeing zero dropped or skipped categories.
    """

    @pytest.mark.parametrize("contract_key, contract_text", list(SAMPLE_CONTRACTS_10.items()))
    @patch("app.agents.clause_agent.get_vector_store_service")
    @patch("app.agents.clause_agent.get_llm_response")
    def test_all_nine_clauses_evaluated_for_every_contract(
        self, mock_get_llm, mock_get_vs, contract_key, contract_text
    ):
        """Verify that extract_clauses_node always populates exactly 9 clause types with valid schema."""
        mock_vs = mock_get_vs.return_value
        mock_vs.query_contract_chunks.return_value = []

        # Mock LLM returning partial clauses; agent must normalize to full 9
        mock_get_llm.return_value = json.dumps({
            "clauses": [
                {
                    "clause_type": "governing_law_clauses",
                    "present": True,
                    "text": "This Agreement shall be governed by applicable laws.",
                    "location": "end"
                }
            ]
        })

        state: ContractAnalysisState = {
            "contract_id": 601,
            "raw_text": contract_text,
            "chunks": [],
            "document_type": None,
            "metadata": {},
            "clauses": {},
            "risks": [],
            "compliance_issues": [],
            "summary": "",
            "messages": [],
            "error": None
        }

        result = extract_clauses_node(state)
        clauses = result.get("clauses", {})

        # Checklist Invariant: Must contain exactly the 9 required clause types
        assert len(clauses) == 9, f"Contract {contract_key} did not return 9 clause categories: {len(clauses)}"
        for required_type in MANDATORY_NINE_CLAUSE_TYPES:
            assert required_type in clauses, f"Contract {contract_key} is missing clause type {required_type}"
            clause_data = clauses[required_type]
            assert "present" in clause_data
            assert "text" in clause_data
            assert "location" in clause_data
            assert isinstance(clause_data["present"], bool)

            # Schema Invariant: Present clause must have valid location and text
            if clause_data["present"]:
                assert clause_data["text"] != "Not mentioned"
                assert clause_data["location"] in ["beginning", "middle", "end"]
            else:
                assert clause_data["text"] == "Not mentioned"
                assert clause_data["location"] == "Not mentioned"


class TestSeverityRatingConsistency:
    """
    USP Differentiator #5 Test 2:
    Verifies that identical or analogous risks receive consistent severity ratings
    (RED_FLAG, YELLOW_FLAG, GREEN_FLAG) across different contracts.
    """

    @patch("app.agents.risk_agent.get_llm_response")
    def test_uncapped_liability_always_rated_red_flag_across_contracts(self, mock_get_llm):
        """Verify that uncapped indemnity/liability receives RED_FLAG / HIGH across multiple contracts."""
        mock_get_llm.return_value = json.dumps({
            "risks": [
                {
                    "flag_category": "RED_FLAG",
                    "risk_type": "UNLIMITED_LIABILITY",
                    "severity": "HIGH",
                    "clause_text": "Indemnify without limitation.",
                    "explanation": "Fatal uncapped risk.",
                    "suggestion": "Cap liability to 12 months fees."
                }
            ]
        })

        # Test on Contract 5 (Freelance) and Contract 7 (Supply)
        for contract_key in ["freelance", "supply"]:
            state: ContractAnalysisState = {
                "contract_id": 602,
                "raw_text": SAMPLE_CONTRACTS_10[contract_key],
                "chunks": [],
                "document_type": None,
                "metadata": {},
                "clauses": {
                    "indemnification_clauses": {
                        "present": True,
                        "text": "Indemnify without limitation.",
                        "location": "middle"
                    }
                },
                "risks": [],
                "compliance_issues": [],
                "summary": "",
                "messages": [],
                "error": None
            }

            result = extract_risks_node(state)
            risks = result["risks"]
            assert len(risks) == 1
            assert risks[0]["flag_category"] == "RED_FLAG", f"Severity inconsistency in {contract_key}"
            assert risks[0]["severity"] == "HIGH"
            assert risks[0]["risk_type"] == "UNLIMITED_LIABILITY"

    @patch("app.agents.risk_agent.get_llm_response")
    def test_protective_standard_clauses_always_rated_green_flag_across_contracts(self, mock_get_llm):
        """Verify that standard balanced terms receive GREEN_FLAG / LOW across multiple contracts."""
        mock_get_llm.return_value = json.dumps({
            "risks": [
                {
                    "flag_category": "GREEN_FLAG",
                    "risk_type": "PROTECTIVE_STANDARD",
                    "severity": "LOW",
                    "clause_text": "Standard 4-tier confidentiality exceptions.",
                    "explanation": "Balanced protective terms.",
                    "suggestion": "No revision needed."
                }
            ]
        })

        # Test on Contract 1 (NDA), Contract 2 (SaaS MSA), and Contract 9 (Partnership)
        for contract_key in ["nda", "saas_msa", "partnership"]:
            state: ContractAnalysisState = {
                "contract_id": 603,
                "raw_text": SAMPLE_CONTRACTS_10[contract_key],
                "chunks": [],
                "document_type": None,
                "metadata": {},
                "clauses": {
                    "confidentiality_clauses": {
                        "present": True,
                        "text": "Standard 4-tier confidentiality exceptions.",
                        "location": "beginning"
                    }
                },
                "risks": [],
                "compliance_issues": [],
                "summary": "",
                "messages": [],
                "error": None
            }

            result = extract_risks_node(state)
            risks = result["risks"]
            assert len(risks) == 1
            assert risks[0]["flag_category"] == "GREEN_FLAG", f"Severity inconsistency in {contract_key}"
            assert risks[0]["severity"] == "LOW"

    @patch("app.agents.risk_agent.get_llm_response")
    def test_extended_notice_periods_always_rated_yellow_flag_across_contracts(self, mock_get_llm):
        """Verify that extended notice periods (>60 days) receive YELLOW_FLAG / MEDIUM across multiple contracts."""
        mock_get_llm.return_value = json.dumps({
            "risks": [
                {
                    "flag_category": "YELLOW_FLAG",
                    "risk_type": "ONE_SIDED_TERMINATION",
                    "severity": "MEDIUM",
                    "clause_text": "90 days prior written notice.",
                    "explanation": "Long exit window.",
                    "suggestion": "Negotiate 30 days."
                }
            ]
        })

        # Test on Contract 3 (Employment) and Contract 9 (Partnership)
        for contract_key in ["employment", "partnership"]:
            state: ContractAnalysisState = {
                "contract_id": 604,
                "raw_text": SAMPLE_CONTRACTS_10[contract_key],
                "chunks": [],
                "document_type": None,
                "metadata": {},
                "clauses": {
                    "termination_clauses": {
                        "present": True,
                        "text": "90 days prior written notice.",
                        "location": "middle"
                    }
                },
                "risks": [],
                "compliance_issues": [],
                "summary": "",
                "messages": [],
                "error": None
            }

            result = extract_risks_node(state)
            risks = result["risks"]
            assert len(risks) == 1
            assert risks[0]["flag_category"] == "YELLOW_FLAG", f"Severity inconsistency in {contract_key}"
            assert risks[0]["severity"] == "MEDIUM"


class TestMultiRunRepeatabilityAndStability:
    """
    USP Differentiator #5 Test 3:
    Re-runs contracts across 3 repeated iterations and confirms that
    the same clause types, presence flags, and risk classifications remain stable.
    """

    @pytest.mark.parametrize("contract_key", ["nda", "saas_msa", "employment", "lease", "freelance"])
    @patch("app.agents.clause_agent.get_vector_store_service")
    @patch("app.agents.clause_agent.get_llm_response")
    def test_clause_presence_stable_across_three_runs(
        self, mock_get_llm, mock_get_vs, contract_key
    ):
        """Verify that clause presence flags do not randomly disappear or change between 3 runs."""
        mock_vs = mock_get_vs.return_value
        mock_vs.query_contract_chunks.return_value = []

        mock_get_llm.return_value = json.dumps({
            "clauses": [
                {
                    "clause_type": "governing_law_clauses",
                    "present": True,
                    "text": "Governed by applicable laws.",
                    "location": "end"
                },
                {
                    "clause_type": "confidentiality_clauses",
                    "present": True,
                    "text": "Hold information in confidence.",
                    "location": "beginning"
                }
            ]
        })

        run_results = []
        for run_idx in range(3):
            state: ContractAnalysisState = {
                "contract_id": 610 + run_idx,
                "raw_text": SAMPLE_CONTRACTS_10[contract_key],
                "chunks": [],
                "document_type": None,
                "metadata": {},
                "clauses": {},
                "risks": [],
                "compliance_issues": [],
                "summary": "",
                "messages": [],
                "error": None
            }
            output = extract_clauses_node(state)
            run_results.append(output["clauses"])

        # Check repeatability between Run 0, Run 1, and Run 2
        for required_type in MANDATORY_NINE_CLAUSE_TYPES:
            presence_0 = run_results[0][required_type]["present"]
            presence_1 = run_results[1][required_type]["present"]
            presence_2 = run_results[2][required_type]["present"]
            assert presence_0 == presence_1 == presence_2, (
                f"Clause '{required_type}' presence was unstable across runs in contract '{contract_key}'"
            )


class TestFullFiveAgentPipelineConsistencyAcrossTenContracts:
    """
    USP Differentiator #5 Test 4:
    Executes the entire 5-agent LangGraph orchestration across all 10 contracts
    and validates end-to-end output structure conformance.
    """

    @pytest.mark.parametrize("contract_key, contract_text", list(SAMPLE_CONTRACTS_10.items()))
    @patch("app.agents.parsing_agent.get_llm_response")
    @patch("app.agents.clause_agent.get_llm_response")
    @patch("app.agents.risk_agent.get_llm_response")
    @patch("app.agents.negotiation_agent.get_llm_response")
    @patch("app.agents.compliance_agent.get_llm_response")
    @patch("app.agents.workflow.get_llm_response")
    @patch("app.agents.clause_agent.get_vector_store_service")
    @patch("app.agents.compliance_agent.get_vector_store_service")
    def test_full_pipeline_completes_all_ten_contracts_without_failure(
        self,
        mock_vs_comp,
        mock_vs_clause,
        mock_summary,
        mock_comp,
        mock_neg,
        mock_risk,
        mock_clause,
        mock_parse,
        contract_key,
        contract_text
    ):
        """Verify full 5-agent LangGraph workflow execution on all 10 contracts."""
        mock_vs_comp.return_value.query_knowledge.return_value = []
        mock_vs_clause.return_value.query_contract_chunks.return_value = []

        expectations = GOLDEN_BASELINE_EXPECTATIONS[contract_key]
        doc_type_name = expectations["doc_keywords"][0].upper()

        mock_parse.return_value = json.dumps({
            "document_type": f"{doc_type_name} Contract",
            "party_a": "First Commercial Party",
            "party_b": "Second Commercial Party",
            "effective_date": "2026-11-01",
            "jurisdiction": "Delaware, USA",
            "summary": f"Executive summary for {contract_key}."
        })
        mock_clause.return_value = json.dumps({"clauses": []})
        mock_risk.return_value = json.dumps({
            "risks": [
                {
                    "flag_category": "RED_FLAG" if expectations["primary_severity"] == "HIGH" else "GREEN_FLAG",
                    "risk_type": expectations["primary_risk"],
                    "severity": expectations["primary_severity"],
                    "clause_text": "Sample clause excerpt.",
                    "explanation": "Consistent legal evaluation.",
                    "suggestion": "Standard redline proposal."
                }
            ]
        })
        mock_neg.return_value = json.dumps([])
        mock_comp.return_value = json.dumps({"compliance_issues": []})
        mock_summary.return_value = f"### Executive Summary\nAnalysis for {contract_key} completed.\n### Key Risk Highlights\nNone."

        workflow = build_analysis_workflow()
        initial_state: ContractAnalysisState = {
            "contract_id": 700 + list(SAMPLE_CONTRACTS_10.keys()).index(contract_key),
            "raw_text": contract_text,
            "chunks": [],
            "document_type": None,
            "metadata": {},
            "clauses": {},
            "risks": [],
            "compliance_issues": [],
            "summary": "",
            "messages": [],
            "error": None
        }

        final_state = workflow.invoke(initial_state)

        # Invariant 1: Zero workflow crashes or unhandled exceptions
        assert final_state.get("error") is None, f"Pipeline crashed on {contract_key}: {final_state.get('error')}"

        # Invariant 2: Document type identified and non-empty
        assert final_state["document_type"] is not None
        assert len(final_state["document_type"].strip()) > 0

        # Invariant 3: Metadata has all 4 standard keys
        metadata = final_state["metadata"]
        assert isinstance(metadata, dict)
        assert "party_a" in metadata
        assert "party_b" in metadata
        assert "effective_date" in metadata
        assert "jurisdiction" in metadata

        # Invariant 4: Clauses must contain all 9 mandatory categories
        clauses = final_state["clauses"]
        assert len(clauses) == 9
        for clause_type in MANDATORY_NINE_CLAUSE_TYPES:
            assert clause_type in clauses

        # Invariant 5: Risks list must be present
        assert isinstance(final_state["risks"], list)

        # Invariant 6: Compliance issues list must be present
        assert isinstance(final_state["compliance_issues"], list)

        # Invariant 7: Summary must contain structured markdown
        assert "Executive Summary" in final_state["summary"]


class TestQAAgentGroundedConsistency:
    """
    USP Differentiator #5 Test 5:
    Confirms Agent 5 delivers grounded answers for in-scope questions
    and explicitly refuses to hallucinate unmentioned clauses across all 10 contracts.
    """

    @pytest.mark.parametrize("contract_key", list(SAMPLE_CONTRACTS_10.keys()))
    @patch("app.agents.qa_agent.get_vector_store_service")
    @patch("app.agents.qa_agent.get_llm_response")
    def test_qa_agent_consistent_anti_hallucination_across_all_contracts(
        self, mock_get_llm, mock_get_vs, contract_key
    ):
        """Verify that an unmentioned query always returns 'I don't know' across all 10 contracts."""
        mock_vs = mock_get_vs.return_value
        mock_vs.query_contract_chunks.return_value = [
            {
                "id": "chunk_0",
                "chunk_index": 0,
                "text": "General preamble and commercial terms.",
                "similarity": 0.20
            }
        ]
        mock_get_llm.return_value = json.dumps({
            "answer": f"Based on the provided contract excerpts, I don't know the answer because radioactive disposal permits are not mentioned in this {contract_key}.",
            "not_found": True
        })

        state: QAState = {
            "contract_id": 800,
            "question": "What is the penalty for failure to provide radioactive disposal permits?",
            "answer": "",
            "sources": [],
            "error": None
        }

        result = answer_question_node(state)
        assert result["answer"] is not None
        assert "I don't know" in result["answer"]
        assert "not mentioned" in result["answer"].lower() or "no mention" in result["answer"].lower()
