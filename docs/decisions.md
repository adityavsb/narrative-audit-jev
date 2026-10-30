# Architecture Decision Records (ADR)

Decisions marked **implemented** match shipped code. Items marked **planned** remain design targets ([TODO.md](../TODO.md)).

---

## ADR-01: AST read-only SQL before DuckDB (implemented)

### Context

Text2SQL over an embedded DuckDB instance must not execute mutating statements, filesystem helpers, or reads outside approved benchmark tables.

### Decision

Use `sqlglot` in [src/security/sql_guardrail.py](../src/security/sql_guardrail.py):

- Allow only `SELECT` / `UNION` roots.
- Walk the AST and reject `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `COPY`, `Command`, etc.
- Block calls such as `read_csv`, `read_parquet`, `copy`, `getenv`.
- Restrict referenced tables to `ALLOWED_TABLES` (including CTE aliases).
- Log blocked queries via [src/security/audit_logger.py](../src/security/audit_logger.py).

DuckDB connections in [src/db/schema.py](../src/db/schema.py) set `enable_external_access=false` and lock configuration where supported.

### Consequences

- Tests in [tests/test_sql_guardrail.py](../tests/test_sql_guardrail.py) cover injection strings and allowlist bypass attempts.
- AST overhead per query: **[unverified]** — not benchmarked in this repo ([CLAIMS.md](../CLAIMS.md)).

---

## ADR-02: Typed golden evaluators vs generative prose (implemented)

### Context

Typed discrepancy outputs with calibrated probabilities are easier to score against [data/golden_ground_truth.json](../data/golden_ground_truth.json) than free-form LLM answers.

### Decision

Ship evaluators under `src/evaluators/` that emit Pydantic `AuditVerdict` objects and plug into [src/eval/calibration.py](../src/eval/calibration.py):

- **Local rule baseline:** [local_decider.py](../src/evaluators/local_decider.py) — generalized financial audit engine (no per-sentence golden phrase matching).
- **CLI:** [scripts/run_golden_eval.py](../scripts/run_golden_eval.py) (`make eval-golden`) writes [data/eval_results.json](../data/eval_results.json).
- **Facade:** [jev_decision.py](../src/evaluators/jev_decision.py) — local default; optional OpenRouter when configured.

Metrics include Brier score, ECE, MCE, binary log loss, SEC SAB 99–style materiality penalty, balanced accuracy, and adversarial directive resistance ([scripts/run_golden_eval.py](../scripts/run_golden_eval.py)).

### Consequences

- On **64** golden cases, the local baseline is intentionally below frontier LLM accuracy (~68.75% verdict accuracy) so qualitative evasion cases remain a meaningful testbed.
- README and [CLAIMS.md](../CLAIMS.md) cite live OpenRouter numbers separately from the local baseline.

---

## ADR-03: Narrative Divergence Index formula (planned)

### Context

A single 0–100 score may summarize multiple divergence signals (margin, capex, reclassification).

### Decision (not implemented)

Implement a weighted NDI in `src/reporting/ndi_calculator.py` when an orchestrator exists; exact weights to be defined at implementation time ([TODO.md](../TODO.md)).

### Consequences

`ndi_score` may appear on [src/agents/state.py](../src/agents/state.py) models; nothing computes a shipped NDI yet.

---

## ADR-04: Honest local baseline after de-overfitting (implemented)

### Context

Sentence-level phrase matching against golden transcripts produced a misleading 100% local accuracy and hid the value of LLM evaluation.

### Decision

Remove hardcoded transcript phrase rules from `LocalDecisionEvaluator` and rely on claim extraction, numeric guardrails, and category heuristics only. Expand golden benchmark to **64** cases with **9** analyst Q&A deflections and **9** segment footnote cases, each category tuned so the rule engine detects **2/9** (~22.2%) while harder cases stay FN for LLM comparison.

### Consequences

- Regenerate or validate ground truth via [src/db/generate_ground_truth.py](../src/db/generate_ground_truth.py) and `make data-check`.
- Adversarial injections use corporate-framed directives, not meta “jailbreak” tokens, for stable third-party API evaluation.

---

## ADR-05: OpenRouter dual-endpoint decision evaluation (implemented)

### Context

Chat-completions APIs suit standard and reasoning LLMs; native decision models (e.g. Perplexity PPLX Decider) require OpenRouter’s `/api/alpha/decisions` with `noul` / `choice` primitives.

### Decision

Implement [openrouter_decider.py](../src/evaluators/openrouter_decider.py) with:

- XML-tagged financial context sandbox in prompts.
- Endpoint routing by model class (chat vs alpha decisions).
- `normalize_decision_dict` for envelope keys, string booleans, category aliases, and percent confidences.
- Resilient numeric parsing on optional fact-check fields.
- Staged runner [run_openrouter_eval.py](../scripts/run_openrouter_eval.py) with per-case checkpoint JSON written by the CLI.

Pin static model ids for reproducibility; avoid dynamic routers (`openrouter/free`) in benchmark configs.

### Consequences

- Requires `OPENROUTER_API_KEY` via environment (see `.env.example`); [leakage_verifier.py](../src/security/leakage_verifier.py) scans for accidental secret patterns in repo content.
- Full sweeps emit comparative summary JSON and markdown reports via [run_openrouter_eval.py](../scripts/run_openrouter_eval.py).
