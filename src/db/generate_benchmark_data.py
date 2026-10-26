"""Generate mathematically coherent synthetic benchmark data for four fictional companies."""

import json
from pathlib import Path


def generate_benchmark_datasets(output_base_dir: Path):
    output_base_dir.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # 1. AuraCloud Systems (AURA) - Margin Dilution
    # =========================================================================
    aura_dir = output_base_dir / "auracloud"
    aura_dir.mkdir(parents=True, exist_ok=True)

    aura_company = {
        "ticker": "AURA",
        "name": "AuraCloud Systems Inc.",
        "sector": "Enterprise Software",
        "business_model": "B2B SaaS / Workflow Automation",
        "fiscal_year_end": "December 31",
        "currency": "USD",
        "is_control_baseline": False
    }
    with open(aura_dir / "company.json", "w") as f:
        json.dump(aura_company, f, indent=2)

    aura_fin = [
        {"id": "AURA_2024_Q1", "ticker": "AURA", "fiscal_year": 2024, "fiscal_quarter": "Q1", "period_end_date": "2024-03-31",
         "total_revenue": 100.0, "cost_of_goods_sold": 21.0, "gross_profit": 79.0, "rd_expense": 20.0, "sm_expense": 30.0,
         "ga_expense": 12.0, "operating_income": 17.0, "net_income": 14.0, "operating_cash_flow": 25.0, "capital_expenditures": 5.0,
         "free_cash_flow": 20.0, "cash_and_equivalents": 150.0, "deferred_revenue": 80.0},
        {"id": "AURA_2024_Q2", "ticker": "AURA", "fiscal_year": 2024, "fiscal_quarter": "Q2", "period_end_date": "2024-06-30",
         "total_revenue": 108.0, "cost_of_goods_sold": 24.8, "gross_profit": 83.2, "rd_expense": 22.0, "sm_expense": 32.0,
         "ga_expense": 12.5, "operating_income": 16.7, "net_income": 13.5, "operating_cash_flow": 26.0, "capital_expenditures": 5.5,
         "free_cash_flow": 20.5, "cash_and_equivalents": 165.0, "deferred_revenue": 84.0},
        {"id": "AURA_2024_Q3", "ticker": "AURA", "fiscal_year": 2024, "fiscal_quarter": "Q3", "period_end_date": "2024-09-30",
         "total_revenue": 118.0, "cost_of_goods_sold": 30.7, "gross_profit": 87.3, "rd_expense": 24.0, "sm_expense": 34.0,
         "ga_expense": 13.0, "operating_income": 16.3, "net_income": 13.0, "operating_cash_flow": 27.0, "capital_expenditures": 6.0,
         "free_cash_flow": 21.0, "cash_and_equivalents": 178.0, "deferred_revenue": 89.0},
        {"id": "AURA_2024_Q4", "ticker": "AURA", "fiscal_year": 2024, "fiscal_quarter": "Q4", "period_end_date": "2024-12-31",
         "total_revenue": 128.0, "cost_of_goods_sold": 37.1, "gross_profit": 90.9, "rd_expense": 26.0, "sm_expense": 36.0,
         "ga_expense": 13.5, "operating_income": 15.4, "net_income": 12.0, "operating_cash_flow": 28.0, "capital_expenditures": 6.5,
         "free_cash_flow": 21.5, "cash_and_equivalents": 190.0, "deferred_revenue": 95.0},
        {"id": "AURA_2025_Q1", "ticker": "AURA", "fiscal_year": 2025, "fiscal_quarter": "Q1", "period_end_date": "2025-03-31",
         "total_revenue": 135.0, "cost_of_goods_sold": 43.2, "gross_profit": 91.8, "rd_expense": 28.0, "sm_expense": 38.0,
         "ga_expense": 14.0, "operating_income": 11.8, "net_income": 9.0, "operating_cash_flow": 28.5, "capital_expenditures": 7.0,
         "free_cash_flow": 21.5, "cash_and_equivalents": 200.0, "deferred_revenue": 98.0},
        {"id": "AURA_2025_Q2", "ticker": "AURA", "fiscal_year": 2025, "fiscal_quarter": "Q2", "period_end_date": "2025-06-30",
         "total_revenue": 143.0, "cost_of_goods_sold": 48.6, "gross_profit": 94.4, "rd_expense": 30.0, "sm_expense": 40.0,
         "ga_expense": 14.5, "operating_income": 9.9, "net_income": 7.5, "operating_cash_flow": 29.0, "capital_expenditures": 7.5,
         "free_cash_flow": 21.5, "cash_and_equivalents": 210.0, "deferred_revenue": 102.0},
        {"id": "AURA_2025_Q3", "ticker": "AURA", "fiscal_year": 2025, "fiscal_quarter": "Q3", "period_end_date": "2025-09-30",
         "total_revenue": 152.0, "cost_of_goods_sold": 56.2, "gross_profit": 95.8, "rd_expense": 32.0, "sm_expense": 42.0,
         "ga_expense": 15.0, "operating_income": 6.8, "net_income": 5.0, "operating_cash_flow": 29.5, "capital_expenditures": 8.0,
         "free_cash_flow": 21.5, "cash_and_equivalents": 220.0, "deferred_revenue": 106.0},
        {"id": "AURA_2025_Q4", "ticker": "AURA", "fiscal_year": 2025, "fiscal_quarter": "Q4", "period_end_date": "2025-12-31",
         "total_revenue": 160.0, "cost_of_goods_sold": 62.4, "gross_profit": 97.6, "rd_expense": 34.0, "sm_expense": 44.0,
         "ga_expense": 15.5, "operating_income": 4.1, "net_income": 3.0, "operating_cash_flow": 30.0, "capital_expenditures": 8.5,
         "free_cash_flow": 21.5, "cash_and_equivalents": 230.0, "deferred_revenue": 110.0}
    ]
    with open(aura_dir / "financials.json", "w") as f:
        json.dump(aura_fin, f, indent=2)

    aura_seg = [
        {"id": "AURA_SEG_2025_Q4_CORE", "ticker": "AURA", "fiscal_year": 2025, "fiscal_quarter": "Q4", "segment_name": "Core Workflow Platform",
         "segment_revenue": 115.0, "segment_gross_margin": 0.74, "is_reported_organic": True, "notes": "Legacy workflow subscription"},
        {"id": "AURA_SEG_2025_Q4_AI", "ticker": "AURA", "fiscal_year": 2025, "fiscal_quarter": "Q4", "segment_name": "AI Copilot & Services",
         "segment_revenue": 45.0, "segment_gross_margin": 0.28, "is_reported_organic": True, "notes": "Generative AI add-on carrying high third-party GPU and token inference costs"}
    ]
    with open(aura_dir / "segments.json", "w") as f:
        json.dump(aura_seg, f, indent=2)

    aura_tx = [
        {"id": "AURA_TX_2025_Q4_PREP", "ticker": "AURA", "fiscal_year": 2025, "fiscal_quarter": "Q4", "section": "PREPARED_REMARKS",
         "speaker_name": "Elena Rostova", "speaker_title": "Chief Executive Officer",
         "content": "We had an outstanding fourth quarter, with total revenue expanding to $160 million. Over 70% of our enterprise customer tier has enabled our AI Copilot suite. We are demonstrating rapid adoption and operating leverage, validating our position as the mission-critical AI platform for enterprise workflows.",
         "sequence_order": 1},
        {"id": "AURA_TX_2025_Q4_QA", "ticker": "AURA", "fiscal_year": 2025, "fiscal_quarter": "Q4", "section": "ANALYST_QA",
         "speaker_name": "Marcus Vance", "speaker_title": "Managing Director, Equity Research",
         "content": "Elena, congratulations on the top-line growth. However, looking at the cost structure, gross margins contracted from 79% in Q1 2024 to 61% in Q4 2025, an 1,800 basis point drop. How much of this is structural cloud inference costs versus temporary scaling friction?",
         "sequence_order": 2},
        {"id": "AURA_TX_2025_Q4_CFO", "ticker": "AURA", "fiscal_year": 2025, "fiscal_quarter": "Q4", "section": "ANALYST_QA",
         "speaker_name": "David Chen", "speaker_title": "Chief Financial Officer",
         "content": "Thanks Marcus. What we are seeing is unprecedented user engagement. When customers run millions of Copilot sessions, we capture long-term platform stickiness. We believe the customer lifetime value and enterprise expansion opportunities will dwarf any near-term gross margin fluctuations as model costs naturally decline over time.",
         "sequence_order": 3}
    ]
    with open(aura_dir / "transcripts.json", "w") as f:
        json.dump(aura_tx, f, indent=2)

    # =========================================================================
    # 2. NexusEnterprise Corp (NXUS) - Capital Sinkhole
    # =========================================================================
    nxus_dir = output_base_dir / "nexusenterprise"
    nxus_dir.mkdir(parents=True, exist_ok=True)

    nxus_company = {
        "ticker": "NXUS",
        "name": "NexusEnterprise Corp",
        "sector": "Cloud Data Infrastructure",
        "business_model": "Enterprise Infrastructure & Data Warehousing",
        "fiscal_year_end": "December 31",
        "currency": "USD",
        "is_control_baseline": False
    }
    with open(nxus_dir / "company.json", "w") as f:
        json.dump(nxus_company, f, indent=2)

    nxus_fin = [
        {"id": "NXUS_2024_Q1", "ticker": "NXUS", "fiscal_year": 2024, "fiscal_quarter": "Q1", "period_end_date": "2024-03-31",
         "total_revenue": 200.0, "cost_of_goods_sold": 60.0, "gross_profit": 140.0, "rd_expense": 45.0, "sm_expense": 40.0,
         "ga_expense": 20.0, "operating_income": 35.0, "net_income": 28.0, "operating_cash_flow": 45.0, "capital_expenditures": 30.0,
         "free_cash_flow": 15.0, "cash_and_equivalents": 400.0, "deferred_revenue": 180.0},
        {"id": "NXUS_2024_Q2", "ticker": "NXUS", "fiscal_year": 2024, "fiscal_quarter": "Q2", "period_end_date": "2024-06-30",
         "total_revenue": 202.0, "cost_of_goods_sold": 61.0, "gross_profit": 141.0, "rd_expense": 46.0, "sm_expense": 40.0,
         "ga_expense": 20.0, "operating_income": 35.0, "net_income": 28.0, "operating_cash_flow": 45.0, "capital_expenditures": 35.0,
         "free_cash_flow": 10.0, "cash_and_equivalents": 395.0, "deferred_revenue": 181.0},
        {"id": "NXUS_2024_Q3", "ticker": "NXUS", "fiscal_year": 2024, "fiscal_quarter": "Q3", "period_end_date": "2024-09-30",
         "total_revenue": 203.0, "cost_of_goods_sold": 62.0, "gross_profit": 141.0, "rd_expense": 47.0, "sm_expense": 41.0,
         "ga_expense": 20.0, "operating_income": 33.0, "net_income": 26.0, "operating_cash_flow": 44.0, "capital_expenditures": 38.0,
         "free_cash_flow": 6.0, "cash_and_equivalents": 390.0, "deferred_revenue": 182.0},
        {"id": "NXUS_2024_Q4", "ticker": "NXUS", "fiscal_year": 2024, "fiscal_quarter": "Q4", "period_end_date": "2024-12-31",
         "total_revenue": 205.0, "cost_of_goods_sold": 63.0, "gross_profit": 142.0, "rd_expense": 48.0, "sm_expense": 42.0,
         "ga_expense": 20.0, "operating_income": 32.0, "net_income": 25.0, "operating_cash_flow": 44.0, "capital_expenditures": 42.0,
         "free_cash_flow": 2.0, "cash_and_equivalents": 380.0, "deferred_revenue": 183.0},
        {"id": "NXUS_2025_Q1", "ticker": "NXUS", "fiscal_year": 2025, "fiscal_quarter": "Q1", "period_end_date": "2025-03-31",
         "total_revenue": 206.0, "cost_of_goods_sold": 64.0, "gross_profit": 142.0, "rd_expense": 50.0, "sm_expense": 43.0,
         "ga_expense": 21.0, "operating_income": 28.0, "net_income": 22.0, "operating_cash_flow": 43.0, "capital_expenditures": 60.0,
         "free_cash_flow": -17.0, "cash_and_equivalents": 350.0, "deferred_revenue": 184.0},
        {"id": "NXUS_2025_Q2", "ticker": "NXUS", "fiscal_year": 2025, "fiscal_quarter": "Q2", "period_end_date": "2025-06-30",
         "total_revenue": 207.0, "cost_of_goods_sold": 65.0, "gross_profit": 142.0, "rd_expense": 52.0, "sm_expense": 44.0,
         "ga_expense": 21.0, "operating_income": 25.0, "net_income": 19.0, "operating_cash_flow": 43.0, "capital_expenditures": 75.0,
         "free_cash_flow": -32.0, "cash_and_equivalents": 310.0, "deferred_revenue": 185.0},
        {"id": "NXUS_2025_Q3", "ticker": "NXUS", "fiscal_year": 2025, "fiscal_quarter": "Q3", "period_end_date": "2025-09-30",
         "total_revenue": 208.0, "cost_of_goods_sold": 66.0, "gross_profit": 142.0, "rd_expense": 54.0, "sm_expense": 45.0,
         "ga_expense": 21.0, "operating_income": 22.0, "net_income": 16.0, "operating_cash_flow": 44.0, "capital_expenditures": 88.0,
         "free_cash_flow": -44.0, "cash_and_equivalents": 260.0, "deferred_revenue": 186.0},
        {"id": "NXUS_2025_Q4", "ticker": "NXUS", "fiscal_year": 2025, "fiscal_quarter": "Q4", "period_end_date": "2025-12-31",
         "total_revenue": 210.0, "cost_of_goods_sold": 67.0, "gross_profit": 143.0, "rd_expense": 56.0, "sm_expense": 46.0,
         "ga_expense": 21.0, "operating_income": 20.0, "net_income": 14.0, "operating_cash_flow": 45.0, "capital_expenditures": 96.0,
         "free_cash_flow": -51.0, "cash_and_equivalents": 205.0, "deferred_revenue": 188.0}
    ]
    with open(nxus_dir / "financials.json", "w") as f:
        json.dump(nxus_fin, f, indent=2)

    nxus_seg = [
        {"id": "NXUS_SEG_2025_Q4_STORAGE", "ticker": "NXUS", "fiscal_year": 2025, "fiscal_quarter": "Q4", "segment_name": "Core Enterprise Data Platform",
         "segment_revenue": 195.0, "segment_gross_margin": 0.70, "is_reported_organic": True, "notes": "Legacy enterprise database clusters"},
        {"id": "NXUS_SEG_2025_Q4_GPU", "ticker": "NXUS", "fiscal_year": 2025, "fiscal_quarter": "Q4", "segment_name": "AI Dedicated Cluster Compute",
         "segment_revenue": 15.0, "segment_gross_margin": 0.40, "is_reported_organic": True, "notes": "Newly deployed GPU infrastructure running at low utilization"}
    ]
    with open(nxus_dir / "segments.json", "w") as f:
        json.dump(nxus_seg, f, indent=2)

    nxus_tx = [
        {"id": "NXUS_TX_2025_Q4_PREP", "ticker": "NXUS", "fiscal_year": 2025, "fiscal_quarter": "Q4", "section": "PREPARED_REMARKS",
         "speaker_name": "Arthur Sterling", "speaker_title": "Chairman & Chief Executive Officer",
         "content": "We are making generational capital investments in next-generation GPU clusters and high-density liquid-cooled compute facilities to capture what we forecast as a $500 billion enterprise AI total addressable market. Demand for foundational compute has never been stronger.",
         "sequence_order": 1},
        {"id": "NXUS_TX_2025_Q4_QA", "ticker": "NXUS", "fiscal_year": 2025, "fiscal_quarter": "Q4", "section": "ANALYST_QA",
         "speaker_name": "Sarah Jenkins", "speaker_title": "Lead Software Analyst, Equity Research",
         "content": "Arthur, your Capex expanded by 220% YoY to $96 million this quarter, while full-year Free Cash Flow turned deeply negative at negative $144 million. However, incremental revenue growth was only $5 million YoY (+2.4%). When do you realistically anticipate ROIC inflecting to cover this cash burn?",
         "sequence_order": 2},
        {"id": "NXUS_TX_2025_Q4_CFO", "ticker": "NXUS", "fiscal_year": 2025, "fiscal_quarter": "Q4", "section": "ANALYST_QA",
         "speaker_name": "Brian Cole", "speaker_title": "Chief Financial Officer",
         "content": "Sarah, this is long-cycle infrastructure. Customer pilot commitments take 18 to 24 months to migrate production data workloads. We are completely comfortable utilizing our balance sheet liquidity because securing compute capacity ahead of the curve is our primary competitive moat.",
         "sequence_order": 3}
    ]
    with open(nxus_dir / "transcripts.json", "w") as f:
        json.dump(nxus_tx, f, indent=2)

    # =========================================================================
    # 3. Synthetix Data Systems (SYNX) - Revenue Reclassification
    # =========================================================================
    synx_dir = output_base_dir / "synthetix"
    synx_dir.mkdir(parents=True, exist_ok=True)

    synx_company = {
        "ticker": "SYNX",
        "name": "Synthetix Data Systems Inc.",
        "sector": "Database Management",
        "business_model": "Distributed SQL / Operational Database",
        "fiscal_year_end": "December 31",
        "currency": "USD",
        "is_control_baseline": False
    }
    with open(synx_dir / "company.json", "w") as f:
        json.dump(synx_company, f, indent=2)

    synx_fin = [
        {"id": "SYNX_2024_Q1", "ticker": "SYNX", "fiscal_year": 2024, "fiscal_quarter": "Q1", "period_end_date": "2024-03-31",
         "total_revenue": 120.0, "cost_of_goods_sold": 26.4, "gross_profit": 93.6, "rd_expense": 30.0, "sm_expense": 36.0,
         "ga_expense": 14.0, "operating_income": 13.6, "net_income": 10.5, "operating_cash_flow": 28.0, "capital_expenditures": 6.0,
         "free_cash_flow": 22.0, "cash_and_equivalents": 180.0, "deferred_revenue": 95.0},
        {"id": "SYNX_2024_Q2", "ticker": "SYNX", "fiscal_year": 2024, "fiscal_quarter": "Q2", "period_end_date": "2024-06-30",
         "total_revenue": 124.0, "cost_of_goods_sold": 27.3, "gross_profit": 96.7, "rd_expense": 31.0, "sm_expense": 37.0,
         "ga_expense": 14.0, "operating_income": 14.7, "net_income": 11.2, "operating_cash_flow": 29.0, "capital_expenditures": 6.0,
         "free_cash_flow": 23.0, "cash_and_equivalents": 190.0, "deferred_revenue": 98.0},
        {"id": "SYNX_2024_Q3", "ticker": "SYNX", "fiscal_year": 2024, "fiscal_quarter": "Q3", "period_end_date": "2024-09-30",
         "total_revenue": 128.0, "cost_of_goods_sold": 28.2, "gross_profit": 99.8, "rd_expense": 32.0, "sm_expense": 38.0,
         "ga_expense": 14.5, "operating_income": 15.3, "net_income": 11.8, "operating_cash_flow": 30.0, "capital_expenditures": 6.5,
         "free_cash_flow": 23.5, "cash_and_equivalents": 200.0, "deferred_revenue": 102.0},
        {"id": "SYNX_2024_Q4", "ticker": "SYNX", "fiscal_year": 2024, "fiscal_quarter": "Q4", "period_end_date": "2024-12-31",
         "total_revenue": 132.0, "cost_of_goods_sold": 29.0, "gross_profit": 103.0, "rd_expense": 33.0, "sm_expense": 39.0,
         "ga_expense": 15.0, "operating_income": 16.0, "net_income": 12.5, "operating_cash_flow": 31.0, "capital_expenditures": 7.0,
         "free_cash_flow": 24.0, "cash_and_equivalents": 210.0, "deferred_revenue": 106.0},
        {"id": "SYNX_2025_Q1", "ticker": "SYNX", "fiscal_year": 2025, "fiscal_quarter": "Q1", "period_end_date": "2025-03-31",
         "total_revenue": 136.0, "cost_of_goods_sold": 30.0, "gross_profit": 106.0, "rd_expense": 34.0, "sm_expense": 40.0,
         "ga_expense": 15.0, "operating_income": 17.0, "net_income": 13.0, "operating_cash_flow": 32.0, "capital_expenditures": 7.0,
         "free_cash_flow": 25.0, "cash_and_equivalents": 220.0, "deferred_revenue": 110.0},
        {"id": "SYNX_2025_Q2", "ticker": "SYNX", "fiscal_year": 2025, "fiscal_quarter": "Q2", "period_end_date": "2025-06-30",
         "total_revenue": 140.0, "cost_of_goods_sold": 31.0, "gross_profit": 109.0, "rd_expense": 35.0, "sm_expense": 41.0,
         "ga_expense": 15.5, "operating_income": 17.5, "net_income": 13.5, "operating_cash_flow": 33.0, "capital_expenditures": 7.5,
         "free_cash_flow": 25.5, "cash_and_equivalents": 230.0, "deferred_revenue": 113.0},
        {"id": "SYNX_2025_Q3", "ticker": "SYNX", "fiscal_year": 2025, "fiscal_quarter": "Q3", "period_end_date": "2025-09-30",
         "total_revenue": 145.0, "cost_of_goods_sold": 32.0, "gross_profit": 113.0, "rd_expense": 36.0, "sm_expense": 42.0,
         "ga_expense": 16.0, "operating_income": 19.0, "net_income": 14.5, "operating_cash_flow": 34.0, "capital_expenditures": 8.0,
         "free_cash_flow": 26.0, "cash_and_equivalents": 240.0, "deferred_revenue": 117.0},
        {"id": "SYNX_2025_Q4", "ticker": "SYNX", "fiscal_year": 2025, "fiscal_quarter": "Q4", "period_end_date": "2025-12-31",
         "total_revenue": 150.0, "cost_of_goods_sold": 33.0, "gross_profit": 117.0, "rd_expense": 37.0, "sm_expense": 43.0,
         "ga_expense": 16.5, "operating_income": 20.5, "net_income": 15.5, "operating_cash_flow": 35.0, "capital_expenditures": 8.0,
         "free_cash_flow": 27.0, "cash_and_equivalents": 250.0, "deferred_revenue": 120.0}
    ]
    with open(synx_dir / "financials.json", "w") as f:
        json.dump(synx_fin, f, indent=2)

    synx_seg = [
        {"id": "SYNX_SEG_2025_Q4_LEGACY", "ticker": "SYNX", "fiscal_year": 2025, "fiscal_quarter": "Q4", "segment_name": "Core Enterprise SQL",
         "segment_revenue": 70.0, "segment_gross_margin": 0.80, "is_reported_organic": True, "notes": "Legacy transactional database subscriptions"},
        {"id": "SYNX_SEG_2025_Q4_RECLASS", "ticker": "SYNX", "fiscal_year": 2025, "fiscal_quarter": "Q4", "segment_name": "Synthetix AI Platform Edition",
         "segment_revenue": 65.0, "segment_gross_margin": 0.77, "is_reported_organic": False, "notes": "Existing SQL database contracts retroactively reclassified into AI Platform tier upon renewal with bundled vector index"},
        {"id": "SYNX_SEG_2025_Q4_ORGANIC", "ticker": "SYNX", "fiscal_year": 2025, "fiscal_quarter": "Q4", "segment_name": "Net-New AI Vector Store",
         "segment_revenue": 15.0, "segment_gross_margin": 0.75, "is_reported_organic": True, "notes": "Genuine net-new customer expansion for AI features"}
    ]
    with open(synx_dir / "segments.json", "w") as f:
        json.dump(synx_seg, f, indent=2)

    synx_tx = [
        {"id": "SYNX_TX_2025_Q4_PREP", "ticker": "SYNX", "fiscal_year": 2025, "fiscal_quarter": "Q4", "section": "PREPARED_REMARKS",
         "speaker_name": "Rajiv Mehta", "speaker_title": "Chief Executive Officer",
         "content": "I am thrilled to announce we crossed a major corporate milestone, reaching $80 million in AI-driven Annual Recurring Revenue this quarter. Our AI Platform Edition is rapidly replacing legacy relational databases across Fortune 500 accounts as the default database for generative applications.",
         "sequence_order": 1},
        {"id": "SYNX_TX_2025_Q4_QA", "ticker": "SYNX", "fiscal_year": 2025, "fiscal_quarter": "Q4", "section": "ANALYST_QA",
         "speaker_name": "Jason Klein", "speaker_title": "Senior Research Analyst, Equity Research",
         "content": "Rajiv, on the $80 million AI ARR figure: footnote 4 in the segment disclosure notes that $65 million of that revenue reflects existing core database renewals migrated into the new SKU with vector features included. Can you disclose what your organic, net-new AI ARR expansion rate was this quarter excluding renewals?",
         "sequence_order": 2},
        {"id": "SYNX_TX_2025_Q4_CFO", "ticker": "SYNX", "fiscal_year": 2025, "fiscal_quarter": "Q4", "section": "ANALYST_QA",
         "speaker_name": "Amanda White", "speaker_title": "Chief Financial Officer",
         "content": "Jason, our customers do not separate their data architecture into AI vs non-AI anymore. When an enterprise renews their database with Synthetix, they are running hybrid vector-relational workloads. We manage the platform holistically, and our consolidated net revenue retention remains very healthy at 112%.",
         "sequence_order": 3}
    ]
    with open(synx_dir / "transcripts.json", "w") as f:
        json.dump(synx_tx, f, indent=2)

    # =========================================================================
    # 4. Vortex Analytics (VORS) - Clean Control Group
    # =========================================================================
    vrtx_dir = output_base_dir / "vortex_control"
    vrtx_dir.mkdir(parents=True, exist_ok=True)

    vrtx_company = {
        "ticker": "VORS",
        "name": "Vortex Analytics Inc.",
        "sector": "Cloud Observability & Security",
        "business_model": "SaaS Observability & Telemetry",
        "fiscal_year_end": "December 31",
        "currency": "USD",
        "is_control_baseline": True
    }
    with open(vrtx_dir / "company.json", "w") as f:
        json.dump(vrtx_company, f, indent=2)

    vrtx_fin = [
        {"id": "VORS_2024_Q1", "ticker": "VORS", "fiscal_year": 2024, "fiscal_quarter": "Q1", "period_end_date": "2024-03-31",
         "total_revenue": 80.0, "cost_of_goods_sold": 16.8, "gross_profit": 63.2, "rd_expense": 18.0, "sm_expense": 24.0,
         "ga_expense": 8.0, "operating_income": 13.2, "net_income": 10.5, "operating_cash_flow": 24.0, "capital_expenditures": 5.0,
         "free_cash_flow": 19.0, "cash_and_equivalents": 120.0, "deferred_revenue": 60.0},
        {"id": "VORS_2024_Q2", "ticker": "VORS", "fiscal_year": 2024, "fiscal_quarter": "Q2", "period_end_date": "2024-06-30",
         "total_revenue": 83.0, "cost_of_goods_sold": 17.4, "gross_profit": 65.6, "rd_expense": 18.5, "sm_expense": 24.5,
         "ga_expense": 8.2, "operating_income": 14.4, "net_income": 11.2, "operating_cash_flow": 25.0, "capital_expenditures": 5.2,
         "free_cash_flow": 19.8, "cash_and_equivalents": 130.0, "deferred_revenue": 62.0},
        {"id": "VORS_2024_Q3", "ticker": "VORS", "fiscal_year": 2024, "fiscal_quarter": "Q3", "period_end_date": "2024-09-30",
         "total_revenue": 86.5, "cost_of_goods_sold": 18.1, "gross_profit": 68.4, "rd_expense": 19.0, "sm_expense": 25.0,
         "ga_expense": 8.5, "operating_income": 15.9, "net_income": 12.4, "operating_cash_flow": 26.0, "capital_expenditures": 5.5,
         "free_cash_flow": 20.5, "cash_and_equivalents": 140.0, "deferred_revenue": 65.0},
        {"id": "VORS_2024_Q4", "ticker": "VORS", "fiscal_year": 2024, "fiscal_quarter": "Q4", "period_end_date": "2024-12-31",
         "total_revenue": 90.0, "cost_of_goods_sold": 18.9, "gross_profit": 71.1, "rd_expense": 19.5, "sm_expense": 25.5,
         "ga_expense": 8.8, "operating_income": 17.3, "net_income": 13.5, "operating_cash_flow": 27.0, "capital_expenditures": 5.8,
         "free_cash_flow": 21.2, "cash_and_equivalents": 150.0, "deferred_revenue": 68.0},
        {"id": "VORS_2025_Q1", "ticker": "VORS", "fiscal_year": 2025, "fiscal_quarter": "Q1", "period_end_date": "2025-03-31",
         "total_revenue": 93.5, "cost_of_goods_sold": 19.6, "gross_profit": 73.9, "rd_expense": 20.0, "sm_expense": 26.0,
         "ga_expense": 9.0, "operating_income": 18.9, "net_income": 14.8, "operating_cash_flow": 28.0, "capital_expenditures": 6.0,
         "free_cash_flow": 22.0, "cash_and_equivalents": 160.0, "deferred_revenue": 71.0},
        {"id": "VORS_2025_Q2", "ticker": "VORS", "fiscal_year": 2025, "fiscal_quarter": "Q2", "period_end_date": "2025-06-30",
         "total_revenue": 97.0, "cost_of_goods_sold": 20.3, "gross_profit": 76.7, "rd_expense": 20.5, "sm_expense": 26.5,
         "ga_expense": 9.2, "operating_income": 20.5, "net_income": 16.0, "operating_cash_flow": 29.0, "capital_expenditures": 6.2,
         "free_cash_flow": 22.8, "cash_and_equivalents": 170.0, "deferred_revenue": 74.0},
        {"id": "VORS_2025_Q3", "ticker": "VORS", "fiscal_year": 2025, "fiscal_quarter": "Q3", "period_end_date": "2025-09-30",
         "total_revenue": 101.0, "cost_of_goods_sold": 21.1, "gross_profit": 79.9, "rd_expense": 21.0, "sm_expense": 27.0,
         "ga_expense": 9.5, "operating_income": 22.4, "net_income": 17.5, "operating_cash_flow": 30.0, "capital_expenditures": 6.5,
         "free_cash_flow": 23.5, "cash_and_equivalents": 180.0, "deferred_revenue": 77.0},
        {"id": "VORS_2025_Q4", "ticker": "VORS", "fiscal_year": 2025, "fiscal_quarter": "Q4", "period_end_date": "2025-12-31",
         "total_revenue": 105.0, "cost_of_goods_sold": 21.9, "gross_profit": 83.1, "rd_expense": 21.5, "sm_expense": 27.5,
         "ga_expense": 9.8, "operating_income": 24.3, "net_income": 19.0, "operating_cash_flow": 31.0, "capital_expenditures": 6.8,
         "free_cash_flow": 24.2, "cash_and_equivalents": 192.0, "deferred_revenue": 80.0}
    ]
    with open(vrtx_dir / "financials.json", "w") as f:
        json.dump(vrtx_fin, f, indent=2)

    vrtx_seg = [
        {"id": "VORS_SEG_2025_Q4_CORE", "ticker": "VORS", "fiscal_year": 2025, "fiscal_quarter": "Q4", "segment_name": "Infrastructure Telemetry & Logs",
         "segment_revenue": 85.0, "segment_gross_margin": 0.79, "is_reported_organic": True, "notes": "Core observability platform"},
        {"id": "VORS_SEG_2025_Q4_AI", "ticker": "VORS", "fiscal_year": 2025, "fiscal_quarter": "Q4", "segment_name": "Automated Anomaly Detection (AI Engine)",
         "segment_revenue": 20.0, "segment_gross_margin": 0.77, "is_reported_organic": True, "notes": "High-margin proprietary lightweight anomaly detector running on-premise and edge"}
    ]
    with open(vrtx_dir / "segments.json", "w") as f:
        json.dump(vrtx_seg, f, indent=2)

    vrtx_tx = [
        {"id": "VORS_TX_2025_Q4_PREP", "ticker": "VORS", "fiscal_year": 2025, "fiscal_quarter": "Q4", "section": "PREPARED_REMARKS",
         "speaker_name": "Simon Gallagher", "speaker_title": "President & Chief Executive Officer",
         "content": "Our Q4 performance reflects steady, disciplined execution. Full-year revenue crossed $396 million, growing 17% YoY, while maintaining industry-leading gross margins of 79.1%. Our proprietary AI anomaly detection modules run locally on client clusters, allowing us to expand analytical value without absorbing third-party GPU cloud costs.",
         "sequence_order": 1},
        {"id": "VORS_TX_2025_Q4_QA", "ticker": "VORS", "fiscal_year": 2025, "fiscal_quarter": "Q4", "section": "ANALYST_QA",
         "speaker_name": "Emily Watson", "speaker_title": "Executive Director, Equity Research",
         "content": "Simon, we've seen competitors in the observability space experience gross margin pressure from LLM inference bills. How has Vortex managed to keep gross margin stable above 79% while rolling out generative telemetry summaries?",
         "sequence_order": 2},
        {"id": "VORS_TX_2025_Q4_CFO", "ticker": "VORS", "fiscal_year": 2025, "fiscal_quarter": "Q4", "section": "ANALYST_QA",
         "speaker_name": "Rachel Adams", "speaker_title": "Chief Financial Officer",
         "content": "Emily, from day one our engineering thesis was edge-first distillation. We avoid unconstrained external LLM API calls on high-frequency log streams. Our customers get instant root-cause analysis, and our unit economics remain highly profitable. We generated $24.2 million in Free Cash Flow this quarter.",
         "sequence_order": 3}
    ]
    with open(vrtx_dir / "transcripts.json", "w") as f:
        json.dump(vrtx_tx, f, indent=2)


if __name__ == "__main__":
    base = Path(__file__).resolve().parent.parent.parent / "data" / "benchmark"
    generate_benchmark_datasets(base)
    print(f"Successfully generated all benchmark datasets in {base}")
