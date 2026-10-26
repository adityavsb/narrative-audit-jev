# Architecture Decision Records (ADR)

This document records the architectural and security decisions governing `narrative-audit-jev`.

---

## ADR-01: AST-Enforced Read-Only SQL Execution over Unconstrained Text2SQL

### Context
In forward-deployed enterprise finance and due diligence workflows, generative LLMs are tasked with formulating queries over internal analytical databases (e.g. DuckDB, Snowflake, BigQuery). Unconstrained Text2SQL engines pose severe security vulnerabilities:
1. **Accidental or Adversarial Mutations:** Malicious filings containing prompt injections (e.g., `"; DROP TABLE companies;--"`) or hallucinations could execute mutating statements (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`).
2. **Filesystem Exfiltration:** Embedded database engines like DuckDB provide built-in functions (`read_csv`, `read_parquet`, `copy`) that allow read/write access to host filesystems.
3. **Regex Fragility:** Simple string or regex blacklisting (`if "DROP" in sql`) is easily bypassed via comments (`DROP/**/TABLE`), whitespace trickery, or nested subqueries.

### Decision
We implement a compiler-grade AST (Abstract Syntax Tree) validator powered by `sqlglot` (`src/security/sql_guardrail.py`):
- Every LLM-generated SQL query is parsed into a syntax tree before reaching DuckDB.
- The root AST node is strictly restricted to `exp.Select` or `exp.Union`.
- The full AST tree is recursively traversed using `.walk()`, blocking all prohibited expression types (`exp.Insert`, `exp.Update`, `exp.Delete`, `exp.Drop`, `exp.Alter`, `exp.Copy`, `exp.Command`, `exp.Pragma`, `exp.Merge`).
- Calls to dangerous system or filesystem functions (`read_csv`, `read_parquet`, `read_json`, `copy`, `system`, `getenv`) are intercepted and rejected with `SecurityViolationError`.
- Multi-statement payloads (`SELECT 1; DROP TABLE t;`) are rejected at the parser level.
- All violation events are immutably logged to `AuditLogger` with full query strings, timestamps, and execution timings.

### Consequences
- **Positive:** Enforces read-only SQL for supported AST shapes and blocks common mutating/exfiltration primitives before DuckDB execution.
- **Trade-off:** Additional $\approx 1.2\text{ ms}$ AST validation overhead per query, which is negligible compared to model inference latency ($\approx 500-2000\text{ ms}$).

---

## ADR-02: Calibrated JEV Probabilistic Methodology vs. Open-Ended Generative LLMs

### Context
Traditional generative LLMs (e.g., GPT-4o, Claude 3.5 Sonnet) output autoregressive natural language text when auditing corporate disclosures. This approach exhibits several institutional deficiencies:
1. **Uncalibrated Confidence:** Generative LLMs exhibit hedging behavior or overconfident assertions without well-calibrated posterior probabilities. A statement phrased with "high confidence" frequently corresponds to $<70\%$ empirical precision.
2. **High Latency & Token Cost:** Generating 500-1,000 explanatory tokens takes 3-10 seconds per filing and incurs substantial inference cost.
3. **Non-Deterministic Schemas:** Parsing unstructured text output into structured downstream trading or audit workflows requires secondary extraction passes prone to schema drifts.

### Decision
We introduce the Calibrated JEV Decision Methodology alongside traditional token-by-token generative evaluation:
- Constrains decision outputs to strictly typed, discrete schemas (`bool` discrepancy flag, `Choice` categorical divergence type, `MaterialityTier`, and ordinal evidence scores).
- Yields calibrated probability distributions ($P \in [0.0, 1.0]$) directly over the hypothesis space.
- Enables empirical calibration benchmarking: Expected Calibration Error (ECE), Brier Score, and reliability curves.

### Consequences
- **Positive:** $5-10\times$ faster decision latency, zero token generation overhead, deterministic typing, and measurable statistical reliability.
- **Trade-off:** Evaluator focuses on classification and severity scoring; rich qualitative narration requires pairing with a downstream templated dossier generator.

---

## ADR-03: Formula Derivation for the Narrative Divergence Index (NDI)

### Context
Enterprise risk teams require a single standardized composite score ($0 - 100$) summarizing the aggregate discrepancy between executive rhetoric and accounting reality.

### Decision
The Narrative Divergence Index ($\text{NDI}$) is formulated as a bounded multi-factor metric:
$$\text{NDI} = \min\left(100, \, 100 \times \left( w_1 \cdot \mathcal{D}_{\text{margin}} + w_2 \cdot \mathcal{D}_{\text{capex}} + w_3 \cdot \mathcal{D}_{\text{rev\_reclass}} + w_4 \cdot \mathcal{D}_{\text{sentiment\_gap}} \right)\right)$$

Where:
- $\mathcal{D}_{\text{margin}} = \max\left(0, \frac{\Delta\text{GM}_{\text{YoY}}}{-0.20}\right)$ (penalizes gross margin dilution)
- $\mathcal{D}_{\text{capex}} = \mathbb{I}(\text{FCF} < 0) \times \min\left(1.0, \frac{\text{Capex}}{\text{Revenue}}\right)$ (penalizes uncapitalized cash burn)
- $\mathcal{D}_{\text{rev\_reclass}} = \frac{\text{Non-Organic Disclosed ARR}}{\text{Total Disclosed ARR}}$ (penalizes reclassified revenue)
- $\mathcal{D}_{\text{sentiment\_gap}} = \max\left(0, \text{Sentiment}_{\text{qual}} - \text{Direction}_{\text{GAAP}}\right)$ (penalizes executive hype during fundamental deterioration)
- Default weights: $w_1 = 0.35, \, w_2 = 0.30, \, w_3 = 0.25, \, w_4 = 0.10$.

Scores are bucketed into institutional risk tiers:
- **0 - 24:** Minimal Divergence (Consistent with Control Group / Verified)
- **25 - 49:** Moderate Scrutiny (Emerging margin compression or capex buildup)
- **50 - 74:** Material Divergence (Significant contradiction between narrative and financials)
- **75 - 100:** Critical Discrepancy (Severe divergence, e.g. large reclassification gap or $>1,500\text{ bps}$ margin collapse)
