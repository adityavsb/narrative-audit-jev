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
        """Analyze statement text for qualitative and quantitative claims with token boundaries."""
        c_lower = content.lower()

        # Regular expressions with word boundaries to prevent substring collisions
        re_margin = re.compile(
            r"\b(gross\s+margins?|margins?|unit\s+economics|operating\s+leverage|software\s+margins?|inference\s+costs?|cost\s+structure)\b"
        )
        re_capex = re.compile(
            r"\b(capex|capital\s+expenditures?|capital\s+investments?|generational|infrastructure|compute\s+capacity|tam|total\s+addressable\s+market)\b"
        )
        re_arr = re.compile(
            r"\b(arr|annual\s+recurring\s+revenue|milestone|ai-driven\s+revenue|database\s+renewals|platform\s+edition)\b"
        )
        re_adoption = re.compile(
            r"\b(copilot|adoption|customers?\s+enabled|customer\s+engagement)\b"
        )

        re_pos = re.compile(
            r"\b(expan\w*|stable|discipline\w*|strong\w*|high(?:er|est|ly)?|all-time|leverag\w*|validat\w*|outstand\w*|resilien\w*)\b"
        )
        re_neg = re.compile(
            r"\b(headwinds?|compress\w*|declin\w*|dilut\w*|contract(?:ed|ion|ing)|drop\w*|fell|erod\w*)\b"
        )
        re_negator = re.compile(r"\b(not|no|never|n't|without|neither)\b")

        claim_type = None
        metrics_mentioned = []

        if re_margin.search(c_lower):
            claim_type = "gross_margin"
            metrics_mentioned.extend(["gross_margin", "cost_of_goods_sold", "operating_income"])
        elif re_capex.search(c_lower):
            claim_type = "capex_efficiency"
            metrics_mentioned.extend(["capital_expenditures", "free_cash_flow"])
        elif re_arr.search(c_lower):
            claim_type = "ai_arr"
            metrics_mentioned.extend(["total_revenue", "segment_revenue"])
        elif re_adoption.search(c_lower):
            claim_type = "customer_adoption"
            metrics_mentioned.append("customer_adoption_rate")
        else:
            return None

        # Determine directional polarity with negation and mixed-sentiment handling
        pos_matches = list(re_pos.finditer(c_lower))
        neg_matches = list(re_neg.finditer(c_lower))

        def is_negated(match: re.Match) -> bool:
            window = c_lower[max(0, match.start() - 35): match.start()]
            return bool(re_negator.search(window))

        eff_pos = sum(1 for m in pos_matches if not is_negated(m)) + sum(1 for m in neg_matches if is_negated(m))
        eff_neg = sum(1 for m in neg_matches if not is_negated(m)) + sum(1 for m in pos_matches if is_negated(m))

        if eff_pos > 0 and eff_neg > 0:
            direction = "NEUTRAL"
        elif eff_pos > 0:
            direction = "EXPANSION"
        elif eff_neg > 0:
            direction = "CONTRACTION"
        else:
            direction = "NEUTRAL"

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

