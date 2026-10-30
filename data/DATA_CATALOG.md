# Evaluation Corpus & Data Catalog

The `narrative-audit-jev` benchmark is a **small, fully synthetic** corpus for testing multi-agent
workflows that compare qualitative disclosure text against structured financial tables.

---

## Corpus Overview

| Metric | Scale in this repository |
| :--- | :--- |
| **Fictional companies** | **4** (AuraCloud, NexusEnterprise, Synthetix, Vortex Analytics) |
| **Quarters per company** | **8** (2024 Q1 – 2025 Q4) |
| **Transcript turns** | **3 per company** (12 total): short scripted CEO/CFO/analyst dialogue |
| **Golden evaluation cases** | **64** labeled claims in `data/golden_ground_truth.json` |

All company names, tickers, speaker names, and financial figures are **original fiction**. They do not
represent real issuers, real people, or real bank affiliations. Any accidental similarity to a real
ticker, company, or figure is coincidental; this corpus is not verified against exchange or trademark
registries and must not be relied on for any real-world decision.

**Ticker note:** Synthetic tickers `AURA`, `NXUS`, `SYNX`, and `VORS` are benchmark identifiers only; they are not intended to identify real issuers.

Regenerate fixtures locally:

```bash
make generate-data
```

---

## Scenario Archetypes

1. **AuraCloud (`AURA`)** — Margin compression vs. optimistic operating-leverage narrative.
2. **NexusEnterprise (`NXUS`)** — Heavy capex and negative free cash flow vs. return-on-capital rhetoric.
3. **Synthetix (`SYNX`)** — Headline “AI ARR” vs. segment footnotes on non-organic reclassification.
4. **Vortex Analytics (`VORS`, control)** — Stable growth and margins; baseline with no intentional divergence.

---

## Data Schemas

The DuckDB warehouse (`src/db/schema.py`) defines four tables: `companies`, `quarterly_financials`,
`segment_disclosures`, and `transcripts`. See schema comments for column definitions.

A minimal single-company reference lives in `data/sample_fixture/` for quick CI checks.

---

## Privacy & Licensing

- No commercial earnings transcripts, analyst models, or proprietary feeds are included.
- Do not infer real-world companies from these scenarios; they were written for benchmark variety only.
