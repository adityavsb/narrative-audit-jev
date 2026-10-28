"""Unit tests for NumericGuardrail fact-checking gate."""

from __future__ import annotations

from pathlib import Path
import pytest

from src.agents.claim_extractor import ClaimExtractor
from src.agents.numeric_guardrail import NumericGuardrail
from src.agents.state import ClaimExtraction
from src.db.schema import get_default_db


def _margin_claim(**kwargs) -> ClaimExtraction:
    defaults = dict(
        claim_id="test_gm",
        ticker="AURA",
        fiscal_year=2025,
        fiscal_quarter="Q4",
        speaker_name="Test Speaker",
        speaker_title="CEO",
        statement="Gross margin this quarter reflects product mix.",
        claim_type="gross_margin",
        metrics_mentioned=["gross_margin"],
        sentiment_direction="NEUTRAL",
    )
    defaults.update(kwargs)
    return ClaimExtraction(**defaults)


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

    def test_contraction_claim_on_diluting_company_is_reconciled(self, populated_db):
        """CONTRACTION margin claims must still hit the gross-margin path, not fallback."""
        guardrail = NumericGuardrail()
        claim = _margin_claim(
            ticker="AURA",
            statement="Gross margins contracted by 1,800 basis points on inference COGS.",
            sentiment_direction="CONTRACTION",
        )
        fact_check = guardrail.verify_claim(populated_db, claim)
        assert fact_check.metric == "gross_margin"
        assert fact_check.is_verified is True
        assert fact_check.audited_value is not None
        assert "compressed" in fact_check.explanation.lower()

    def test_contraction_claim_on_control_company_is_contradicted(self, populated_db):
        """False dilution claims against Vortex must be flagged, not skipped."""
        guardrail = NumericGuardrail()
        claim = _margin_claim(
            ticker="VORS",
            statement="Vortex is experiencing severe gross margin dilution and ballooning cloud costs.",
            sentiment_direction="CONTRACTION",
        )
        fact_check = guardrail.verify_claim(populated_db, claim)
        assert fact_check.metric == "gross_margin"
        assert fact_check.is_verified is False
        assert "contradiction" in fact_check.explanation.lower()

    def test_margin_claim_with_infrastructure_does_not_use_capex_path(self, populated_db):
        """Gross-margin claims must not fall through to capex heuristics when text mentions infrastructure."""
        guardrail = NumericGuardrail()
        claim = _margin_claim(
            ticker="AURA",
            statement=(
                "Gross margins contracted while we scaled inference infrastructure for Copilot workloads."
            ),
            sentiment_direction="CONTRACTION",
        )
        fact_check = guardrail.verify_claim(populated_db, claim)
        assert fact_check.metric == "gross_margin"
        assert fact_check.metric != "free_cash_flow_drain"

    def test_organic_arr_magnitude_mismatch(self, populated_db):
        """Stated ARR figures should reconcile to segment totals when no reclassification row exists."""
        guardrail = NumericGuardrail()
        claim = _margin_claim(
            ticker="VORS",
            statement="We reached $500 million in AI-driven Annual Recurring Revenue this quarter.",
            claim_type="ai_arr",
            metrics_mentioned=["segment_revenue"],
            sentiment_direction="EXPANSION",
        )
        fact_check = guardrail.verify_claim(populated_db, claim)
        assert fact_check.metric == "organic_arr_magnitude"
        assert fact_check.is_verified is False

    def test_neutral_margin_claim_is_reconciled_not_skipped(self, populated_db):
        """NEUTRAL margin claims without 'high'/'stable' must still reconcile to GAAP GM."""
        guardrail = NumericGuardrail()
        claim = _margin_claim(
            ticker="AURA",
            statement="Gross margin this quarter reflects the mix of Copilot and core workflow SKUs.",
            sentiment_direction="NEUTRAL",
        )
        fact_check = guardrail.verify_claim(populated_db, claim)
        assert fact_check.metric == "gross_margin"
        assert fact_check.metric != "general_accounting_reconciliation"
        assert fact_check.audited_value is not None
        assert abs(fact_check.audited_value - 0.61) < 0.01

    def test_margin_claim_2024_uses_baseline_fallback(self, populated_db):
        """Claims in 2024 without prior YoY year-1 row must fall back to earliest baseline."""
        guardrail = NumericGuardrail()
        claim = _margin_claim(
            ticker="AURA",
            fiscal_year=2024,
            fiscal_quarter="Q4",
            statement="Gross margins expanded strongly across all product lines.",
            sentiment_direction="EXPANSION",
        )
        fact_check = guardrail.verify_claim(populated_db, claim)
        assert fact_check.metric == "gross_margin"
        assert fact_check.is_verified is False  # Compressed from 79% (Q1) to 71% (Q4)
        assert "contradiction" in fact_check.explanation.lower() or "dilution" in fact_check.explanation.lower()

    def test_margin_percentage_discrepancy_detected(self, populated_db):
        """Stated percentage in statement must be parsed and reconciled against audited margin."""
        guardrail = NumericGuardrail()
        claim = _margin_claim(
            ticker="AURA",
            fiscal_year=2025,
            fiscal_quarter="Q4",
            statement="Our gross margin was 90% this quarter based on software efficiency.",
            sentiment_direction="NEUTRAL",
        )
        fact_check = guardrail.verify_claim(populated_db, claim)
        assert fact_check.metric == "gross_margin_magnitude"
        assert fact_check.is_verified is False
        assert fact_check.claimed_value == 0.9
        assert abs(fact_check.audited_value - 0.61) < 0.01
        assert "contradiction" in fact_check.explanation.lower()

    def test_capex_with_margin_discipline_not_hijacked(self, populated_db):
        """Capex claims mentioning margin discipline must not be hijacked by gross margin path."""
        guardrail = NumericGuardrail()
        claim = ClaimExtraction(
            claim_id="capex_margin_test",
            ticker="NXUS",
            fiscal_year=2025,
            fiscal_quarter="Q4",
            speaker_name="CEO",
            speaker_title="CEO",
            statement="We spent aggressively on infrastructure to scale capacity while maintaining margin discipline.",
            claim_type="capex_efficiency",
            metrics_mentioned=["capital_expenditures", "free_cash_flow"],
            sentiment_direction="EXPANSION",
        )
        fact_check = guardrail.verify_claim(populated_db, claim)
        # Should evaluate FCF drain, not gross margin
        assert fact_check.metric == "free_cash_flow_drain"
        assert fact_check.is_verified is False
