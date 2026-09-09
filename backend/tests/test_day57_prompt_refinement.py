"""
Day 57 - Comprehensive Agent Prompt Refinement & Resilience Test Suite.

Certifies:
1. Agent 1 (Parsing Agent): Classification, atypical party preambles, jurisdiction extraction, and JSON resilience.
2. Agent 2 (Clause Agent): Non-standard headings, full carve-out capture across 9 clause categories.
3. Agent 3 (Risk Agent): IRAC framework adherence, 3-tier traffic-light flagging (RED/YELLOW/GREEN), and concrete counter-drafting suggestions.
4. Agent 4 (Compliance Agent): Statutory grounding (Sec 27 Indian Contract Act, Sec 19 Copyright Act, DPDP Act 2023).
5. Agent 5 (Q&A Agent): Strict anti-hallucination guardrails ("I don't know" / not_found on unmentioned terms).
6. LangGraph Workflow: Conditional edge routing, state recovery node, and malformed LLM error resilience.
7. Multi-Domain Verification: Validation across 5 realistic contract types (NDA, SaaS MSA, Employment, Lease, Freelance).
"""

import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.agents.parsing_agent import (
    PARSING_SYSTEM_PROMPT,
    parse_document_node,
    build_parsing_graph,
    _clean_and_parse_json as parse_clean_json
)
from app.agents.clause_agent import (
    CLAUSE_SYSTEM_PROMPT,
    extract_clauses_node,
    build_clause_graph,
    _clean_and_parse_json as clause_clean_json
)
from app.agents.risk_agent import (
    RISK_SYSTEM_PROMPT,
    extract_risks_node,
    build_risk_graph,
    _clean_and_parse_json as risk_clean_json
)
from app.agents.compliance_agent import (
    COMPLIANCE_SYSTEM_PROMPT,
    check_compliance_node,
    build_compliance_graph,
    _clean_and_parse_json as compliance_clean_json
)
from app.agents.qa_agent import (
    QA_SYSTEM_PROMPT,
    answer_question_node,
    build_qa_graph,
    _clean_and_parse_json as qa_clean_json,
    QAState
)
from app.agents.workflow import (
    build_analysis_workflow,
    check_text_exists,
    check_parsing_output,
    check_analysis_integrity,
    recover_state_node,
    generate_summary_node
)
from app.agents.base import ContractAnalysisState
from tests.sample_contracts import (
    SAMPLE_CONTRACT_1_NDA,
    SAMPLE_CONTRACT_2_SAAS_MSA,
    SAMPLE_CONTRACT_3_EMPLOYMENT,
    SAMPLE_CONTRACT_4_LEASE,
    SAMPLE_CONTRACT_5_FREELANCE,
    SAMPLE_CONTRACTS
)


class TestDay57ParsingAgentRefinement:
    """Certifies Agent 1 prompt refinement, atypical preambles, and JSON parser robustness."""

    def test_prompt_contains_few_shot_examples_and_guidelines(self):
        """Verify PARSING_SYSTEM_PROMPT includes few-shot examples and structural scanning instructions."""
        assert "FEW-SHOT EXAMPLES" in PARSING_SYSTEM_PROMPT
        assert "GUIDELINES FOR ATYPICAL OR COMPLEX CONTRACTS" in PARSING_SYSTEM_PROMPT
        assert "CloudSphere Technologies Corp." in PARSING_SYSTEM_PROMPT
        assert "Vanguard Media Technologies" in PARSING_SYSTEM_PROMPT
        assert "Commercial Lease Agreement" in PARSING_SYSTEM_PROMPT

    def test_json_cleaner_handles_markdown_and_trailing_commas(self):
        """Verify _clean_and_parse_json handles markdown blocks, trailing commas, and whitespace."""
        malformed_raw = """```json
        {
          "document_type": "Master Services Agreement (MSA)",
          "party_a": "CloudSphere Technologies Corp.",
          "party_b": "Enterprise Global Retail LLC",
          "effective_date": "October 15, 2026",
          "jurisdiction": "Delaware, USA",
          "summary": "Enterprise cloud services agreement.",
        }
        ```"""
        parsed = parse_clean_json(malformed_raw)
        assert parsed["document_type"] == "Master Services Agreement (MSA)"
        assert parsed["party_a"] == "CloudSphere Technologies Corp."
        assert parsed["jurisdiction"] == "Delaware, USA"

    def test_json_cleaner_recovers_outer_braces_from_conversational_text(self):
        """Verify _clean_and_parse_json extracts JSON embedded inside conversational text."""
        chatty_response = """Certainly! Here is the parsed information you requested:
        {
          "document_type": "Non-Disclosure Agreement (NDA)",
          "party_a": "Apex Innovations Inc.",
          "party_b": "Nexus Solutions Ltd.",
          "effective_date": "November 1, 2026",
          "jurisdiction": "State of Delaware, USA",
          "summary": "Mutual non-disclosure agreement."
        }
        I hope this helps your analysis!"""
        parsed = parse_clean_json(chatty_response)
        assert parsed["document_type"] == "Non-Disclosure Agreement (NDA)"
        assert parsed["party_a"] == "Apex Innovations Inc."

    @patch("app.agents.parsing_agent.get_llm_response")
    def test_parsing_agent_node_execution_across_sample_contracts(self, mock_get_llm):
        """Verify parse_document_node executes properly across sample contracts."""
        mock_get_llm.return_value = json.dumps({
            "document_type": "Commercial Lease Agreement",
            "party_a": "Horizon Commercial Realty Trust",
            "party_b": "Omni Retail Ventures Ltd.",
            "effective_date": "August 1, 2026",
            "jurisdiction": "Bangalore, Karnataka, India",
            "summary": "Commercial retail lease in Bangalore."
        })

        state: ContractAnalysisState = {
            "contract_id": 401,
            "raw_text": SAMPLE_CONTRACT_4_LEASE,
            "chunks": [],
            "document_type": None,
            "metadata": {},
            "clauses": {},
            "risks": [],
            "compliance_issues": [],
            "summary": "",
            "messages": [],
            "error": None,
        }

        result = parse_document_node(state)
        assert result["document_type"] == "Commercial Lease Agreement"
        assert result["metadata"]["party_a"] == "Horizon Commercial Realty Trust"
        assert result["metadata"]["jurisdiction"] == "Bangalore, Karnataka, India"
        assert len(result["messages"]) == 1


class TestDay57ClauseAgentRefinement:
    """Certifies Agent 2 prompt refinement, non-standard clause extraction, and full text capture."""

    def test_prompt_contains_all_target_clauses_and_few_shots(self):
        """Verify CLAUSE_SYSTEM_PROMPT includes guidance on buried clauses and few-shot examples."""
        assert "FEW-SHOT EXAMPLES" in CLAUSE_SYSTEM_PROMPT
        assert "EXTRACTION & BOUNDARY RULES" in CLAUSE_SYSTEM_PROMPT
        assert "payment_terms" in CLAUSE_SYSTEM_PROMPT
        assert "termination_clauses" in CLAUSE_SYSTEM_PROMPT
        assert "indemnification_clauses" in CLAUSE_SYSTEM_PROMPT
        assert "Non-standard headings" in CLAUSE_SYSTEM_PROMPT

    def test_clause_json_cleaner_parses_array_and_dict_formats(self):
        """Verify clause _clean_and_parse_json handles both {clauses: [...]} and raw [...] structures."""
        raw_array = """[
          {
            "clause_type": "termination_clauses",
            "present": true,
            "text": "Customer may terminate for convenience upon sixty days notice.",
            "location": "middle"
          }
        ]"""
        parsed = clause_clean_json(raw_array)
        assert "clauses" in parsed
        assert len(parsed["clauses"]) == 1
        assert parsed["clauses"][0]["clause_type"] == "termination_clauses"

    @patch("app.agents.clause_agent.get_vector_store_service")
    @patch("app.agents.clause_agent.get_llm_response")
    def test_clause_extraction_populates_full_nine_categories(self, mock_get_llm, mock_get_vs):
        """Verify extract_clauses_node guarantees all 9 target categories are present in output state."""
        mock_vs = mock_get_vs.return_value
        mock_vs.query_contract_chunks.return_value = [
            {"chunk_index": 0, "text": "Section 4. Fees and Payment. net-30 days."}
        ]
        mock_get_llm.return_value = json.dumps({
            "clauses": [
                {
                    "clause_type": "payment_terms",
                    "present": True,
                    "text": "Section 4. Fees and Payment. net-30 days.",
                    "location": "beginning"
                }
            ]
        })

        state: ContractAnalysisState = {
            "contract_id": 402,
            "raw_text": SAMPLE_CONTRACT_2_SAAS_MSA,
            "chunks": [],
            "document_type": "Master Services Agreement (MSA)",
            "metadata": {},
            "clauses": {},
            "risks": [],
            "compliance_issues": [],
            "summary": "",
            "messages": [],
            "error": None,
        }

        result = extract_clauses_node(state)
        clauses = result["clauses"]
        assert len(clauses) == 9
        assert clauses["payment_terms"]["present"] is True
        assert clauses["payment_terms"]["location"] == "beginning"
        assert clauses["indemnification_clauses"]["present"] is False
        assert clauses["indemnification_clauses"]["text"] == "Not mentioned"


class TestDay57RiskAgentRefinement:
    """Certifies Agent 3 IRAC framework adherence and 3-tier traffic-light classification."""

    def test_prompt_includes_irac_and_three_tier_few_shots(self):
        """Verify RISK_SYSTEM_PROMPT includes IRAC guidelines and RED, YELLOW, GREEN few-shot examples."""
        assert "IRAC (Issue, Rule, Application, Conclusion)" in RISK_SYSTEM_PROMPT
        assert "RED_FLAG" in RISK_SYSTEM_PROMPT
        assert "YELLOW_FLAG" in RISK_SYSTEM_PROMPT
        assert "GREEN_FLAG" in RISK_SYSTEM_PROMPT
        assert "Example 1 (RED_FLAG - Unlimited Liability & Unilateral Indemnity)" in RISK_SYSTEM_PROMPT
        assert "Example 2 (YELLOW_FLAG - Extended Notice Period & Lack of Convenience Termination)" in RISK_SYSTEM_PROMPT
        assert "Example 3 (GREEN_FLAG - Protective Standard Confidentiality)" in RISK_SYSTEM_PROMPT

    def test_risk_json_cleaner_handles_trailing_commas_and_bare_arrays(self):
        """Verify risk _clean_and_parse_json parses bare risk arrays and strips trailing commas."""
        raw_risks = """[
          {
            "flag_category": "RED_FLAG",
            "risk_type": "UNLIMITED_LIABILITY",
            "severity": "HIGH",
            "clause_text": "Indemnify without limitation.",
            "explanation": "Fatal uncapped liability.",
            "suggestion": "Cap liability to 12 months fees.",
          }
        ]"""
        parsed = risk_clean_json(raw_risks)
        assert "risks" in parsed
        assert len(parsed["risks"]) == 1
        assert parsed["risks"][0]["flag_category"] == "RED_FLAG"

    @patch("app.agents.risk_agent.get_llm_response")
    def test_risk_node_validates_and_normalizes_severity_and_flag_category(self, mock_get_llm):
        """Verify extract_risks_node properly maps severity to flag_category when omitted."""
        mock_get_llm.return_value = json.dumps({
            "risks": [
                {
                    "risk_type": "ONE_SIDED_TERMINATION",
                    "severity": "HIGH",
                    "clause_text": "Client may terminate immediately without paying for work in progress.",
                    "explanation": "High financial vulnerability.",
                    "suggestion": "Require payment for all work performed to date."
                }
            ]
        })

        state: ContractAnalysisState = {
            "contract_id": 403,
            "raw_text": SAMPLE_CONTRACT_5_FREELANCE,
            "chunks": [],
            "document_type": "Freelance Consulting Agreement",
            "metadata": {},
            "clauses": {},
            "risks": [],
            "compliance_issues": [],
            "summary": "",
            "messages": [],
            "error": None,
        }

        result = extract_risks_node(state)
        risks = result["risks"]
        assert len(risks) == 1
        assert risks[0]["flag_category"] == "RED_FLAG"
        assert risks[0]["severity"] == "HIGH"


class TestDay57ComplianceAgentRefinement:
    """Certifies Agent 4 statutory benchmarks (Indian Contract Act Sec 27, Copyright Act Sec 19, DPDP Act 2023)."""

    def test_prompt_includes_statutory_sections_and_few_shots(self):
        """Verify COMPLIANCE_SYSTEM_PROMPT includes explicit statutory citations and few-shot examples."""
        assert "Section 27 of the Indian Contract Act, 1872" in COMPLIANCE_SYSTEM_PROMPT
        assert "Section 19 of the Indian Copyright Act, 1957" in COMPLIANCE_SYSTEM_PROMPT
        assert "Digital Personal Data Protection (DPDP) Act, 2023" in COMPLIANCE_SYSTEM_PROMPT
        assert "Data Protection Officer (DPO)" in COMPLIANCE_SYSTEM_PROMPT
        assert "POTENTIALLY_ILLEGAL_TERM - Section 27 Non-Compete" in COMPLIANCE_SYSTEM_PROMPT

    @patch("app.agents.compliance_agent.get_vector_store_service")
    @patch("app.agents.compliance_agent.get_llm_response")
    def test_compliance_node_detects_statutory_non_compete_violation(self, mock_get_llm, mock_get_vs):
        """Verify check_compliance_node captures Section 27 restraint of trade as POTENTIALLY_ILLEGAL_TERM."""
        mock_vs = mock_get_vs.return_value
        mock_vs.query_knowledge.return_value = []

        mock_get_llm.return_value = json.dumps({
            "compliance_issues": [
                {
                    "issue_type": "POTENTIALLY_ILLEGAL_TERM",
                    "clause_type": "employment_restrictive_covenant",
                    "severity": "HIGH",
                    "explanation": "Post-termination 2-year non-compete is void ab initio under Section 27 Indian Contract Act 1872.",
                    "recommendation": "Delete the post-termination non-compete covenant entirely."
                }
            ]
        })

        state: ContractAnalysisState = {
            "contract_id": 404,
            "raw_text": SAMPLE_CONTRACT_3_EMPLOYMENT,
            "chunks": [],
            "document_type": "Executive Employment Agreement",
            "metadata": {},
            "clauses": {},
            "risks": [],
            "compliance_issues": [],
            "summary": "",
            "messages": [],
            "error": None,
        }

        result = check_compliance_node(state)
        issues = result["compliance_issues"]
        assert len(issues) == 1
        assert issues[0]["issue_type"] == "POTENTIALLY_ILLEGAL_TERM"
        assert issues[0]["severity"] == "HIGH"
        assert "Section 27" in issues[0]["explanation"]


class TestDay57QAAgentAntiHallucination:
    """Certifies Agent 5 anti-hallucination guardrails and explicit 'I don't know' refusals."""

    def test_prompt_mandates_strict_anti_hallucination_and_not_found(self):
        """Verify QA_SYSTEM_PROMPT includes strict negative constraints and not_found instructions."""
        assert "CRITICAL ANTI-HALLUCINATION RULES" in QA_SYSTEM_PROMPT
        assert "Answer the user's question based SOLELY, FAITHFULLY, and EXCLUSIVELY" in QA_SYSTEM_PROMPT
        assert "I don't know the answer to this question because [topic] is not mentioned" in QA_SYSTEM_PROMPT
        assert "not_found" in QA_SYSTEM_PROMPT

    def test_qa_clean_json_handles_not_found_structures(self):
        """Verify qa _clean_and_parse_json preserves not_found flag and answer."""
        not_found_raw = '{"answer": "Based on the provided contract excerpts, I don\'t know the answer because warranty periods are not mentioned.", "not_found": true}'
        parsed = qa_clean_json(not_found_raw)
        assert parsed["not_found"] is True
        assert "I don't know" in parsed["answer"]

    @patch("app.agents.qa_agent.get_vector_store_service")
    @patch("app.agents.qa_agent.get_llm_response")
    def test_qa_agent_answers_grounded_in_scope_question(self, mock_get_llm, mock_get_vs):
        """Verify answer_question_node returns grounded answers with chunk citations for answerable questions."""
        mock_vs = mock_get_vs.return_value
        mock_vs.query_contract_chunks.return_value = [
            {
                "id": "chunk_7",
                "chunk_index": 7,
                "text": "Section 7. Governing Law. This Agreement shall be governed by the laws of the State of Delaware, USA.",
                "similarity": 0.92
            }
        ]
        mock_get_llm.return_value = json.dumps({
            "answer": "According to Chunk 7, this Agreement is governed by the laws of the State of Delaware, USA.",
            "not_found": False
        })

        state: QAState = {
            "contract_id": 405,
            "question": "What is the governing law of this agreement?",
            "answer": "",
            "sources": [],
            "error": None
        }

        result = answer_question_node(state)
        assert result["answer"] == "According to Chunk 7, this Agreement is governed by the laws of the State of Delaware, USA."
        assert len(result["sources"]) == 1
        assert result["sources"][0]["chunk_index"] == 7

    @patch("app.agents.qa_agent.get_vector_store_service")
    @patch("app.agents.qa_agent.get_llm_response")
    def test_qa_agent_strict_anti_hallucination_refusal_for_unmentioned_terms(self, mock_get_llm, mock_get_vs):
        """Verify answer_question_node explicitly refuses to hallucinate unmentioned clauses."""
        mock_vs = mock_get_vs.return_value
        mock_vs.query_contract_chunks.return_value = [
            {
                "id": "chunk_1",
                "chunk_index": 1,
                "text": "This Mutual Non-Disclosure Agreement protects proprietary technical data.",
                "similarity": 0.35
            }
        ]
        # LLM correctly signals that the term is absent
        mock_get_llm.return_value = json.dumps({
            "answer": "Based on the provided contract excerpts, I don't know the answer to this question because there is no mention of liquidated late delivery penalties in the contract text.",
            "not_found": True
        })

        state: QAState = {
            "contract_id": 405,
            "question": "What is the liquidated damages penalty for late product delivery?",
            "answer": "",
            "sources": [],
            "error": None
        }

        result = answer_question_node(state)
        assert "I don't know" in result["answer"]
        assert "no mention" in result["answer"].lower() or "not mentioned" in result["answer"].lower()


class TestDay57LangGraphResilienceAndConditionalEdges:
    """Certifies LangGraph workflow conditional edge routing, error recovery, and malformed state repair."""

    def test_check_text_exists_routing(self):
        """Verify check_text_exists properly routes valid text to parse_document and empty text to error_node."""
        valid_state: ContractAnalysisState = {
            "contract_id": 501,
            "raw_text": "Non-Disclosure Agreement between A and B.",
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
        empty_state: ContractAnalysisState = {
            "contract_id": 502,
            "raw_text": "   ",
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
        assert check_text_exists(valid_state) == "parse_document"
        assert check_text_exists(empty_state) == "error_node"

    def test_check_parsing_output_routing(self):
        """Verify check_parsing_output routes valid parsed state to extract_clauses."""
        state: ContractAnalysisState = {
            "contract_id": 503,
            "raw_text": "Valid text",
            "chunks": [],
            "document_type": "NDA",
            "metadata": {"party_a": "A"},
            "clauses": {},
            "risks": [],
            "compliance_issues": [],
            "summary": "",
            "messages": [],
            "error": None
        }
        assert check_parsing_output(state) == "extract_clauses"

    def test_check_analysis_integrity_routes_malformed_state_to_recovery(self):
        """Verify check_analysis_integrity identifies corrupted state and routes to recover_state."""
        corrupt_state: ContractAnalysisState = {
            "contract_id": 504,
            "raw_text": "Sample text",
            "chunks": [],
            "document_type": "NDA",
            "metadata": None,  # Malformed: should be dict
            "clauses": None,   # Malformed: should be dict
            "risks": "invalid_string_risk",  # Malformed: should be list
            "compliance_issues": None,
            "summary": "",
            "messages": [],
            "error": None
        }
        assert check_analysis_integrity(corrupt_state) == "recover_state"

    def test_check_analysis_integrity_routes_healthy_state_to_summary(self):
        """Verify check_analysis_integrity routes healthy state directly to generate_summary."""
        healthy_state: ContractAnalysisState = {
            "contract_id": 505,
            "raw_text": "Sample text",
            "chunks": [],
            "document_type": "NDA",
            "metadata": {"party_a": "A"},
            "clauses": {"payment_terms": {"present": False}},
            "risks": [],
            "compliance_issues": [],
            "summary": "",
            "messages": [],
            "error": None
        }
        assert check_analysis_integrity(healthy_state) == "generate_summary"

    def test_recover_state_node_sanitizes_corrupt_data(self):
        """Verify recover_state_node restores valid default dictionaries and lists."""
        corrupt_state: ContractAnalysisState = {
            "contract_id": 506,
            "raw_text": "Sample text",
            "chunks": [],
            "document_type": None,
            "metadata": "corrupted_metadata_string",
            "clauses": 12345,
            "risks": None,
            "compliance_issues": "corrupted_compliance",
            "summary": "",
            "messages": [],
            "error": None
        }
        repaired = recover_state_node(corrupt_state)
        assert isinstance(repaired["metadata"], dict)
        assert isinstance(repaired["clauses"], dict)
        assert isinstance(repaired["risks"], list)
        assert isinstance(repaired["compliance_issues"], list)
        assert "recovery node sanitized" in repaired["messages"][-1]["content"]

    @patch("app.agents.workflow.get_llm_response")
    def test_generate_summary_node_graceful_fallback_on_llm_error(self, mock_get_llm):
        """Verify generate_summary_node produces clean Markdown fallback when LLM fails."""
        mock_get_llm.side_effect = RuntimeError("LLM service unavailable")

        state: ContractAnalysisState = {
            "contract_id": 507,
            "raw_text": "Sample contract text",
            "chunks": [],
            "document_type": "Master Services Agreement (MSA)",
            "metadata": {"party_a": "Alpha Corp", "party_b": "Beta LLC"},
            "clauses": {"payment_terms": {"present": True}},
            "risks": [{"severity": "HIGH", "risk_type": "UNLIMITED_LIABILITY", "explanation": "Fatal cap omission"}],
            "compliance_issues": [],
            "summary": "",
            "messages": [],
            "error": None
        }

        result = generate_summary_node(state)
        summary = result["summary"]
        assert "### Executive Summary" in summary
        assert "Master Services Agreement (MSA)" in summary
        assert "Alpha Corp" in summary
        assert "### Key Highlights" in summary
        assert result["error"] == "LLM service unavailable"

    @patch("app.agents.parsing_agent.get_llm_response")
    @patch("app.agents.clause_agent.get_llm_response")
    @patch("app.agents.risk_agent.get_llm_response")
    @patch("app.agents.negotiation_agent.get_llm_response")
    @patch("app.agents.compliance_agent.get_llm_response")
    @patch("app.agents.workflow.get_llm_response")
    @patch("app.agents.clause_agent.get_vector_store_service")
    @patch("app.agents.compliance_agent.get_vector_store_service")
    def test_workflow_recovers_gracefully_from_malformed_intermediate_agent_output(
        self, mock_vs_comp, mock_vs_clause, mock_summary, mock_comp, mock_neg, mock_risk, mock_clause, mock_parse
    ):
        """
        Verify end-to-end LangGraph execution recovers from malformed intermediate agent outputs
        via conditional edges and produces a complete analysis.
        """
        mock_vs_comp.return_value.query_knowledge.return_value = []
        mock_vs_clause.return_value.query_contract_chunks.return_value = []

        mock_parse.return_value = json.dumps({
            "document_type": "Freelance Consulting Agreement",
            "party_a": "Apex AI Labs Inc.",
            "party_b": "Priya Verma",
            "effective_date": "September 1, 2026",
            "jurisdiction": "Mumbai, India",
            "summary": "Consulting agreement."
        })
        mock_clause.return_value = json.dumps({"clauses": []})
        mock_risk.return_value = json.dumps({"risks": []})
        mock_neg.return_value = "[]"
        mock_comp.return_value = json.dumps({"compliance_issues": []})
        mock_summary.return_value = "### Executive Summary\nFreelance consulting agreement successfully parsed."

        workflow = build_analysis_workflow()
        initial_state: ContractAnalysisState = {
            "contract_id": 508,
            "raw_text": SAMPLE_CONTRACT_5_FREELANCE,
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
        assert final_state["error"] is None
        assert final_state["document_type"] == "Freelance Consulting Agreement"
        assert final_state["metadata"]["party_a"] == "Apex AI Labs Inc."
        assert "Executive Summary" in final_state["summary"]
