"""Unit tests for NumericGuardrail fact-checking gate."""

from __future__ import annotations

from pathlib import Path
import pytest

from src.agents.claim_extractor import ClaimExtractor
from src.agents.numeric_guardrail import NumericGuardrail
from src.db.schema import get_default_db


@pytest.fixture
def populated_db():
    bench_dir = Path(__file__).parent.parent / "data" / "benchmark"
    db = get_default_db(bench_dir)
    return db.conn


class TestNumericGuardrail:
    def test_verify_aura_margin_dilution(self, populated_db):
        extractor = ClaimExtractor()
        guardrail = NumericGuardrail()

        claims = extractor.extract_from_db(populated_db, "AURA", 2025, "Q4")
        gm_claim = next(c for c in claims if c.claim_type == "gross_margin")

        fact_check = guardrail.verify_claim(populated_db, gm_claim)
        assert fact_check.is_verified is False
        assert fact_check.metric == "gross_margin"
        assert fact_check.audited_value is not None
        assert "compressed" in fact_check.explanation.lower() or "drop" in fact_check.explanation.lower()

    def test_verify_nxus_capex_drain(self, populated_db):
        extractor = ClaimExtractor()
        guardrail = NumericGuardrail()

        claims = extractor.extract_from_db(populated_db, "NXUS", 2025, "Q4")
        capex_claim = next(c for c in claims if c.claim_type == "capex_efficiency")

        fact_check = guardrail.verify_claim(populated_db, capex_claim)
        assert fact_check.is_verified is False
        assert fact_check.metric == "free_cash_flow_drain"
        assert fact_check.audited_value < 0  # Negative FCF
        assert "collapsed" in fact_check.explanation.lower() or "negative" in fact_check.explanation.lower()

    def test_verify_synx_reclassification(self, populated_db):
        extractor = ClaimExtractor()
        guardrail = NumericGuardrail()

        claims = extractor.extract_from_db(populated_db, "SYNX", 2025, "Q4")
        arr_claim = next(c for c in claims if c.claim_type == "ai_arr")

        fact_check = guardrail.verify_claim(populated_db, arr_claim)
        assert fact_check.is_verified is False
        assert fact_check.metric == "organic_arr_reclassification"
        assert "reclassification" in fact_check.explanation.lower()

    def test_verify_vortex_clean_control(self, populated_db):
        extractor = ClaimExtractor()
        guardrail = NumericGuardrail()

        claims = extractor.extract_from_db(populated_db, "VORS", 2025, "Q4")
        gm_claim = next(c for c in claims if c.claim_type == "gross_margin")

        fact_check = guardrail.verify_claim(populated_db, gm_claim)
        assert fact_check.is_verified is True
        assert fact_check.metric == "gross_margin"
        assert fact_check.audited_value > 0.75
        assert "consistent" in fact_check.explanation.lower()
