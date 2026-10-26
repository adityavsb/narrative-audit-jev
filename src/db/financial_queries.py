"""Parameterized financial queries and analytical helper functions for DuckDB."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import duckdb
import pandas as pd


def get_company_profile(conn: duckdb.DuckDBPyConnection, ticker: str) -> Optional[Dict[str, Any]]:
    """Retrieve metadata and business model for a company."""
    res = conn.execute(
        "SELECT ticker, name, sector, business_model, fiscal_year_end, currency, is_control_baseline FROM companies WHERE ticker = ?",
        [ticker]
    ).fetchone()
    if not res:
        return None
    return {
        "ticker": res[0],
        "name": res[1],
        "sector": res[2],
        "business_model": res[3],
        "fiscal_year_end": res[4],
        "currency": res[5],
        "is_control_baseline": res[6]
    }


def get_quarterly_financials_row(
    conn: duckdb.DuckDBPyConnection, ticker: str, fiscal_year: int, fiscal_quarter: str
) -> Optional[Dict[str, Any]]:
    """Retrieve full income, balance sheet and cash flow statement for a specific quarter."""
    df = conn.execute(
        """
        SELECT * FROM quarterly_financials 
        WHERE ticker = ? AND fiscal_year = ? AND fiscal_quarter = ?
        """,
        [ticker, fiscal_year, fiscal_quarter]
    ).df()
    if df.empty:
        return None
    return df.iloc[0].to_dict()


def get_full_financial_history(conn: duckdb.DuckDBPyConnection, ticker: str) -> pd.DataFrame:
    """Retrieve all chronological quarterly records for a company."""
    return conn.execute(
        """
        SELECT 
            fiscal_year,
            fiscal_quarter,
            period_end_date,
            total_revenue,
            cost_of_goods_sold,
            gross_profit,
            round(gross_profit / nullif(total_revenue, 0), 4) as gross_margin,
            operating_income,
            net_income,
            operating_cash_flow,
            capital_expenditures,
            free_cash_flow,
            cash_and_equivalents,
            deferred_revenue
        FROM quarterly_financials
        WHERE ticker = ?
        ORDER BY period_end_date ASC
        """,
        [ticker]
    ).df()


def get_segment_history(conn: duckdb.DuckDBPyConnection, ticker: str) -> pd.DataFrame:
    """Retrieve segment disclosure evolution across quarters."""
    return conn.execute(
        """
        SELECT 
            fiscal_year,
            fiscal_quarter,
            segment_name,
            segment_revenue,
            segment_gross_margin,
            is_reported_organic,
            notes
        FROM segment_disclosures
        WHERE ticker = ?
        ORDER BY fiscal_year ASC, fiscal_quarter ASC, segment_revenue DESC
        """,
        [ticker]
    ).df()


def get_transcript_text(
    conn: duckdb.DuckDBPyConnection,
    ticker: str,
    fiscal_year: int,
    fiscal_quarter: str,
    section: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve transcript statements in sequential order."""
    query = """
        SELECT section, speaker_name, speaker_title, content, sequence_order
        FROM transcripts
        WHERE ticker = ? AND fiscal_year = ? AND fiscal_quarter = ?
    """
    params = [ticker, fiscal_year, fiscal_quarter]
    if section:
        query += " AND section = ?"
        params.append(section)
    query += " ORDER BY sequence_order ASC"

    rows = conn.execute(query, params).fetchall()
    return [
        {
            "section": r[0],
            "speaker_name": r[1],
            "speaker_title": r[2],
            "content": r[3],
            "sequence_order": r[4]
        }
        for r in rows
    ]


def search_transcripts_by_keyword(
    conn: duckdb.DuckDBPyConnection, ticker: str, keyword: str
) -> pd.DataFrame:
    """Case-insensitive keyword search across all earnings call transcripts for a company."""
    query = """
        SELECT fiscal_year, fiscal_quarter, section, speaker_name, speaker_title, content
        FROM transcripts
        WHERE ticker = ? AND lower(content) LIKE ?
        ORDER BY fiscal_year DESC, fiscal_quarter DESC, sequence_order ASC
    """
    return conn.execute(query, [ticker, f"%{keyword.lower()}%"]).df()
