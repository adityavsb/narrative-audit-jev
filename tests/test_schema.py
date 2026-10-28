"""Unit tests for DuckDB schema, accounting identities, and benchmark data loading."""

import json
from pathlib import Path
import duckdb
import pytest
from src.db.schema import (
    EXPECTED_GOLDEN_CASES,
    FinancialDatabase,
    get_default_db,
    main,
    validate_benchmark,
)


@pytest.fixture(scope="module")
def db():
    bench_dir = Path(__file__).resolve().parent.parent / "data" / "benchmark"
    database = get_default_db(bench_dir)
    yield database
    database.close()


def test_companies_loaded(db: FinancialDatabase):
    """Verify all four fictional benchmark companies are loaded with valid attributes."""
    df = db.query_df("SELECT ticker, name, is_control_baseline FROM companies ORDER BY ticker")
    assert len(df) == 4
    tickers = set(df["ticker"].tolist())
    assert tickers == {"AURA", "NXUS", "SYNX", "VORS"}

    # Verify control baseline flag
    vors = df[df["ticker"] == "VORS"].iloc[0]
    assert bool(vors["is_control_baseline"]) is True

    aura = df[df["ticker"] == "AURA"].iloc[0]
    assert bool(aura["is_control_baseline"]) is False


def test_quarterly_financials_count_and_accounting_identities(db: FinancialDatabase):
    """Verify 8 quarters per company (32 total) and GAAP accounting balance equations."""
    df = db.query_df("SELECT * FROM quarterly_financials")
    assert len(df) == 32  # 4 companies * 8 quarters

    # Accounting equation 1: Revenue - COGS == Gross Profit
    diff_gp = (df["total_revenue"] - df["cost_of_goods_sold"]) - df["gross_profit"]
    assert (diff_gp.abs() < 1e-4).all(), "Gross profit does not equal Revenue - COGS"

    # Accounting equation 2: Operating Cash Flow - Capex == Free Cash Flow
    diff_fcf = (df["operating_cash_flow"] - df["capital_expenditures"]) - df["free_cash_flow"]
    assert (diff_fcf.abs() < 1e-4).all(), "Free Cash Flow does not equal OCF - Capex"


def test_segment_disclosures_integrity(db: FinancialDatabase):
    """Verify segment disclosures are present and tie back to registered companies."""
    df = db.query_df("SELECT ticker, segment_name, segment_revenue, is_reported_organic FROM segment_disclosures")
    assert not df.empty

    # Synthetix must have reclassified legacy segment
    synx_reclass = df[(df["ticker"] == "SYNX") & (df["is_reported_organic"] == False)]
    assert len(synx_reclass) == 1
    assert synx_reclass.iloc[0]["segment_revenue"] == 65.0


def test_transcripts_presence(db: FinancialDatabase):
    """Verify earnings call transcripts with prepared remarks and analyst Q&A exist."""
    df = db.query_df("SELECT ticker, section, speaker_title, content FROM transcripts")
    assert len(df) >= 12  # At least 3 snippets per company (CEO, Analyst, CFO)

    sections = set(df["section"].tolist())
    assert "PREPARED_REMARKS" in sections
    assert "ANALYST_QA" in sections


def test_sample_fixture_loading():
    """Verify that FinancialDatabase can load directly from data/sample_fixture."""
    fixture_dir = Path(__file__).resolve().parent.parent / "data" / "sample_fixture"
    assert fixture_dir.exists()
    db = get_default_db(fixture_dir)
    stats = db.get_summary_stats()
    assert stats["companies_count"] == 1
    assert stats["quarters_count"] == 4
    assert stats["segments_count"] == 2
    assert stats["transcripts_count"] == 3
    db.close()


def test_validate_benchmark_passes_on_shipped_data():
    """make data-check / --validate must enforce schema, identities, and 52 golden cases."""
    errors, stats = validate_benchmark()
    assert errors == [], errors
    assert stats["companies_count"] == 4
    assert stats["quarters_count"] == 32
    assert stats["golden_cases"] == EXPECTED_GOLDEN_CASES


def test_validate_benchmark_fails_when_golden_file_missing(tmp_path):
    bench_dir = Path(__file__).resolve().parent.parent / "data" / "benchmark"
    errors, _stats = validate_benchmark(
        benchmark_dir=bench_dir,
        golden_path=tmp_path / "missing_golden.json",
    )
    assert errors
    assert any("not found" in err.lower() for err in errors)


def test_validate_benchmark_fails_on_corrupt_verified_number(tmp_path):
    repo = Path(__file__).resolve().parent.parent
    golden_src = repo / "data" / "golden_ground_truth.json"
    tampered = tmp_path / "golden_ground_truth.json"
    cases = json.loads(golden_src.read_text())
    cases[0]["ground_truth"]["verified_numbers"]["total_revenue_q4_2025"] = 1.0
    tampered.write_text(json.dumps(cases))

    errors, _stats = validate_benchmark(
        benchmark_dir=repo / "data" / "benchmark",
        golden_path=tampered,
    )
    assert errors
    assert any("total_revenue_q4_2025" in err for err in errors)


def test_cli_validate_flag_passes():
    assert main(["--validate"]) == 0


def test_duckdb_connection_is_hardened(db: FinancialDatabase):
    """Verify DuckDB connection has external access disabled and configuration locked."""
    with pytest.raises(duckdb.Error) as exc_info:
        db.conn.execute("SELECT content FROM read_text('README.md')")
    assert "PermissionException" in str(exc_info.value) or "disabled" in str(exc_info.value).lower()

    with pytest.raises(duckdb.Error) as exc_info_lock:
        db.conn.execute("SET enable_external_access=true")
    assert "lock" in str(exc_info_lock.value).lower()

