"""Unit tests for the Semantic Metrics Layer and automated financial divergence triggers."""

from pathlib import Path
import pytest
from src.db.schema import FinancialDatabase, get_default_db
from src.db.semantic_metrics import SemanticMetricsLayer


@pytest.fixture(scope="module")
def semantic_layer():
    bench_dir = Path(__file__).resolve().parent.parent / "data" / "benchmark"
    db = get_default_db(bench_dir)
    layer = SemanticMetricsLayer(db.conn)
    yield layer
    db.close()


def test_margin_trends_calculation(semantic_layer: SemanticMetricsLayer):
    """Verify margin calculations and YoY/QoQ trend calculation."""
    df = semantic_layer.get_quarterly_margin_trends("AURA")
    assert len(df) == 8

    # Q1 2024 Gross Margin: 79.0 / 100.0 = 0.79
    assert abs(df.iloc[0]["gross_margin"] - 0.79) < 1e-4

    # Q4 2025 Gross Margin: 97.6 / 160.0 = 0.61
    assert abs(df.iloc[-1]["gross_margin"] - 0.61) < 1e-4

    # Monotonic drop check
    assert df.iloc[-1]["gross_margin"] < df.iloc[0]["gross_margin"]


def test_auracloud_triggers_margin_dilution(semantic_layer: SemanticMetricsLayer):
    """AuraCloud must trigger gross margin dilution flag (> 500 bps drop)."""
    flags = semantic_layer.calculate_audit_flags("AURA")
    assert flags["gm_dilution_flag"] is True
    assert flags["total_gm_delta_bps"] <= -1500.0  # Actually ~ -1800 bps
    assert flags["capex_sinkhole_flag"] is False


def test_nexus_triggers_capex_sinkhole(semantic_layer: SemanticMetricsLayer):
    """NexusEnterprise must trigger capex sinkhole flag (Capex growth >> revenue growth + negative FCF)."""
    flags = semantic_layer.calculate_audit_flags("NXUS")
    assert flags["capex_sinkhole_flag"] is True
    assert flags["latest_free_cash_flow"] < 0
    assert flags["capex_growth_yoy"] > 1.0  # > 100% growth


def test_synthetix_triggers_reclassification(semantic_layer: SemanticMetricsLayer):
    """Synthetix must trigger revenue reclassification flag (>= 30% segment revenue reclassified)."""
    flags = semantic_layer.calculate_audit_flags("SYNX")
    assert flags["revenue_reclassification_flag"] is True
    assert flags["reclassification_ratio"] >= 0.40  # Actually ~ 43% of total segment revenue


def test_vortex_control_triggers_zero_flags(semantic_layer: SemanticMetricsLayer):
    """Control company (Vortex Analytics) must produce zero false positive flags."""
    flags = semantic_layer.calculate_audit_flags("VORS")
    assert flags["gm_dilution_flag"] is False
    assert flags["capex_sinkhole_flag"] is False
    assert flags["revenue_reclassification_flag"] is False
    assert flags["latest_free_cash_flow"] > 0
    assert flags["latest_gross_margin"] >= 0.78
