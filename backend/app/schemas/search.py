"""
Search Schemas
--------------
Pydantic schemas for Day 40 Semantic Search across contracts.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class SearchChunkResult(BaseModel):
    """Represents a matching text chunk from a contract."""
    chunk_index: int = Field(..., description="Index of the chunk in the document")
    text: str = Field(..., description="Raw text of the matching chunk")
    similarity: float = Field(..., description="Cosine similarity score (0.0 - 1.0)")
    highlighted_text: Optional[str] = Field(
        None, description="Chunk text with search keywords highlighted with <mark> tags"
    )


class ContractSearchResult(BaseModel):
    """Represents a contract matching the semantic search query."""
    contract_id: int
    filename: str
    document_type: Optional[str] = Field("Uncategorized", description="Document type from parsed analysis")
    risk_level: Optional[str] = Field("UNKNOWN", description="Risk level (CRITICAL, HIGH, MEDIUM, LOW, SAFE)")
    risk_score: Optional[int] = Field(None, description="0-100 overall risk evaluation score")
    created_at: datetime
    status: str
    max_similarity: float = Field(..., description="Highest similarity score among matching chunks")
    match_count: int = Field(..., description="Total number of matching chunks for this contract")
    matching_chunks: List[SearchChunkResult] = Field(
        default_factory=list, description="Top matching text excerpts"
    )


class SemanticSearchResponse(BaseModel):
    """API response model for GET /contracts/search."""
    query: str
    total_contracts_matched: int
    total_chunks_matched: int
    results: List[ContractSearchResult]
