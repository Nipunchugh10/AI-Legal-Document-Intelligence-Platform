"""
Comparison Service
------------------
Core algorithmic engine for semantic clause diffing, text-level delta matching,
and legal risk evolution computation between contract versions.

Day 38 — Contract Comparison Feature — Backend
"""

import difflib
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.comparison import (
    ClauseDiffItem,
    ComparisonMetrics,
    ComparisonResponse,
    DiffSegment,
    RiskProfileDelta,
)

logger = logging.getLogger(__name__)

STANDARD_CLAUSE_TAXONOMY = {
    "payment_terms": "Payment Terms & Milestones",
    "liability_clauses": "Liability Cap & Limitations",
    "termination_clauses": "Termination & Exit Provisions",
    "confidentiality_clauses": "Confidentiality & Non-Disclosure",
    "intellectual_property_clauses": "Intellectual Property & IP Assignment",
    "dispute_resolution_clauses": "Dispute Resolution & Arbitration",
    "governing_law": "Governing Law & Jurisdiction",
    "indemnification_clauses": "Indemnification & Third-Party Claims",
    "non_compete_clauses": "Non-Compete & Restrictive Covenants",
    "warranties_clauses": "Representations & Warranties",
    "severability_clauses": "Severability & Survival",
}


class ComparisonService:
    """Service that computes clause-level and text-level differences between two contracts."""

    @staticmethod
    def _extract_clause_text(clause_val: Any) -> str:
        """Normalizes extracted clause value to clean string text."""
        if not clause_val:
            return ""
        if isinstance(clause_val, dict):
            text = clause_val.get("text", "")
            return text.strip() if isinstance(text, str) else ""
        if isinstance(clause_val, str):
            return clause_val.strip()
        return str(clause_val).strip()

    @classmethod
    def compute_diff_segments(cls, base_text: str, target_text: str) -> List[DiffSegment]:
        """
        Generates word-level difference segments using Python difflib SequenceMatcher.
        Produces visual diff tokens with operations: 'equal', 'delete', 'insert', 'replace'.
        """
        base_words = re.findall(r"\S+|\s+", base_text) if base_text else []
        target_words = re.findall(r"\S+|\s+", target_text) if target_text else []

        matcher = difflib.SequenceMatcher(None, base_words, target_words)
        segments: List[DiffSegment] = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                text = "".join(base_words[i1:i2])
                if text:
                    segments.append(DiffSegment(operation="equal", text=text))
            elif tag == "delete":
                text = "".join(base_words[i1:i2])
                if text:
                    segments.append(DiffSegment(operation="delete", text=text))
            elif tag == "insert":
                text = "".join(target_words[j1:j2])
                if text:
                    segments.append(DiffSegment(operation="insert", text=text))
            elif tag == "replace":
                del_text = "".join(base_words[i1:i2])
                ins_text = "".join(target_words[j1:j2])
                if del_text:
                    segments.append(DiffSegment(operation="delete", text=del_text))
                if ins_text:
                    segments.append(DiffSegment(operation="insert", text=ins_text))

        return segments

    @classmethod
    def calculate_risk_profile(cls, risks: Optional[List[Dict[str, Any]]]) -> Tuple[int, int, int, int]:
        """
        Calculates mathematical risk score (0-100) and flag counts (Red, Yellow, Green).
        Red = +25 pts, Yellow = +10 pts, Green = -5 pts.
        """
        if not risks:
            return 0, 0, 0, 0

        red_count = 0
        yellow_count = 0
        green_count = 0

        for r in risks:
            category = r.get("flag_category") or r.get("severity") or ""
            cat_upper = category.upper()
            if "RED" in cat_upper or cat_upper == "HIGH":
                red_count += 1
            elif "YELLOW" in cat_upper or cat_upper == "MEDIUM":
                yellow_count += 1
            elif "GREEN" in cat_upper or cat_upper == "LOW":
                green_count += 1

        computed = red_count * 25 + yellow_count * 10 - green_count * 5
        score = min(100, max(0, computed)) if risks else 0
        return score, red_count, yellow_count, green_count

    @classmethod
    def compare_risk_profiles(
        cls,
        base_risks: Optional[List[Dict[str, Any]]],
        target_risks: Optional[List[Dict[str, Any]]],
    ) -> RiskProfileDelta:
        """Computes delta metrics and strategic narrative between baseline and target risks."""
        b_score, b_red, b_yellow, b_green = cls.calculate_risk_profile(base_risks)
        t_score, t_red, t_yellow, t_green = cls.calculate_risk_profile(target_risks)

        score_delta = t_score - b_score

        if score_delta <= -15 or (t_red < b_red):
            assessment = "Risk Reduced — The revised draft lowers contractual liability and includes more protective provisions."
        elif score_delta >= 15 or (t_red > b_red):
            assessment = "Risk Increased — The revised draft introduces higher liability exposure or more restrictive obligations."
        else:
            assessment = "Neutral / Comparable — Both contract versions maintain similar legal risk profiles."

        return RiskProfileDelta(
            base_risk_score=b_score,
            target_risk_score=t_score,
            score_delta=score_delta,
            base_red_flags=b_red,
            target_red_flags=t_red,
            base_yellow_flags=b_yellow,
            target_yellow_flags=t_yellow,
            base_green_flags=b_green,
            target_green_flags=t_green,
            assessment=assessment,
        )

    @classmethod
    def compare_clauses(
        cls,
        base_clauses: Dict[str, Any],
        target_clauses: Dict[str, Any],
    ) -> Tuple[List[ClauseDiffItem], int, int, int, int]:
        """
        Performs semantic clause-level diff across standard taxonomy keys and any custom discovered clauses.
        Returns: (clause_diffs, added_count, removed_count, modified_count, unchanged_count)
        """
        all_keys = list(STANDARD_CLAUSE_TAXONOMY.keys())
        for k in list(base_clauses.keys()) + list(target_clauses.keys()):
            if k not in all_keys:
                all_keys.append(k)

        clause_diffs: List[ClauseDiffItem] = []
        added_count = 0
        removed_count = 0
        modified_count = 0
        unchanged_count = 0

        for key in all_keys:
            base_val = base_clauses.get(key)
            target_val = target_clauses.get(key)

            base_text = cls._extract_clause_text(base_val)
            target_text = cls._extract_clause_text(target_val)

            title = STANDARD_CLAUSE_TAXONOMY.get(key, key.replace("_", " ").title())

            # 1. Check if both are empty/missing
            if not base_text and not target_text:
                continue

            # 2. Check if Added
            if not base_text and target_text:
                added_count += 1
                diff_segments = [DiffSegment(operation="insert", text=target_text)]
                clause_diffs.append(
                    ClauseDiffItem(
                        clause_key=key,
                        clause_title=title,
                        status="ADDED",
                        base_text=None,
                        target_text=target_text,
                        similarity_ratio=0.0,
                        diff_segments=diff_segments,
                    )
                )
                continue

            # 3. Check if Removed
            if base_text and not target_text:
                removed_count += 1
                diff_segments = [DiffSegment(operation="delete", text=base_text)]
                clause_diffs.append(
                    ClauseDiffItem(
                        clause_key=key,
                        clause_title=title,
                        status="REMOVED",
                        base_text=base_text,
                        target_text=None,
                        similarity_ratio=0.0,
                        diff_segments=diff_segments,
                    )
                )
                continue

            # 4. Both exist -> compute similarity ratio and diff
            matcher = difflib.SequenceMatcher(None, base_text, target_text)
            similarity = round(matcher.ratio(), 4)

            if similarity >= 0.99 or base_text == target_text:
                unchanged_count += 1
                clause_diffs.append(
                    ClauseDiffItem(
                        clause_key=key,
                        clause_title=title,
                        status="UNCHANGED",
                        base_text=base_text,
                        target_text=target_text,
                        similarity_ratio=1.0,
                        diff_segments=[DiffSegment(operation="equal", text=target_text)],
                    )
                )
            else:
                modified_count += 1
                diff_segments = cls.compute_diff_segments(base_text, target_text)
                clause_diffs.append(
                    ClauseDiffItem(
                        clause_key=key,
                        clause_title=title,
                        status="MODIFIED",
                        base_text=base_text,
                        target_text=target_text,
                        similarity_ratio=similarity,
                        diff_segments=diff_segments,
                    )
                )

        return clause_diffs, added_count, removed_count, modified_count, unchanged_count

    @classmethod
    def perform_comparison(
        cls,
        base_id: int,
        base_filename: str,
        base_text: str,
        base_analysis: Optional[Dict[str, Any]],
        target_id: int,
        target_filename: str,
        target_text: str,
        target_analysis: Optional[Dict[str, Any]],
    ) -> ComparisonResponse:
        """Executes complete full-text, clause-level, and risk profile comparison."""
        base_clauses = (base_analysis.get("clauses") if base_analysis else {}) or {}
        target_clauses = (target_analysis.get("clauses") if target_analysis else {}) or {}

        base_risks = (base_analysis.get("risks") if base_analysis else []) or []
        target_risks = (target_analysis.get("risks") if target_analysis else []) or []

        # 1. Clause level comparison
        clause_diffs, added, removed, modified, unchanged = cls.compare_clauses(base_clauses, target_clauses)

        # 2. Risk delta comparison
        risk_delta = cls.compare_risk_profiles(base_risks, target_risks)

        # 3. Text level word counts and overall similarity
        base_words = len(base_text.split()) if base_text else 0
        target_words = len(target_text.split()) if target_text else 0

        full_text_matcher = difflib.SequenceMatcher(None, base_text or "", target_text or "")
        full_text_similarity = round(full_text_matcher.ratio() * 100, 1)

        metrics = ComparisonMetrics(
            clauses_added_count=added,
            clauses_removed_count=removed,
            clauses_modified_count=modified,
            clauses_unchanged_count=unchanged,
            base_word_count=base_words,
            target_word_count=target_words,
            similarity_percentage=full_text_similarity,
        )

        # 4. Generate executive summary narrative
        summary_parts = [
            f"Compared baseline '{base_filename}' with target draft '{target_filename}'.",
            f"Overall text similarity is {full_text_similarity}%.",
            f"Identified {modified} modified clause(s), {added} added clause(s), {removed} removed clause(s), and {unchanged} unchanged clause(s).",
            f"Risk Score shifted from {risk_delta.base_risk_score} to {risk_delta.target_risk_score} (Delta: {risk_delta.score_delta:+d} points).",
            risk_delta.assessment,
        ]
        summary = " ".join(summary_parts)

        return ComparisonResponse(
            base_contract_id=base_id,
            base_filename=base_filename,
            target_contract_id=target_id,
            target_filename=target_filename,
            summary=summary,
            metrics=metrics,
            clause_diffs=clause_diffs,
            risk_delta=risk_delta,
        )
