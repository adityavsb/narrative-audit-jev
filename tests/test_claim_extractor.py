"""Unit tests for ClaimExtractor."""

from __future__ import annotations

from pathlib import Path
import pytest

from src.agents.claim_extractor import ClaimExtractor
from src.db.schema import get_default_db


@pytest.fixture
def populated_db():
    bench_dir = Path(__file__).parent.parent / "data" / "benchmark"
    db = get_default_db(bench_dir)
    return db.conn


class TestClaimExtractor:
    def test_extract_claims_aura_margin(self, populated_db):
        extractor = ClaimExtractor()
        claims = extractor.extract_from_db(populated_db, "AURA", 2025, "Q4")

        assert len(claims) > 0
        gm_claims = [c for c in claims if c.claim_type == "gross_margin"]
        assert len(gm_claims) > 0
        assert "gross_margin" in gm_claims[0].metrics_mentioned

    def test_extract_claims_nxus_capex(self, populated_db):
        extractor = ClaimExtractor()
        claims = extractor.extract_from_db(populated_db, "NXUS", 2025, "Q4")

        assert len(claims) > 0
        capex_claims = [c for c in claims if c.claim_type == "capex_efficiency"]
        assert len(capex_claims) > 0
        assert "capital_expenditures" in capex_claims[0].metrics_mentioned

    def test_extract_claims_synx_arr(self, populated_db):
        extractor = ClaimExtractor()
        claims = extractor.extract_from_db(populated_db, "SYNX", 2025, "Q4")

        assert len(claims) > 0
        arr_claims = [c for c in claims if c.claim_type == "ai_arr"]
        assert len(arr_claims) > 0
        assert "total_revenue" in arr_claims[0].metrics_mentioned

    def test_extract_claims_vortex_control(self, populated_db):
        extractor = ClaimExtractor()
        claims = extractor.extract_from_db(populated_db, "VORS", 2025, "Q4")

        assert len(claims) > 0
        assert any(c.claim_type == "gross_margin" for c in claims)

    def test_word_boundary_prevents_false_positives(self):
        extractor = ClaimExtractor()
        # "carry" should not trigger "arr" regex
        claim = extractor._analyze_statement(
            "TEST", 2025, "Q4", "C1", "CEO", "CEO",
            "We carry additional inventory to service customer needs across the country."
        )
        assert claim is None

        # "contract" should not trigger CONTRACTION when used as a noun
        claim2 = extractor._analyze_statement(
            "TEST", 2025, "Q4", "C2", "CEO", "CEO",
            "Our gross margin expanded under the new contract structure."
        )
        assert claim2 is not None
        assert claim2.claim_type == "gross_margin"
        assert claim2.sentiment_direction == "EXPANSION"

    def test_negation_inverts_sentiment(self):
        extractor = ClaimExtractor()
        # "not compress" should invert negative word into positive/expansion
        claim = extractor._analyze_statement(
            "TEST", 2025, "Q4", "C3", "CFO", "CFO",
            "Our gross margins did not compress during the quarter."
        )
        assert claim is not None
        assert claim.claim_type == "gross_margin"
        assert claim.sentiment_direction == "EXPANSION"

        # "without any decline" should invert decline
        claim2 = extractor._analyze_statement(
            "TEST", 2025, "Q4", "C4", "CFO", "CFO",
            "We scaled capex without any decline in efficiency."
        )
        assert claim2 is not None
        assert claim2.claim_type == "capex_efficiency"
        assert claim2.sentiment_direction == "EXPANSION"

    def test_mixed_sentiment_resolves_to_neutral(self):
        extractor = ClaimExtractor()
        # Mixed statement: "expanded" and "headwind"
        claim = extractor._analyze_statement(
            "TEST", 2025, "Q4", "C5", "CEO", "CEO",
            "Our gross margins expanded in software, but hardware experienced significant headwinds."
        )
        assert claim is not None
        assert claim.claim_type == "gross_margin"
        assert claim.sentiment_direction == "NEUTRAL"
