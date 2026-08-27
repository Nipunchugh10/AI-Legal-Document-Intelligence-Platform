"""
Comparison Schemas
------------------
Pydantic schemas for multi-version contract difference and semantic clause change detection.

Day 38 — Contract Comparison Feature — Backend
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ComparisonRequest(BaseModel):
    """Payload for comparing two contracts."""

    base_contract_id: int = Field(..., description="ID of the original/baseline contract")
    target_contract_id: int = Field(..., description="ID of the revised/target contract to compare against")


class DiffSegment(BaseModel):
    """A segment of text in a diff representation."""

    operation: str = Field(..., description="'equal', 'insert', 'delete', or 'replace'")
    text: str = Field(..., description="Text content for this segment")


class ClauseDiffItem(BaseModel):
    """Clause-level comparison result."""

    clause_key: str = Field(..., description="Key identifier of the clause (e.g. liability_clauses, payment_terms)")
    clause_title: str = Field(..., description="Human-readable title of the clause")
    status: str = Field(..., description="'ADDED', 'REMOVED', 'MODIFIED', or 'UNCHANGED'")
    base_text: Optional[str] = Field(None, description="Text in the baseline contract")
    target_text: Optional[str] = Field(None, description="Text in the target/revised contract")
    similarity_ratio: float = Field(..., description="Similarity score between 0.0 and 1.0")
    diff_segments: List[DiffSegment] = Field(default_factory=list, description="Word-level diff tokens for visual rendering")


class RiskProfileDelta(BaseModel):
    """Comparison of risk exposure and flag counts between versions."""

    base_risk_score: int = Field(..., description="Risk score of the base contract (0-100)")
    target_risk_score: int = Field(..., description="Risk score of the target contract (0-100)")
    score_delta: int = Field(..., description="Difference in risk score (target - base)")
    base_red_flags: int = Field(..., description="Critical Red Flag count in base contract")
    target_red_flags: int = Field(..., description="Critical Red Flag count in target contract")
    base_yellow_flags: int = Field(..., description="Moderate Concern count in base contract")
    target_yellow_flags: int = Field(..., description="Moderate Concern count in target contract")
    base_green_flags: int = Field(..., description="Protective count in base contract")
    target_green_flags: int = Field(..., description="Protective count in target contract")
    assessment: str = Field(..., description="Summary of risk evolution (e.g., 'Risk Reduced', 'Risk Increased', 'Neutral')")


class ComparisonMetrics(BaseModel):
    """Quantitative metrics summarizing changes between versions."""

    clauses_added_count: int = Field(..., description="Number of newly added clauses")
    clauses_removed_count: int = Field(..., description="Number of removed clauses")
    clauses_modified_count: int = Field(..., description="Number of modified clauses")
    clauses_unchanged_count: int = Field(..., description="Number of unchanged clauses")
    base_word_count: int = Field(..., description="Total word count of baseline document")
    target_word_count: int = Field(..., description="Total word count of target document")
    similarity_percentage: float = Field(..., description="Overall full-text similarity percentage (0-100)")


class ComparisonResponse(BaseModel):
    """Full comparison payload returned by the diff endpoint."""

    base_contract_id: int = Field(..., description="ID of baseline contract")
    base_filename: str = Field(..., description="Filename of baseline contract")
    target_contract_id: int = Field(..., description="ID of target/revised contract")
    target_filename: str = Field(..., description="Filename of target/revised contract")
    summary: str = Field(..., description="Executive summary of contractual changes and risk impact")
    metrics: ComparisonMetrics = Field(..., description="Quantitative comparison metrics")
    clause_diffs: List[ClauseDiffItem] = Field(..., description="List of clause differences")
    risk_delta: RiskProfileDelta = Field(..., description="Risk score and flag count comparison")
