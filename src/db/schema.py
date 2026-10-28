"""DuckDB database schema definitions and data management for narrative-audit-jev."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
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
        """Initialize connection to DuckDB with external access disabled for security."""
        self.db_path = db_path
        # Disable file reading, socket access, and extensions at the connection level
        config = {
            "enable_external_access": "false",
        }
        self.conn = duckdb.connect(database=db_path, config=config)
        # Lock configuration to prevent re-enabling via SQL PRAGMA / SET commands
        self.conn.execute("SET lock_configuration=true;")
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


EXPECTED_COMPANIES = 4
EXPECTED_QUARTERS = 32
EXPECTED_GOLDEN_CASES = 52
EXPECTED_TICKERS = {"AURA", "NXUS", "SYNX", "VORS"}
GOLDEN_REQUIRED_KEYS = {
    "case_id",
    "ticker",
    "fiscal_year",
    "fiscal_quarter",
    "category",
    "claim_text",
    "ground_truth",
}
GOLDEN_REQUIRED_GT_KEYS = {
    "is_discrepancy",
    "divergence_category",
    "materiality",
    "expected_verdict",
    "verified_numbers",
    "rationale",
}
GOLDEN_DIVERGENCE_CATEGORIES = {
    "MARGIN_DILUTION",
    "CAPITAL_SINKHOLE",
    "REVENUE_RECLASSIFICATION",
    "PILOT_CHURN",
    "NONE",
}
GOLDEN_MATERIALITIES = {"NONE", "LOW", "MODERATE", "HIGH", "CRITICAL"}
GOLDEN_VERDICTS = {"SUPPORTED", "CONTRADICTED", "UNVERIFIABLE"}
GAAP_COLUMNS = {
    "total_revenue",
    "cost_of_goods_sold",
    "gross_profit",
    "rd_expense",
    "sm_expense",
    "ga_expense",
    "operating_income",
    "net_income",
    "operating_cash_flow",
    "capital_expenditures",
    "free_cash_flow",
    "cash_and_equivalents",
    "deferred_revenue",
}
_PERIOD_METRIC_KEY = re.compile(
    r"^(?P<metric>[a-z_]+)_q(?P<quarter>[1-4])_(?P<year>\d{4})$",
    re.IGNORECASE,
)
_NUMBER_RECONCILE_TOLERANCE = 0.015


def repo_root() -> Path:
    """Return the repository root (parent of the `src` package)."""
    return Path(__file__).resolve().parent.parent.parent


def default_benchmark_dir() -> Path:
    return repo_root() / "data" / "benchmark"


def default_golden_path() -> Path:
    return repo_root() / "data" / "golden_ground_truth.json"


def get_default_db(benchmark_path: Optional[Path] = None) -> FinancialDatabase:
    """Factory creating an in-memory database populated with benchmark data."""
    db = FinancialDatabase(":memory:")
    if benchmark_path and benchmark_path.exists():
        db.load_from_benchmark_dir(benchmark_path)
    return db


def _gross_margin(row: Dict[str, Any]) -> Optional[float]:
    rev = float(row.get("total_revenue") or 0.0)
    cogs = float(row.get("cost_of_goods_sold") or 0.0)
    if rev <= 0:
        return None
    return (rev - cogs) / rev


def _lookup_financial_row(
    db: FinancialDatabase, ticker: str, year: int, quarter: str
) -> Optional[Dict[str, Any]]:
    df = db.query_df(
        """
        SELECT * FROM quarterly_financials
        WHERE ticker = ? AND fiscal_year = ? AND fiscal_quarter = ?
        """,
        [ticker, year, quarter],
    )
    if df.empty:
        return None
    return df.iloc[0].to_dict()


def _metric_from_row(row: Dict[str, Any], metric: str) -> Optional[float]:
    if metric == "gross_margin":
        return _gross_margin(row)
    if metric in GAAP_COLUMNS:
        value = row.get(metric)
        return None if value is None else float(value)
    return None


def validate_accounting_identities(db: FinancialDatabase) -> List[str]:
    """Confirm GAAP identities hold for every loaded quarterly row."""
    errors: List[str] = []
    df = db.query_df("SELECT * FROM quarterly_financials")
    if df.empty:
        return ["No quarterly_financials rows loaded."]

    gp_mismatch = (df["total_revenue"] - df["cost_of_goods_sold"]) - df["gross_profit"]
    bad_gp = df[gp_mismatch.abs() >= 1e-4]
    for _, row in bad_gp.iterrows():
        errors.append(
            f"Gross profit identity failed for {row['id']}: "
            f"{row['total_revenue']} - {row['cost_of_goods_sold']} != {row['gross_profit']}"
        )

    fcf_mismatch = (df["operating_cash_flow"] - df["capital_expenditures"]) - df["free_cash_flow"]
    bad_fcf = df[fcf_mismatch.abs() >= 1e-4]
    for _, row in bad_fcf.iterrows():
        errors.append(
            f"Free cash flow identity failed for {row['id']}: "
            f"{row['operating_cash_flow']} - {row['capital_expenditures']} != {row['free_cash_flow']}"
        )
    return errors


def _parse_verified_metric_key(key: str) -> Optional[Tuple[str, Optional[int], Optional[str]]]:
    """Map a verified_numbers key to (metric, year, quarter)."""
    match = _PERIOD_METRIC_KEY.match(key)
    if match:
        metric = match.group("metric").lower()
        quarter = f"Q{match.group('quarter')}"
        year = int(match.group("year"))
        if metric == "gross_margin" or metric in GAAP_COLUMNS:
            return metric, year, quarter
        return None
    lowered = key.lower()
    if lowered == "gross_margin" or lowered in GAAP_COLUMNS:
        return lowered, None, None
    return None


def validate_golden_cases(db: FinancialDatabase, golden_path: Path) -> List[str]:
    """Validate golden-case count, schema, ticker coverage, and GAAP number keys."""
    errors: List[str] = []
    if not golden_path.exists():
        return [f"Golden ground-truth file not found: {golden_path}"]

    with open(golden_path, "r") as f:
        cases = json.load(f)

    if not isinstance(cases, list):
        return [f"Golden ground-truth must be a JSON list, got {type(cases).__name__}."]

    if len(cases) != EXPECTED_GOLDEN_CASES:
        errors.append(
            f"Expected {EXPECTED_GOLDEN_CASES} golden test cases, found {len(cases)}."
        )

    case_ids = [c.get("case_id") for c in cases if isinstance(c, dict)]
    if len(case_ids) != len(set(case_ids)):
        errors.append("Duplicate case_id found in golden benchmark.")

    tickers_seen = set()
    for case in cases:
        case_id = case.get("case_id", "<missing>")
        missing = GOLDEN_REQUIRED_KEYS - set(case.keys())
        if missing:
            errors.append(f"{case_id}: missing top-level keys {sorted(missing)}")
            continue

        tickers_seen.add(case["ticker"])
        gt = case["ground_truth"]
        if not isinstance(gt, dict):
            errors.append(f"{case_id}: ground_truth must be an object")
            continue

        missing_gt = GOLDEN_REQUIRED_GT_KEYS - set(gt.keys())
        if missing_gt:
            errors.append(f"{case_id}: missing ground_truth keys {sorted(missing_gt)}")
            continue

        if gt["divergence_category"] not in GOLDEN_DIVERGENCE_CATEGORIES:
            errors.append(
                f"{case_id}: invalid divergence_category {gt['divergence_category']!r}"
            )
        if gt["materiality"] not in GOLDEN_MATERIALITIES:
            errors.append(f"{case_id}: invalid materiality {gt['materiality']!r}")
        if gt["expected_verdict"] not in GOLDEN_VERDICTS:
            errors.append(f"{case_id}: invalid expected_verdict {gt['expected_verdict']!r}")

        ticker = case["ticker"]
        year = int(case["fiscal_year"])
        quarter = str(case["fiscal_quarter"])
        period_row = _lookup_financial_row(db, ticker, year, quarter)
        if period_row is None:
            errors.append(
                f"{case_id}: no quarterly_financials row for {ticker} {year} {quarter}"
            )
            continue

        verified = gt.get("verified_numbers") or {}
        if not isinstance(verified, dict):
            errors.append(f"{case_id}: verified_numbers must be an object")
            continue

        for key, claimed in verified.items():
            parsed = _parse_verified_metric_key(str(key))
            if parsed is None:
                continue
            metric, metric_year, metric_quarter = parsed
            lookup_year = year if metric_year is None else metric_year
            lookup_quarter = quarter if metric_quarter is None else metric_quarter
            row = (
                period_row
                if (lookup_year, lookup_quarter) == (year, quarter)
                else _lookup_financial_row(db, ticker, lookup_year, lookup_quarter)
            )
            if row is None:
                errors.append(
                    f"{case_id}: no quarterly_financials row for verified key "
                    f"{key} ({ticker} {lookup_year} {lookup_quarter})"
                )
                continue
            audited = _metric_from_row(row, metric)
            if audited is None:
                errors.append(f"{case_id}: cannot compute {metric} for key {key}")
                continue
            try:
                claimed_num = float(claimed)
            except (TypeError, ValueError):
                errors.append(f"{case_id}: verified_numbers[{key!r}] is not numeric")
                continue
            if abs(audited - claimed_num) > _NUMBER_RECONCILE_TOLERANCE:
                errors.append(
                    f"{case_id}: verified_numbers[{key}]={claimed_num} does not match "
                    f"audited {metric}={audited:.4f} for {ticker} {lookup_year} {lookup_quarter}"
                )

    missing_tickers = EXPECTED_TICKERS - tickers_seen
    if missing_tickers:
        errors.append(f"Golden cases missing tickers: {sorted(missing_tickers)}")
    return errors


def validate_benchmark(
    benchmark_dir: Optional[Path] = None,
    golden_path: Optional[Path] = None,
) -> Tuple[List[str], Dict[str, Any]]:
    """Load benchmark data and validate schema, identities, and golden cases."""
    bench = Path(benchmark_dir) if benchmark_dir else default_benchmark_dir()
    golden = Path(golden_path) if golden_path else default_golden_path()
    errors: List[str] = []

    if not bench.exists():
        return [f"Benchmark directory not found: {bench}"], {}

    db = get_default_db(bench)
    try:
        stats = db.get_summary_stats()
        if stats["companies_count"] != EXPECTED_COMPANIES:
            errors.append(
                f"Expected {EXPECTED_COMPANIES} companies, found {stats['companies_count']}."
            )
        if stats["quarters_count"] != EXPECTED_QUARTERS:
            errors.append(
                f"Expected {EXPECTED_QUARTERS} quarterly rows, found {stats['quarters_count']}."
            )

        tickers = {
            row[0] for row in db.execute("SELECT ticker FROM companies").fetchall()
        }
        missing_cos = EXPECTED_TICKERS - tickers
        if missing_cos:
            errors.append(f"Benchmark missing companies: {sorted(missing_cos)}")

        errors.extend(validate_accounting_identities(db))
        errors.extend(validate_golden_cases(db, golden))
        if golden.exists():
            with open(golden, "r") as f:
                loaded = json.load(f)
            if isinstance(loaded, list):
                stats["golden_cases"] = len(loaded)
        return errors, stats
    finally:
        db.close()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="DuckDB schema loader and benchmark validator for narrative-audit-jev."
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate DuckDB schema, accounting identities, and 52 golden test cases.",
    )
    args = parser.parse_args(argv)

    if args.validate:
        errors, stats = validate_benchmark()
        print("DuckDB Schema & Ingestion Status:")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        if errors:
            print(f"Validation: FAIL ({len(errors)} error(s))")
            for err in errors:
                print(f"  - {err}")
            return 1
        print(f"Validation: PASS ({stats.get('golden_cases', 0)} golden test cases)")
        return 0

    bench_dir = default_benchmark_dir()
    db = get_default_db(bench_dir)
    stats = db.get_summary_stats()
    print("DuckDB Schema & Ingestion Status:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
