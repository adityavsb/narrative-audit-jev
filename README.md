# Narrative Audit JEV (`narrative-audit-jev`)

> **Research prototype:** narrative–financial consistency checks over a synthetic benchmark  
> *Multi-agent Text2SQL, claim extraction, and numeric reconciliation — not a PCAOB/GAAS audit product.*

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Database](https://img.shields.io/badge/DuckDB-1.0+-yellow.svg)](https://duckdb.org/)
[![Architecture](https://img.shields.io/badge/Orchestration-Multi--Agent%20Graph-orange.svg)]()
[![Evaluation](https://img.shields.io/badge/Methodology-Generative%20vs%20JEV-purple.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

### Disclaimer
*For academic research and systems benchmarking only. Not financial, investment, legal, or tax advice.
All companies, tickers, speakers, and dialogue in `data/` are **fictional**. No affiliation with any real
issuer, bank, or analyst firm is implied. This is not an external audit or compliance certification.*

---

## Overview

In corporate reporting, equity research, and institutional credit analysis, reconciling forward-looking qualitative commentary (earnings call transcripts, investor decks, executive remarks) with audited quantitative financial disclosures (SEC 10-K, 10-Q XBRL statements) is a labor-intensive, error-prone process.

Analysts frequently face **material narrative divergence**:
1. **Gross Margin Dilution:** Executive claims of *"rapid AI adoption and expanding operating leverage"* while underlying Cost of Goods Sold (COGS) inflates by 1,800+ basis points due to model API & GPU hosting expenses.
2. **Capital Allocation Divergence (Capex Sinkhole):** Aggressive infrastructure Capex commitments (+220% YoY) that outpace real operating cash flow, pushing Free Cash Flow deeply negative.
3. **Revenue Quality & Reclassification:** Reporting headline *"AI ARR milestones"* where segment footnotes reveal that 80%+ reflects existing legacy database renewals retroactively reclassified into an AI SKU with zero organic expansion.
4. **Baseline Control:** Verifying that a disciplined, healthy company (*Vortex Analytics*) triggers zero false positives.

`narrative-audit-jev` is an open-source **research harness** that runs over **DuckDB** tables, pairs
short synthetic disclosure text with structured line items, and implements Text2SQL, claim extraction,
and numeric guardrails. **Calibrated JEV evaluators, generative LLM baselines, and ECE/Brier reporting
described in the architecture diagram are design targets; they are not fully implemented in this tree.**

---

## Architecture

```
                                ┌─────────────────────────────────────────┐
                                │    Synthetic Benchmark Corpus (4 cos.)  │
                                │   • Structured Financials (8 Quarters)  │
                                │   • Earnings Call Transcripts (Q&A)     │
                                └────────────────────┬────────────────────┘
                                                     │
                                                     ▼
                                ┌─────────────────────────────────────────┐
                                │        DuckDB Analytical Engine         │
                                │    Normalized Financial Schema (SQL)    │
                                └────────────────────┬────────────────────┘
                                                     │
                      ┌──────────────────────────────┴──────────────────────────────┐
                      │                                                             │
                      ▼                                                             ▼
        ┌───────────────────────────┐                                 ┌───────────────────────────┐
        │   Text2SQL Analyst Agent  │                                 │ Qualitative Claim Agent   │
        │ • AST Read-Only Guardrail │                                 │ • Extracts disclosures    │
        │ • Margin & Capex metrics  │                                 │ • Identifies analyst Q&A  │
        │ • Parameterized execution │                                 │   hesitancy & deflections │
        └─────────────┬─────────────┘                                 └─────────────┬─────────────┘
                      │                                                             │
                      └──────────────────────────────┬──────────────────────────────┘
                                                     │
                                                     ▼
                                      ┌─────────────────────────────┐
                                      │ Claim-to-Metric Coordinator │
                                      │   State Graph Orchestrator  │
                                      └──────────────┬──────────────┘
                                                     │
                      ┌──────────────────────────────┴──────────────────────────────┐
                      │                                                             │
                      ▼                                                             ▼
        ┌───────────────────────────┐                                 ┌───────────────────────────┐
        │  Method A: Token-Based    │                                 │     Method B: JEV-Style   │
        │      Generative LLM       │                                 │    Calibrated Decision    │
        │ • Qualitative synthesis   │                                 │ • Evaluates typed schema  │
        │ • Explanatory commentary  │                                 │ • Calibrated P(Divergence)│
        │ • Uncalibrated verbal text│                                 │ • Softmax over categories │
        └─────────────┬─────────────┘                                 └─────────────┬─────────────┘
                      │                                                             │
                      └──────────────────────────────┬──────────────────────────────┘
                                                     │
                                                     ▼
                                      ┌─────────────────────────────┐
                                      │ Deterministic Numeric Critic│
                                      │  • Reconciles every cited   │
                                      │    number against SQL rows  │
                                      └──────────────┬──────────────┘
                                                     │
                                                     ▼
                                      ┌─────────────────────────────┐
                                      │   Executive Audit Dossier   │
                                      │ • Narrative Divergence Index│
                                      │ • Calibrated Risk Profile   │
                                      │ • ECE & Brier Score Report  │
                                      └─────────────────────────────┘
```

---

## Dual Methodology: Generative LLMs vs. Calibrated JEV

| Dimension | Method A: Generative LLM | Method B: JEV Calibrated Decision |
| :--- | :--- | :--- |
| **Output Type** | Autoregressive markdown paragraphs | Typed schema (`bool`, `Choice`, `Ordinal`) |
| **Probability Output** | Uncalibrated verbal hedging ("likely", "possibly") | Exact calibrated probability: $P(\text{Divergence}) \in [0.0, 1.0]$ |
| **Confidence Scoring** | Post-hoc prompted 1–10 scale | Calibrated softmax backed by empirical logits |
| **Latency Profile** | 500–2,000 output tokens ($O(T)$ decode steps) | Single forward-pass restricted logit evaluation ($5\times - 10\times$ faster) |
| **Enterprise Readiness** | Requires regex or secondary LLM to parse | Native JSON / Pydantic object ready for downstream risk pipelines |

---

## Synthetic Benchmark Corpus

Four **original fictional scenarios** (32 quarter-rows total, eight per company). Regenerate with `make generate-data`.

1. **AuraCloud Systems (`AURA`):** Margin compression vs. optimistic operating-leverage narrative.
2. **NexusEnterprise Corp (`NXUS`):** Heavy capex and negative free cash flow vs. return-on-capital rhetoric.
3. **Synthetix Data Systems (`SYNX`):** Headline “AI ARR” vs. segment footnotes on non-organic reclassification.
4. **Vortex Analytics (`VORS`, control):** Stable growth and margins; baseline scenario for tests (not a measured false-positive rate on real filings).

---

## Security & validation (implemented)

* **AST read-only SQL:** Text2SQL output is parsed with `sqlglot` to block mutating statements and risky DuckDB functions.
* **Prompt-injection fixtures:** Tests include injection strings in transcript text; agents are expected to stay bounded by SQL facts.
* **Numeric reconciler:** The numeric guardrail compares extracted claims against DuckDB rows for the synthetic benchmark.
* **Publication hygiene:** `tests/test_privacy_leakage.py` scans fixtures and repository text for accidental third-party identifiers.

---

## Quickstart

### 1. Installation
```bash
git clone https://github.com/adityavsb/narrative-audit-jev.git
cd narrative-audit-jev

# Create virtual environment and install dependencies
make install
```

### 2. Run Test Suite
```bash
# Run unit & schema integrity tests
make test
```

### 3. Validate Benchmark Datasets
```bash
# Verify DuckDB schema, accounting identities, and 52 golden test cases
make data-check
```

---

## Project Documentation
* [Detailed Project Roadmap & Architecture Plan](plan.md)
* [Architecture Decision Records (ADRs)](docs/decisions.md)

---

## License
MIT License.
