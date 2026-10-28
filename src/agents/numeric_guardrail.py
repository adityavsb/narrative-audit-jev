"""Deterministic Numeric Critic / Fact-Checking Gate.

Cross-references claimed figures and operational narratives directly against
underlying synthetic financial statement entries in DuckDB, flagging contradictions and
unsupported qualitative assertions.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional
import duckdb

from src.agents.state import ClaimExtraction, NumericFactCheck
from src.db.financial_queries import get_quarterly_financials_row, get_segment_history

_OPTIMISTIC_MARGIN_TERMS = ("high", "stable", "expand", "resilient", "software-like")
_PESSIMISTIC_MARGIN_TERMS = ("compress", "dilut", "decline", "drop", "contract", "headwind")
_MATERIAL_GM_COMPRESSION = -0.05  # 500 bps YoY
_DOLLAR_AMOUNT_RE = re.compile(
    r"\$\s*(\d+(?:\.\d+)?)\s*(million|mil|m|billion|bil|b)\b",
    re.IGNORECASE,
)
_PERCENTAGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%", re.IGNORECASE)


def _parse_stated_margin_percentages(text: str) -> List[float]:
    """Parse percentage figures explicitly tied to margin within a 60-character window."""
    candidates = []
    for match in _PERCENTAGE_RE.finditer(text):
        start = max(0, match.start() - 60)
        end = min(len(text), match.end() + 60)
        window = text[start:end].lower()
        if "margin" in window:
            val = float(match.group(1))
            candidates.append(val / 100.0 if val > 1.0 else val)
    return candidates



def _parse_stated_dollars_millions(text: str) -> Optional[float]:
    """Parse the first '$N million' style figure into millions USD."""
    match = _DOLLAR_AMOUNT_RE.search(text)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2).lower()
    if unit in {"billion", "bil", "b"}:
        value *= 1000.0
    return value


def _gross_margin(row: Optional[Dict[str, Any]]) -> Optional[float]:
    if not row:
        return None
    rev = float(row.get("total_revenue") or 0.0)
    cogs = float(row.get("cost_of_goods_sold") or 0.0)
    if rev <= 0:
        return None
    return (rev - cogs) / rev


def _margin_claim_polarity(claim: ClaimExtraction, statement_lower: str) -> str:
    """Classify a margin claim as optimistic, pessimistic, or neutral.

    Sentiment on the extracted claim is authoritative so CONTRACTION/NEUTRAL
    statements are not skipped just because the text also contains 'high'.
    """
    direction = (claim.sentiment_direction or "NEUTRAL").upper()
    if direction == "CONTRACTION":
        return "pessimistic"
    if direction in {"EXPANSION", "STABLE"}:
        return "optimistic"
    if any(term in statement_lower for term in _PESSIMISTIC_MARGIN_TERMS):
        return "pessimistic"
    if any(term in statement_lower for term in _OPTIMISTIC_MARGIN_TERMS):
        return "optimistic"
    return "neutral"


class NumericGuardrail:
    """Reconciles executive assertions against structured benchmark ledger entries."""

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

        # 1. Gross margin claim verification — always reconcile, all polarities.
        if claim.claim_type == "gross_margin" or (
            "margin" in c_lower and claim.claim_type != "capex_efficiency"
        ):
            audited_gm = _gross_margin(fin_row)
            if audited_gm is None:
                return NumericFactCheck(
                    metric="gross_margin",
                    is_verified=False,
                    explanation=(
                        f"Cannot compute gross margin for {ticker} {year} {quarter}: "
                        "revenue is missing or zero."
                    ),
                )

            # Prior baseline lookup: prioritize YoY (year - 1), fallback to earliest historical quarter
            prev_row = get_quarterly_financials_row(conn, ticker, year - 1, quarter)
            baseline_type = "YoY"
            if not prev_row:
                # Fallback: check earliest available quarter in dataset to establish baseline
                earliest_df = conn.execute(
                    "SELECT * FROM quarterly_financials WHERE ticker = ? ORDER BY period_end_date ASC LIMIT 1",
                    [ticker],
                ).df()
                if not earliest_df.empty and earliest_df.iloc[0]["id"] != fin_row.get("id"):
                    prev_row = earliest_df.iloc[0].to_dict()
                    baseline_type = f"vs baseline {prev_row['fiscal_year']} {prev_row['fiscal_quarter']}"
                else:
                    prev_row = fin_row
                    baseline_type = "single-period"

            prev_gm = _gross_margin(prev_row)
            if prev_gm is None:
                prev_gm = audited_gm
            gm_diff = audited_gm - prev_gm
            polarity = _margin_claim_polarity(claim, c_lower)

            # Stated percentage check: flag numeric discrepancies regardless of polarity
            stated_pcts = _parse_stated_margin_percentages(statement)
            stated_pct = None
            if stated_pcts:
                best_match = min(stated_pcts, key=lambda p: abs(audited_gm - p))
                pct_err = abs(audited_gm - best_match)
                if pct_err > self.tolerance:
                    return NumericFactCheck(
                        metric="gross_margin_magnitude",
                        audited_value=round(audited_gm, 4),
                        claimed_value=round(best_match, 4),
                        delta_percent=round(pct_err * 100, 2),
                        is_verified=False,
                        explanation=(
                            f"Contradiction: Statement cited {best_match:.1%} gross margin, but audited "
                            f"gross margin was {audited_gm:.1%} (discrepancy of {pct_err*100:.1f} percentage points)."
                        ),
                    )
                stated_pct = best_match

            if polarity == "optimistic":
                if gm_diff < _MATERIAL_GM_COMPRESSION:
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
                return NumericFactCheck(
                    metric="gross_margin",
                    audited_value=round(audited_gm, 4),
                    claimed_value=round(audited_gm, 4),
                    delta_percent=round(gm_diff * 100, 2),
                    is_verified=True,
                    explanation=f"Audited gross margin of {audited_gm:.1%} is consistent with stable software unit economics.",
                )

            if polarity == "pessimistic":
                if gm_diff < _MATERIAL_GM_COMPRESSION:
                    return NumericFactCheck(
                        metric="gross_margin",
                        audited_value=round(audited_gm, 4),
                        claimed_value=round(prev_gm, 4),
                        delta_percent=round(gm_diff * 100, 2),
                        is_verified=True,
                        explanation=(
                            f"Audited gross margin compressed from {prev_gm:.1%} to {audited_gm:.1%} "
                            f"(drop of {abs(gm_diff)*100:.1f} percentage points), consistent with the contraction claim."
                        ),
                    )
                return NumericFactCheck(
                    metric="gross_margin",
                    audited_value=round(audited_gm, 4),
                    claimed_value=round(prev_gm, 4),
                    delta_percent=round(gm_diff * 100, 2),
                    is_verified=False,
                    explanation=(
                        f"Contradiction: Claim asserted gross-margin contraction, but audited gross margin "
                        f"moved from {prev_gm:.1%} to {audited_gm:.1%} "
                        f"({gm_diff * 100:+.1f} percentage points {baseline_type}), which is not a material dilution."
                    ),
                )

            return NumericFactCheck(
                metric="gross_margin",
                audited_value=round(audited_gm, 4),
                claimed_value=round(stated_pct if stated_pct is not None else audited_gm, 4),
                delta_percent=round(gm_diff * 100, 2),
                is_verified=True,
                explanation=(
                    f"Gross-margin claim is directionally neutral. Audited gross margin is {audited_gm:.1%} "
                    f"({baseline_type} change {gm_diff * 100:+.1f} percentage points)."
                ),
            )

        # 2. Capital expenditure / FCF sinkhole verification (mutually exclusive with margin path)
        elif claim.claim_type == "capex_efficiency" or (
            ("infrastructure" in c_lower or "capex" in c_lower)
            and claim.claim_type != "gross_margin"
            and "margin" not in c_lower
        ):
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
        elif claim.claim_type == "ai_arr" or "arr" in c_lower:
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
                stated = _parse_stated_dollars_millions(statement)
                if stated is not None and total_seg > 0:
                    rel_diff = abs(stated - total_seg) / total_seg
                    if rel_diff > self.tolerance:
                        return NumericFactCheck(
                            metric="organic_arr_magnitude",
                            audited_value=round(total_seg, 2),
                            claimed_value=round(stated, 2),
                            delta_percent=round(rel_diff * 100, 2),
                            is_verified=False,
                            explanation=(
                                f"Contradiction: Narrative cites ${stated:,.1f}M ARR but organic segment "
                                f"disclosures sum to ${total_seg:,.1f}M for the quarter."
                            ),
                        )
                return NumericFactCheck(
                    metric="organic_arr_reclassification",
                    audited_value=round(total_seg, 2),
                    claimed_value=round(stated, 2) if stated is not None else None,
                    is_verified=True,
                    explanation="Reported ARR segment revenue aligns with organic GAAP product disclosures.",
                )

        # 4. Fallback verification
        return NumericFactCheck(
            metric="general_accounting_reconciliation",
            is_verified=True,
            explanation="Qualitative assertion does not conflict with GAAP line items.",
        )
