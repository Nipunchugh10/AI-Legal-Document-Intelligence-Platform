"""
Contract Schemas
----------------
Pydantic schemas for document (contract) upload and retrieval.

Day 5 — File Upload System
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class ContractResponse(BaseModel):
    """Returned when a contract is successfully uploaded or queried."""

    id: int = Field(..., description="Unique database ID of the contract")
    user_id: int = Field(..., description="ID of the user who owns this contract")
    filename: str = Field(..., description="Original filename of the uploaded contract")
    upload_path: str = Field(..., description="Local file path where the PDF is stored")
    status: str = Field(..., description="Processing status of the contract (pending, ingested, analyzed, failed)")
    created_at: datetime = Field(..., description="Timestamp of when the contract was uploaded")

    model_config = {"from_attributes": True}


class TextExtractionResponse(BaseModel):
    """Returned when a contract's text is successfully extracted."""

    contract_id: int
    page_count: int
    is_scanned: bool
    strategy: str
    text: str


class ChunkingResponse(BaseModel):
    """Returned when a contract's text is successfully chunked."""

    contract_id: int
    chunk_count: int
    chunks: list[str]


class ParsingAgentResponse(BaseModel):
    """Returned when a contract is analyzed by the Document Parsing Agent (Agent 1)."""

    contract_id: int
    document_type: str
    party_a: str
    party_b: str
    effective_date: str
    jurisdiction: str
    summary: str


class ClauseItem(BaseModel):
    """A single extracted clause item."""

    text: str = Field(..., description="The exact text of the clause extracted from the contract")
    location: str = Field(..., description="Approximate location in the document (beginning, middle, end, or Not mentioned)")
    present: bool = Field(..., description="Whether this clause type was found present in the contract")


class ClauseAgentResponse(BaseModel):
    """Returned when a contract is analyzed by the Clause Detection Agent (Agent 2)."""

    contract_id: int
    clauses: dict[str, ClauseItem] = Field(..., description="Map of clause_type to its details")


class RiskItem(BaseModel):
    """A single identified risk flag."""

    risk_type: str = Field(..., description="Type of the risk (e.g., UNLIMITED_LIABILITY, ONE_SIDED_TERMINATION, etc.)")
    severity: str = Field(..., description="Risk severity: HIGH, MEDIUM, or LOW")
    clause_text: str = Field(..., description="The contract clause text associated with the risk")
    explanation: str = Field(..., description="Explanation of why this is a risk")
    suggestion: str = Field(..., description="Actionable suggestion for negotiation")
    suggested_revision: Optional[str] = Field(None, description="Redline revision language to replace or amend the clause")
    negotiation_tip: Optional[str] = Field(None, description="Tactical advice for negotiating this clause")


class RiskAgentResponse(BaseModel):
    """Returned when a contract is analyzed by the Risk Assessment Agent (Agent 3)."""

    contract_id: int
    risks: list[RiskItem] = Field(..., description="List of identified risk items")


class ComplianceIssueItem(BaseModel):
    """A single identified compliance issue."""

    issue_type: str = Field(..., description="Type of compliance issue: MISSING_REQUIRED_CLAUSE, POTENTIALLY_ILLEGAL_TERM, DPDP_COMPLIANCE_ISSUE")
    clause_type: str = Field(..., description="The type of clause associated with the compliance issue")
    severity: str = Field(..., description="Severity level: HIGH, MEDIUM, or LOW")
    explanation: str = Field(..., description="Explanation of the compliance issue")
    recommendation: str = Field(..., description="Actionable recommendation to achieve compliance")


class ComplianceAgentResponse(BaseModel):
    """Returned when a contract is analyzed by the Compliance Agent (Agent 4)."""

    contract_id: int
    compliance_issues: list[ComplianceIssueItem] = Field(..., description="List of identified compliance issues")


class QASourceItem(BaseModel):
    """A source snippet chunk cited by the QA agent."""

    chunk_index: int = Field(..., description="The index of the contract chunk used as a source")
    text: str = Field(..., description="The content of the contract snippet")
    similarity: float = Field(..., description="The semantic similarity score of the chunk to the question")


class QARequest(BaseModel):
    """Payload for asking a question about a contract."""

    question: str = Field(..., description="The natural language question about the contract")


class QAResponse(BaseModel):
    """Returned when a contract question is answered."""

    contract_id: int = Field(..., description="Database ID of the contract")
    question: str = Field(..., description="The question that was asked")
    answer: str = Field(..., description="The generated answer, grounded in the contract")
    sources: list[QASourceItem] = Field(..., description="The list of cited sources from the contract")


class AnalysisWorkflowResponse(BaseModel):
    """Returned when the full contract analysis workflow runs successfully."""

    contract_id: int = Field(..., description="Database ID of the analyzed contract")
    status: str = Field(..., description="The status of the analysis workflow")
    document_type: str = Field(..., description="The classified document type")
    metadata: dict[str, Any] = Field(..., description="The parsed document metadata (parties, date, jurisdiction)")
    clauses: dict[str, Any] = Field(..., description="The extracted legal clauses")
    risks: list[dict[str, Any]] = Field(..., description="The identified risk items")
    compliance_issues: list[dict[str, Any]] = Field(..., description="The identified compliance issues")
    summary: str = Field(..., description="The generated Markdown executive summary report")


