# Architecture Decision Records (ADR)

Decisions that match **shipped code** are marked implemented. JEV/NDI items are design targets only ([TODO.md](../TODO.md)).

---

## ADR-01: AST read-only SQL before DuckDB (implemented)

### Context

Text2SQL over an embedded DuckDB instance must not execute mutating statements or filesystem helpers, including under adversarial transcript text in the benchmark.

### Decision

Use `sqlglot` in [src/security/sql_guardrail.py](../src/security/sql_guardrail.py):

- Allow only `SELECT` / `UNION` roots.
- Walk the AST and reject `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `COPY`, `Command`, etc.
- Block calls such as `read_csv`, `read_parquet`, `copy`, `getenv`.
- Log blocked queries via [src/security/audit_logger.py](../src/security/audit_logger.py).

### Consequences

- Tests in [tests/test_sql_guardrail.py](../tests/test_sql_guardrail.py) cover injection strings.
- AST overhead per query: **[unverified]** — not benchmarked in this repo (see [CLAIMS.md](../CLAIMS.md)).

---

## ADR-02: JEV-style typed decisions vs generative prose (planned)

### Context

Typed discrepancy outputs with calibrated probabilities are easier to evaluate against [data/golden_ground_truth.json](../data/golden_ground_truth.json) than free-form LLM answers.

### Decision (not implemented)

Add evaluators under `src/evaluators/` that emit Pydantic verdict objects (`is_discrepancy`, divergence category, materiality) and support ECE/Brier on the 52 golden cases.

### Consequences

- [src/agents/numeric_guardrail.py](../src/agents/numeric_guardrail.py) is the only deterministic reconciliation gate today.
- No latency or calibration numbers are claimed in README until this lands.

---

## ADR-03: Narrative Divergence Index formula (planned)

### Context

A single 0–100 score may summarize multiple divergence signals (margin, capex, reclassification).

### Decision (not implemented)

Use the weighted sum documented in the previous revision of this file; implement in `src/reporting/ndi_calculator.py` when the orchestrator exists.

### Consequences

`ndi_score` appears on [src/agents/state.py](../src/agents/state.py) models only; nothing computes it yet.
