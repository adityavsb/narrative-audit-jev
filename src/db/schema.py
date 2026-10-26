"""DuckDB database schema definitions and data management for narrative-audit-jev."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import duckdb


SCHEMA_SQL = """
-- Company metadata table
CREATE TABLE IF NOT EXISTS companies (
    ticker VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    sector VARCHAR NOT NULL,
    business_model VARCHAR NOT NULL,
    fiscal_year_end VARCHAR NOT NULL,
    currency VARCHAR DEFAULT 'USD',
    is_control_baseline BOOLEAN DEFAULT FALSE
);

-- Core quarterly financial statement disclosures (GAAP)
CREATE TABLE IF NOT EXISTS quarterly_financials (
    id VARCHAR PRIMARY KEY,
    ticker VARCHAR NOT NULL REFERENCES companies(ticker),
    fiscal_year INTEGER NOT NULL,
    fiscal_quarter VARCHAR NOT NULL,
    period_end_date DATE NOT NULL,
    total_revenue DOUBLE NOT NULL,
    cost_of_goods_sold DOUBLE NOT NULL,
    gross_profit DOUBLE NOT NULL,
    rd_expense DOUBLE NOT NULL,
    sm_expense DOUBLE NOT NULL,
    ga_expense DOUBLE NOT NULL,
    operating_income DOUBLE NOT NULL,
    net_income DOUBLE NOT NULL,
    operating_cash_flow DOUBLE NOT NULL,
    capital_expenditures DOUBLE NOT NULL,
    free_cash_flow DOUBLE NOT NULL,
    cash_and_equivalents DOUBLE NOT NULL,
    deferred_revenue DOUBLE NOT NULL
);

-- Segment-level revenue & product disclosures
CREATE TABLE IF NOT EXISTS segment_disclosures (
    id VARCHAR PRIMARY KEY,
    ticker VARCHAR NOT NULL REFERENCES companies(ticker),
    fiscal_year INTEGER NOT NULL,
    fiscal_quarter VARCHAR NOT NULL,
    segment_name VARCHAR NOT NULL,
    segment_revenue DOUBLE NOT NULL,
    segment_gross_margin DOUBLE,
    is_reported_organic BOOLEAN DEFAULT TRUE,
    notes TEXT
);

-- Earnings call and investor conference transcripts
CREATE TABLE IF NOT EXISTS transcripts (
    id VARCHAR PRIMARY KEY,
    ticker VARCHAR NOT NULL REFERENCES companies(ticker),
    fiscal_year INTEGER NOT NULL,
    fiscal_quarter VARCHAR NOT NULL,
    section VARCHAR NOT NULL, -- 'PREPARED_REMARKS' or 'ANALYST_QA'
    speaker_name VARCHAR NOT NULL,
    speaker_title VARCHAR NOT NULL,
    content TEXT NOT NULL,
    sequence_order INTEGER NOT NULL
);

-- Index creation for efficient analytical slicing
CREATE INDEX IF NOT EXISTS idx_fin_ticker_quarter ON quarterly_financials(ticker, fiscal_year, fiscal_quarter);
CREATE INDEX IF NOT EXISTS idx_seg_ticker_quarter ON segment_disclosures(ticker, fiscal_year, fiscal_quarter);
CREATE INDEX IF NOT EXISTS idx_tx_ticker_quarter ON transcripts(ticker, fiscal_year, fiscal_quarter);
"""


class FinancialDatabase:
    """Manages an embedded or persistent DuckDB analytical instance."""

    def __init__(self, db_path: Optional[str] = ":memory:"):
        """Initialize connection to DuckDB."""
        self.db_path = db_path
        self.conn = duckdb.connect(database=db_path)
        self._init_schema()

    def _init_schema(self) -> None:
        """Create tables and indexes if they do not exist."""
        self.conn.execute(SCHEMA_SQL)

    def execute(self, query: str, parameters: Optional[List[Any]] = None) -> duckdb.DuckDBPyConnection:
        """Execute a query against DuckDB."""
        if parameters:
            return self.conn.execute(query, parameters)
        return self.conn.execute(query)

    def query_df(self, query: str, parameters: Optional[List[Any]] = None):
        """Execute query and return results as a Pandas DataFrame."""
        return self.execute(query, parameters).df()

    def load_company(self, company_dict: Dict[str, Any]) -> None:
        """Insert or update a company record."""
        self.conn.execute(
            """
            INSERT OR REPLACE INTO companies 
            (ticker, name, sector, business_model, fiscal_year_end, currency, is_control_baseline)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                company_dict["ticker"],
                company_dict["name"],
                company_dict["sector"],
                company_dict["business_model"],
                company_dict["fiscal_year_end"],
                company_dict.get("currency", "USD"),
                company_dict.get("is_control_baseline", False),
            ],
        )

    def load_quarterly_financials(self, records: List[Dict[str, Any]]) -> None:
        """Insert quarterly financial records."""
        for r in records:
            # Derived metrics check
            gp = r["gross_profit"]
            cogs = r["cost_of_goods_sold"]
            rev = r["total_revenue"]
            # Enforce accounting equation: revenue - cogs == gross_profit (within tolerance)
            assert abs((rev - cogs) - gp) < 0.01, f"Gross profit mismatch for {r['id']}: {rev} - {cogs} != {gp}"
            
            fcf = r["operating_cash_flow"] - r["capital_expenditures"]
            assert abs(fcf - r["free_cash_flow"]) < 0.01, f"FCF mismatch for {r['id']}"

            self.conn.execute(
                """
                INSERT OR REPLACE INTO quarterly_financials
                (id, ticker, fiscal_year, fiscal_quarter, period_end_date, total_revenue,
                 cost_of_goods_sold, gross_profit, rd_expense, sm_expense, ga_expense,
                 operating_income, net_income, operating_cash_flow, capital_expenditures,
                 free_cash_flow, cash_and_equivalents, deferred_revenue)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    r["id"], r["ticker"], r["fiscal_year"], r["fiscal_quarter"],
                    r["period_end_date"], r["total_revenue"], r["cost_of_goods_sold"],
                    r["gross_profit"], r["rd_expense"], r["sm_expense"], r["ga_expense"],
                    r["operating_income"], r["net_income"], r["operating_cash_flow"],
                    r["capital_expenditures"], r["free_cash_flow"], r["cash_and_equivalents"],
                    r["deferred_revenue"]
                ]
            )

    def load_segment_disclosures(self, records: List[Dict[str, Any]]) -> None:
        """Insert segment-level disclosures."""
        for r in records:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO segment_disclosures
                (id, ticker, fiscal_year, fiscal_quarter, segment_name, segment_revenue,
                 segment_gross_margin, is_reported_organic, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    r["id"], r["ticker"], r["fiscal_year"], r["fiscal_quarter"],
                    r["segment_name"], r["segment_revenue"], r.get("segment_gross_margin"),
                    r.get("is_reported_organic", True), r.get("notes", "")
                ]
            )

    def load_transcripts(self, records: List[Dict[str, Any]]) -> None:
        """Insert transcript snippets."""
        for r in records:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO transcripts
                (id, ticker, fiscal_year, fiscal_quarter, section, speaker_name,
                 speaker_title, content, sequence_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    r["id"], r["ticker"], r["fiscal_year"], r["fiscal_quarter"],
                    r["section"], r["speaker_name"], r["speaker_title"],
                    r["content"], r["sequence_order"]
                ]
            )

    def load_from_benchmark_dir(self, benchmark_dir: Path) -> Dict[str, int]:
        """Ingest all JSON datasets from a benchmark or sample fixture directory."""
        counts = {"companies": 0, "financials": 0, "segments": 0, "transcripts": 0}
        
        if (benchmark_dir / "company.json").exists():
            dirs_to_scan = [benchmark_dir]
        else:
            dirs_to_scan = [d for d in benchmark_dir.iterdir() if d.is_dir()]

        for company_dir in dirs_to_scan:
            meta_file = company_dir / "company.json"
            fin_file = company_dir / "financials.json"
            seg_file = company_dir / "segments.json"
            tx_file = company_dir / "transcripts.json"

            if meta_file.exists():
                with open(meta_file, "r") as f:
                    self.load_company(json.load(f))
                    counts["companies"] += 1

            if fin_file.exists():
                with open(fin_file, "r") as f:
                    records = json.load(f)
                    self.load_quarterly_financials(records)
                    counts["financials"] += len(records)

            if seg_file.exists():
                with open(seg_file, "r") as f:
                    records = json.load(f)
                    self.load_segment_disclosures(records)
                    counts["segments"] += len(records)

            if tx_file.exists():
                with open(tx_file, "r") as f:
                    records = json.load(f)
                    self.load_transcripts(records)
                    counts["transcripts"] += len(records)

        return counts

    def get_summary_stats(self) -> Dict[str, Any]:
        """Return dataset counts and table statistics."""
        return {
            "companies_count": self.conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0],
            "quarters_count": self.conn.execute("SELECT COUNT(*) FROM quarterly_financials").fetchone()[0],
            "segments_count": self.conn.execute("SELECT COUNT(*) FROM segment_disclosures").fetchone()[0],
            "transcripts_count": self.conn.execute("SELECT COUNT(*) FROM transcripts").fetchone()[0],
        }

    def close(self) -> None:
        """Close the DuckDB connection."""
        self.conn.close()


def get_default_db(benchmark_path: Optional[Path] = None) -> FinancialDatabase:
    """Factory creating an in-memory database populated with benchmark data."""
    db = FinancialDatabase(":memory:")
    if benchmark_path and benchmark_path.exists():
        db.load_from_benchmark_dir(benchmark_path)
    return db


if __name__ == "__main__":
    import sys
    bench_dir = Path(__file__).resolve().parent.parent.parent / "data" / "benchmark"
    db = get_default_db(bench_dir)
    stats = db.get_summary_stats()
    print("DuckDB Schema & Ingestion Status:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    db.close()
    sys.exit(0)
