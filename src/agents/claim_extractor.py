"""Qualitative claim extractor for earnings call transcripts and footnote disclosures."""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional
import duckdb

from src.agents.state import ClaimExtraction
from src.db.financial_queries import get_transcript_text


class ClaimExtractor:
    """Extracts structured qualitative claims from corporate transcripts and disclosures."""

    def __init__(self, llm_client: Optional[Callable[[str], List[Dict[str, Any]]]] = None):
        self.llm_client = llm_client

    def extract_from_transcript_rows(
        self,
        ticker: str,
        fiscal_year: int,
        fiscal_quarter: str,
        rows: List[Dict[str, Any]],
    ) -> List[ClaimExtraction]:
        """Extract claims from a list of transcript dictionary rows."""
        claims: List[ClaimExtraction] = []

        for idx, row in enumerate(rows):
            content = row.get("content", "")
            speaker = row.get("speaker_name", "Executive")
            title = row.get("speaker_title", "Leadership")

            # Extract any substantive forward-looking or operational assertions
            extracted = self._analyze_statement(
                ticker=ticker,
                fiscal_year=fiscal_year,
                fiscal_quarter=fiscal_quarter,
                claim_id=f"{ticker}_{fiscal_year}_{fiscal_quarter}_claim_{idx+1}",
                speaker_name=speaker,
                speaker_title=title,
                content=content,
            )
            if extracted:
                claims.append(extracted)

        return claims

    def extract_from_db(
        self,
        conn: duckdb.DuckDBPyConnection,
        ticker: str,
        fiscal_year: int,
        fiscal_quarter: str,
    ) -> List[ClaimExtraction]:
        """Extract claims directly by querying transcript table in DuckDB."""
        transcript_rows = get_transcript_text(
            conn, ticker=ticker, fiscal_year=fiscal_year, fiscal_quarter=fiscal_quarter
        )
        return self.extract_from_transcript_rows(
            ticker=ticker,
            fiscal_year=fiscal_year,
            fiscal_quarter=fiscal_quarter,
            rows=transcript_rows,
        )

    def _analyze_statement(
        self,
        ticker: str,
        fiscal_year: int,
        fiscal_quarter: str,
        claim_id: str,
        speaker_name: str,
        speaker_title: str,
        content: str,
    ) -> Optional[ClaimExtraction]:
        """Analyze statement text for qualitative and quantitative claims."""
        c_lower = content.lower()

        # Identify claim type & mentioned metrics
        claim_type = None
        metrics_mentioned = []
        direction = "NEUTRAL"

        # 1. Gross margin, unit economics & operating leverage
        if any(w in c_lower for w in ["gross margin", "margin", "unit economics", "operating leverage", "software margin", "inference cost", "cost structure"]):
            claim_type = "gross_margin"
            metrics_mentioned.extend(["gross_margin", "cost_of_goods_sold", "operating_income"])
            if any(w in c_lower for w in ["expand", "stable", "discipline", "strong", "high", "all-time", "leverag", "validat", "outstand"]):
                direction = "EXPANSION"
            elif any(w in c_lower for w in ["headwind", "compress", "decline", "dilut", "contract", "drop"]):
                direction = "CONTRACTION"

        # 2. Capital expenditure & infrastructure investments
        elif any(w in c_lower for w in ["capex", "capital expenditure", "capital investment", "generational", "infrastructure", "compute capacity", "tam"]):
            claim_type = "capex_efficiency"
            metrics_mentioned.extend(["capital_expenditures", "free_cash_flow"])
            if any(w in c_lower for w in ["invest", "aggressive", "scale", "expansion", "growth", "generational"]):
                direction = "EXPANSION"

        # 3. AI ARR & Product revenue milestones
        elif any(w in c_lower for w in ["arr", "annual recurring revenue", "milestone", "ai-driven revenue", "database renewals", "platform edition"]):
            claim_type = "ai_arr"
            metrics_mentioned.extend(["total_revenue", "segment_revenue"])
            direction = "EXPANSION"

        # 4. Customer adoption & engagement
        elif any(w in c_lower for w in ["copilot", "adoption", "customers enabled", "customer engagement"]):
            claim_type = "customer_adoption"
            metrics_mentioned.append("customer_adoption_rate")
            direction = "EXPANSION"

        # If no specific audit-relevant pattern is detected, return None
        if not claim_type:
            return None

        return ClaimExtraction(
            claim_id=claim_id,
            ticker=ticker,
            fiscal_year=fiscal_year,
            fiscal_quarter=fiscal_quarter,
            speaker_name=speaker_name,
            speaker_title=speaker_title,
            statement=content.strip(),
            claim_type=claim_type,
            metrics_mentioned=metrics_mentioned,
            sentiment_direction=direction,
        )
