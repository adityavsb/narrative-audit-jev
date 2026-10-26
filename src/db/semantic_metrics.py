"""Semantic Metrics Layer: Standardized GAAP financial ratios and growth analytics."""

from __future__ import annotations

from typing import Dict, Any, List, Optional
import duckdb
import pandas as pd


class SemanticMetricsLayer:
    """Computes standardized, audited financial metrics over DuckDB financial tables."""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn

    def get_quarterly_margin_trends(self, ticker: str) -> pd.DataFrame:
        """Calculate YoY and QoQ Gross Margin, Operating Margin, and FCF Margin trends."""
        query = """
        WITH base AS (
            SELECT 
                ticker,
                fiscal_year,
                fiscal_quarter,
                period_end_date,
                total_revenue,
                cost_of_goods_sold,
                gross_profit,
                operating_income,
                capital_expenditures,
                operating_cash_flow,
                free_cash_flow,
                (gross_profit / NULLIF(total_revenue, 0)) AS gross_margin,
                (operating_income / NULLIF(total_revenue, 0)) AS operating_margin,
                (free_cash_flow / NULLIF(total_revenue, 0)) AS fcf_margin,
                (capital_expenditures / NULLIF(operating_cash_flow, 0)) AS capex_to_ocf_ratio
            FROM quarterly_financials
            WHERE ticker = ?
        ),
        lagged AS (
            SELECT 
                *,
                LAG(total_revenue, 1) OVER (PARTITION BY ticker ORDER BY period_end_date) AS prev_qoq_rev,
                LAG(total_revenue, 4) OVER (PARTITION BY ticker ORDER BY period_end_date) AS prev_yoy_rev,
                LAG(gross_margin, 1) OVER (PARTITION BY ticker ORDER BY period_end_date) AS prev_qoq_gm,
                LAG(gross_margin, 4) OVER (PARTITION BY ticker ORDER BY period_end_date) AS prev_yoy_gm,
                LAG(capital_expenditures, 4) OVER (PARTITION BY ticker ORDER BY period_end_date) AS prev_yoy_capex
            FROM base
        )
        SELECT 
            ticker,
            fiscal_year,
            fiscal_quarter,
            period_end_date,
            total_revenue,
            gross_profit,
            gross_margin,
            operating_margin,
            fcf_margin,
            capital_expenditures,
            operating_cash_flow,
            free_cash_flow,
            capex_to_ocf_ratio,
            ((total_revenue - prev_qoq_rev) / NULLIF(prev_qoq_rev, 0)) AS qoq_revenue_growth,
            ((total_revenue - prev_yoy_rev) / NULLIF(prev_yoy_rev, 0)) AS yoy_revenue_growth,
            (gross_margin - prev_qoq_gm) AS qoq_gross_margin_delta,
            (gross_margin - prev_yoy_gm) AS yoy_gross_margin_delta,
            ((capital_expenditures - prev_yoy_capex) / NULLIF(prev_yoy_capex, 0)) AS yoy_capex_growth
        FROM lagged
        ORDER BY period_end_date ASC;
        """
        return self.conn.execute(query, [ticker]).df()

    def get_segment_growth_breakdown(self, ticker: str, fiscal_year: int, fiscal_quarter: str) -> pd.DataFrame:
        """Fetch segment revenue and organic vs reclassified proportions."""
        query = """
        SELECT 
            segment_name,
            segment_revenue,
            segment_gross_margin,
            is_reported_organic,
            notes,
            segment_revenue / SUM(segment_revenue) OVER () AS pct_of_total_segment_revenue
        FROM segment_disclosures
        WHERE ticker = ? AND fiscal_year = ? AND fiscal_quarter = ?
        ORDER BY segment_revenue DESC;
        """
        return self.conn.execute(query, [ticker, fiscal_year, fiscal_quarter]).df()

    def calculate_audit_flags(self, ticker: str) -> Dict[str, Any]:
        """Evaluate key financial divergence triggers across historical quarters."""
        df = self.get_quarterly_margin_trends(ticker)
        if df.empty:
            return {"error": f"No financial records found for ticker {ticker}"}

        latest = df.iloc[-1]
        earliest = df.iloc[0]

        # 1. Gross Margin Compression Check (Latest vs Baseline)
        total_gm_drop_bps = (latest["gross_margin"] - earliest["gross_margin"]) * 10000  # basis points
        gm_dilution_flag = total_gm_drop_bps <= -500  # > 500 bps drop

        # 2. Capex Sinkhole Check: Capex growth vastly outpacing revenue + negative FCF
        capex_growth_yoy = latest["yoy_capex_growth"] if pd.notnull(latest["yoy_capex_growth"]) else 0.0
        rev_growth_yoy = latest["yoy_revenue_growth"] if pd.notnull(latest["yoy_revenue_growth"]) else 0.0
        fcf_negative = latest["free_cash_flow"] < 0
        capex_sinkhole_flag = (capex_growth_yoy > 1.0) and fcf_negative and (capex_growth_yoy > rev_growth_yoy * 2)

        # 3. Revenue Reclassification Check
        seg_df = self.conn.execute(
            """
            SELECT 
                SUM(CASE WHEN is_reported_organic = FALSE THEN segment_revenue ELSE 0 END) AS reclassified_rev,
                SUM(segment_revenue) AS total_segment_rev
            FROM segment_disclosures
            WHERE ticker = ? AND fiscal_year = ? AND fiscal_quarter = ?
            """,
            [ticker, int(latest["fiscal_year"]), str(latest["fiscal_quarter"])]
        ).df()

        reclass_flag = False
        reclass_ratio = 0.0
        if not seg_df.empty and seg_df["total_segment_rev"].iloc[0] > 0:
            reclass_rev = seg_df["reclassified_rev"].iloc[0]
            total_seg = seg_df["total_segment_rev"].iloc[0]
            reclass_ratio = reclass_rev / total_seg
            reclass_flag = reclass_ratio >= 0.30  # >= 30% of segment revenue is reclassified

        return {
            "ticker": ticker,
            "latest_quarter": f"{latest['fiscal_year']}-{latest['fiscal_quarter']}",
            "latest_revenue": float(latest["total_revenue"]),
            "latest_gross_margin": float(latest["gross_margin"]),
            "total_gm_delta_bps": float(total_gm_drop_bps),
            "gm_dilution_flag": bool(gm_dilution_flag),
            "latest_capex": float(latest["capital_expenditures"]),
            "latest_free_cash_flow": float(latest["free_cash_flow"]),
            "capex_growth_yoy": float(capex_growth_yoy),
            "capex_sinkhole_flag": bool(capex_sinkhole_flag),
            "reclassification_ratio": float(reclass_ratio),
            "revenue_reclassification_flag": bool(reclass_flag),
        }
