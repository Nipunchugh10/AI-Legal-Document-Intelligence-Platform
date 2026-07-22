"""
Contract Schemas
----------------
Pydantic schemas for document (contract) upload and retrieval.

Day 5 — File Upload System
"""

from datetime import datetime
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


