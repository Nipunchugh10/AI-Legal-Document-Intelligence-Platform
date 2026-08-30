"""
Search Service
--------------
Core service for Day 40 Semantic Search across user contracts.
Performs vector similarity search via ChromaDB, merges relational metadata,
applies multi-attribute filtering (document type, risk level, date range),
and computes keyword highlight snippets.
"""

import re
import html
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.analysis import Analysis
from app.services.vector_store import get_vector_store_service
from app.schemas.search import (
    SearchChunkResult,
    ContractSearchResult,
    SemanticSearchResponse,
)


class SearchService:
    """Service handling multi-contract semantic search, filtering, and text highlighting."""

    @staticmethod
    def highlight_query_terms(text: str, query: str) -> str:
        """
        Highlight search terms inside text snippet using <mark> HTML tags.
        Escapes HTML characters in the text and applies case-insensitive word boundary matching.
        """
        if not text or not query:
            return html.escape(text or "")

        safe_text = html.escape(text)
        # Extract meaningful keywords (length >= 2, alphanumeric)
        keywords = [
            re.escape(k.strip())
            for k in re.split(r"\s+", query)
            if len(k.strip()) >= 2
        ]

        if not keywords:
            return safe_text

        pattern = re.compile(rf"(?i)\b({'|'.join(keywords)})\b")
        return pattern.sub(r"<mark>\1</mark>", safe_text)

    @classmethod
    def search_user_contracts(
        cls,
        db: Session,
        user_id: int,
        query: str,
        limit: int = 10,
        document_type: Optional[str] = None,
        risk_level: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        contract_id: Optional[int] = None,
        min_similarity: float = 0.0,
    ) -> SemanticSearchResponse:
        """
        Executes semantic search across all contracts owned by the user.
        Merges ChromaDB vector cosine similarities with PostgreSQL relational metadata.
        """
        clean_query = query.strip()
        if not clean_query:
            return SemanticSearchResponse(
                query=query,
                total_contracts_matched=0,
                total_chunks_matched=0,
                results=[],
            )

        # 1. Fetch user's contracts matching base constraints
        contract_query = db.query(Contract).filter(Contract.user_id == user_id)

        if contract_id:
            contract_query = contract_query.filter(Contract.id == contract_id)
        if date_from:
            contract_query = contract_query.filter(Contract.created_at >= date_from)
        if date_to:
            contract_query = contract_query.filter(Contract.created_at <= date_to)

        user_contracts = contract_query.all()
        if not user_contracts:
            return SemanticSearchResponse(
                query=clean_query,
                total_contracts_matched=0,
                total_chunks_matched=0,
                results=[],
            )

        contract_map = {c.id: c for c in user_contracts}
        contract_ids = list(contract_map.keys())

        # 2. Fetch analysis metadata (parsed doc type, risk score & level) for these contracts
        analyses = (
            db.query(Analysis)
            .filter(Analysis.contract_id.in_(contract_ids))
            .all()
        )

        doc_type_map: Dict[int, str] = {}
        risk_map: Dict[int, Dict[str, Any]] = {}

        for a in analyses:
            cid = a.contract_id
            if a.analysis_type == "parsed" and a.result_json:
                doc_type_map[cid] = a.result_json.get("document_type") or "Uncategorized"

            elif a.analysis_type == "risks" and a.result_json:
                res = a.result_json
                score = res.get("risk_score")
                
                # Determine risk level from score or flag counts
                red_count = 0
                yellow_count = 0
                risk_items = res.get("risks", []) or res.get("risk_flags", [])
                for r in risk_items:
                    severity = str(r.get("severity") or r.get("level") or "").upper()
                    if "RED" in severity or "CRITICAL" in severity or "HIGH" in severity:
                        red_count += 1
                    elif "YELLOW" in severity or "MODERATE" in severity or "MEDIUM" in severity:
                        yellow_count += 1

                if score is not None:
                    if score >= 70:
                        computed_level = "CRITICAL"
                    elif score >= 40:
                        computed_level = "HIGH"
                    elif score >= 20:
                        computed_level = "MEDIUM"
                    else:
                        computed_level = "LOW"
                else:
                    if red_count >= 2:
                        computed_level = "CRITICAL"
                    elif red_count == 1:
                        computed_level = "HIGH"
                    elif yellow_count >= 1:
                        computed_level = "MEDIUM"
                    else:
                        computed_level = "SAFE"

                risk_map[cid] = {
                    "risk_score": score,
                    "risk_level": computed_level,
                }

        # 3. Perform vector similarity search in ChromaDB
        vector_store = get_vector_store_service()
        # Request enough chunks to cover multi-contract distribution
        raw_chunks = vector_store.query_user_contracts(
            contract_ids=contract_ids,
            query_text=clean_query,
            n_results=max(limit * 8, 30),
            min_similarity=min_similarity,
        )

        # 4. Group matching chunks by contract_id
        grouped_chunks: Dict[int, List[Dict[str, Any]]] = {}
        for chunk in raw_chunks:
            cid = chunk.get("contract_id")
            if cid in contract_map:
                if cid not in grouped_chunks:
                    grouped_chunks[cid] = []
                grouped_chunks[cid].append(chunk)

        # 5. Build results with metadata and filter matching
        contract_results: List[ContractSearchResult] = []
        total_matched_chunks = 0

        for cid, contract in contract_map.items():
            chunks_for_contract = grouped_chunks.get(cid, [])
            if not chunks_for_contract:
                continue

            c_doc_type = doc_type_map.get(cid, "Uncategorized")
            c_risk_info = risk_map.get(cid, {"risk_score": None, "risk_level": "UNKNOWN"})
            c_risk_level = c_risk_info.get("risk_level", "UNKNOWN")
            c_risk_score = c_risk_info.get("risk_score")

            # Apply document_type filter if requested (case-insensitive substring)
            if document_type:
                dt_filter = document_type.strip().lower()
                if dt_filter not in c_doc_type.lower() and dt_filter not in contract.filename.lower():
                    continue

            # Apply risk_level filter if requested
            if risk_level:
                rl_filter = risk_level.strip().upper()
                if rl_filter != c_risk_level.upper():
                    continue

            # Format top matching chunks
            formatted_chunks: List[SearchChunkResult] = []
            max_sim = 0.0

            for chunk_data in chunks_for_contract:
                sim = float(chunk_data.get("similarity", 0.0))
                if sim > max_sim:
                    max_sim = sim
                
                raw_text = chunk_data.get("text", "")
                highlighted = cls.highlight_query_terms(raw_text, clean_query)

                formatted_chunks.append(
                    SearchChunkResult(
                        chunk_index=int(chunk_data.get("chunk_index", 0)),
                        text=raw_text,
                        similarity=sim,
                        highlighted_text=highlighted,
                    )
                )

            total_matched_chunks += len(formatted_chunks)

            contract_results.append(
                ContractSearchResult(
                    contract_id=cid,
                    filename=contract.filename,
                    document_type=c_doc_type,
                    risk_level=c_risk_level,
                    risk_score=c_risk_score,
                    created_at=contract.created_at,
                    status=contract.status,
                    max_similarity=round(max_sim, 4),
                    match_count=len(formatted_chunks),
                    matching_chunks=formatted_chunks[:5],  # top 5 chunks per contract
                )
            )

        # 6. Sort contracts by highest similarity score descending
        contract_results.sort(key=lambda x: x.max_similarity, reverse=True)
        paginated_results = contract_results[:limit]

        return SemanticSearchResponse(
            query=clean_query,
            total_contracts_matched=len(contract_results),
            total_chunks_matched=total_matched_chunks,
            results=paginated_results,
        )
