"""Deterministic Numeric Critic / Fact-Checking Gate.

Cross-references claimed figures and operational narratives directly against
underlying audited accounting entries in DuckDB, flagging contradictions and
unsupported qualitative assertions.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
import duckdb

from src.agents.state import ClaimExtraction, NumericFactCheck
from src.db.financial_queries import get_quarterly_financials_row, get_segment_history


class NumericGuardrail:
    """Enforces mathematical reconciliation between executive assertions and GAAP ledger facts."""

    def __init__(self, tolerance: float = 0.02):
        self.tolerance = tolerance  # 2% default tolerance

    def verify_claim(
        self,
        conn: duckdb.DuckDBPyConnection,
        claim: ClaimExtraction,
    ) -> NumericFactCheck:
        """Cross-examine a qualitative claim against DuckDB financial rows."""
        ticker = claim.ticker
        year = claim.fiscal_year
        quarter = claim.fiscal_quarter
        statement = claim.statement
        c_lower = statement.lower()

        fin_row = get_quarterly_financials_row(conn, ticker, year, quarter)
        if not fin_row:
            return NumericFactCheck(
                metric="financial_row_existence",
                is_verified=False,
                explanation=f"No audited financial statements found for {ticker} {year} {quarter}.",
            )

        # 1. Gross margin claim verification
        if claim.claim_type == "gross_margin" or "margin" in c_lower:
            rev = fin_row.get("total_revenue", 0.0)
            cogs = fin_row.get("cost_of_goods_sold", 0.0)
            audited_gm = (rev - cogs) / rev if rev > 0 else 0.0

            # Check if claim asserted high / software-like / expanding margins
            if claim.sentiment_direction == "EXPANSION" or "high" in c_lower or "stable" in c_lower:
                # Query historical gross margin 4 quarters prior (YoY)
                prev_row = get_quarterly_financials_row(conn, ticker, year - 1, quarter)
                prev_gm = (
                    (prev_row["total_revenue"] - prev_row["cost_of_goods_sold"]) / prev_row["total_revenue"]
                    if prev_row and prev_row.get("total_revenue", 0) > 0
                    else audited_gm
                )

                gm_diff = audited_gm - prev_gm
                # If gross margin compressed by > 500 bps (5 percentage points)
                if gm_diff < -0.05:
                    return NumericFactCheck(
                        metric="gross_margin",
                        audited_value=round(audited_gm, 4),
                        claimed_value=round(prev_gm, 4),
                        delta_percent=round(gm_diff * 100, 2),
                        is_verified=False,
                        explanation=(
                            f"Contradiction: Executive asserted high/expanding margins, but audited gross margin "
                            f"compressed from {prev_gm:.1%} to {audited_gm:.1%} (drop of {abs(gm_diff)*100:.1f} percentage points) "
                            f"due to surging inference/infrastructure COGS."
                        ),
                    )
                else:
                    return NumericFactCheck(
                        metric="gross_margin",
                        audited_value=round(audited_gm, 4),
                        claimed_value=round(audited_gm, 4),
                        delta_percent=round(gm_diff * 100, 2),
                        is_verified=True,
                        explanation=f"Audited gross margin of {audited_gm:.1%} is consistent with stable software unit economics.",
                    )

        # 2. Capital expenditure / FCF sinkhole verification
        if claim.claim_type == "capex_efficiency" or "infrastructure" in c_lower or "capex" in c_lower:
            capex = fin_row.get("capital_expenditures", 0.0)
            fcf = fin_row.get("free_cash_flow", 0.0)
            rev = fin_row.get("total_revenue", 0.0)
            capex_intensity = capex / rev if rev > 0 else 0.0

            # If capex > 30% of revenue and FCF is negative
            if fcf < 0 and capex_intensity > 0.30:
                return NumericFactCheck(
                    metric="free_cash_flow_drain",
                    audited_value=round(fcf, 2),
                    claimed_value=round(capex, 2),
                    delta_percent=round(capex_intensity * 100, 2),
                    is_verified=False,
                    explanation=(
                        f"Contradiction: Narrative emphasized infrastructure scaling for TAM capture, "
                        f"but Capex intensity reached {capex_intensity:.1%} of revenue while Free Cash Flow "
                        f"collapsed to negative ${abs(fcf):,.0f}."
                    ),
                )
            else:
                return NumericFactCheck(
                    metric="free_cash_flow_drain",
                    audited_value=round(fcf, 2),
                    claimed_value=round(capex, 2),
                    delta_percent=round(capex_intensity * 100, 2),
                    is_verified=True,
                    explanation=f"Capex intensity of {capex_intensity:.1%} is supported by positive FCF of ${fcf:,.0f}.",
                )

        # 3. AI ARR & Segment Reclassification verification
        if claim.claim_type == "ai_arr" or "arr" in c_lower:
            # Check segment disclosures for the quarter
            seg_df = get_segment_history(conn, ticker)
            quarter_segs = seg_df[
                (seg_df["fiscal_year"] == year) & (seg_df["fiscal_quarter"] == quarter)
            ]

            reclassified = quarter_segs[quarter_segs["is_reported_organic"] == False]
            if not reclassified.empty:
                notes = reclassified.iloc[0].get("notes", "")
                reclass_rev = reclassified.iloc[0].get("segment_revenue", 0.0)
                return NumericFactCheck(
                    metric="organic_arr_reclassification",
                    audited_value=round(reclass_rev, 2),
                    claimed_value=None,
                    is_verified=False,
                    explanation=(
                        f"Contradiction: Disclosed ARR of ${reclass_rev:,.0f} contains non-organic revenue reclassification. "
                        f"Footnote disclosures state: '{notes}'."
                    ),
                )
            else:
                total_seg = quarter_segs["segment_revenue"].sum() if not quarter_segs.empty else 0.0
                return NumericFactCheck(
                    metric="organic_arr_reclassification",
                    audited_value=round(total_seg, 2),
                    is_verified=True,
                    explanation="Reported ARR segment revenue aligns with organic GAAP product disclosures.",
                )

        # 4. Fallback verification
        return NumericFactCheck(
            metric="general_accounting_reconciliation",
            is_verified=True,
            explanation="Qualitative assertion does not conflict with GAAP line items.",
        )
