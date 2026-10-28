# Working notes

Dated, first-person record of decisions and corrections. Newest first. These are notes, not user documentation; see [README.md](README.md) for how to run the project.

## 2026-10 — Authorship remediation

### Decisions

- **2026-10 — MLflow deferred, not shipped.** I had listed MLflow in dependencies early on; for this repo it was overkill with no runner or eval pipeline wired up. I removed it from `pyproject.toml` and moved experiment tracking to [TODO.md](TODO.md) until there is a real harness to log.

- **2026-10 — In-memory DuckDB for load and test.** I load the synthetic benchmark into `:memory:` via `get_default_db()` so CI stays fast and a fresh clone gets the same tables without a persistent warehouse. That matches the research purpose here; a file-backed or hosted DuckDB is something to revisit only if this moves toward production ingestion.

- **2026-10 — AST read-only SQL (`sqlglot`) before DuckDB.** Every generated query is parsed and restricted to read-only shapes before execution, to block the injection fixtures we ship (multi-statement payloads, comment tricks, and similar patterns that are becoming common in LLM-facing tools). This is a first cut at that class of issue—not a complete security audit—documented in ADR-01 and [tests/test_sql_guardrail.py](tests/test_sql_guardrail.py).

- **2026-10 — Rule-based `ClaimExtractor`, not LLM-by-default.** For this corpus I need deterministic claim types so pytest and `make data-check` can assert the same outcome every run; an LLM extractor would add cost and flake. I kept an optional LLM hook on Text2SQL for later, but the default path is keywords/rules—build what is needed for reliable behavior instead of putting an LLM on every step.

### Things I got wrong

- **2026-10 — README implied a full multi-agent + JEV pipeline.** Agent-assisted drafting made it look like orchestrator, calibrated JEV evaluators, and dossier reporting were already in the tree; they were not. I caught that on review, rewrote [README.md](README.md) to match what ships, and moved the rest to [TODO.md](TODO.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

- **2026-10 — Big-bang first build instead of a tight scope.** I let the initial drop read like a finished product (diagrams, roadmap file, one large commit), which invited more hallucinated surface area. I should have iterated: schema + fixtures → guardrails → agents → eval only when the previous layer was tested. The authorship branch is the correction pattern I want to keep.

- **2026-10 — `make data-check` did not actually validate.** The Makefile passed `--validate` but [src/db/schema.py](src/db/schema.py) ignored it and only printed counts, while the README said it verified the 52 golden test cases. That was misleading until `0d3ffaf`; now `--validate` checks identities, golden schema, and keyed numbers in `verified_numbers`.

- **2026-10 — Text2SQL schema context did not match DuckDB.** `SCHEMA_CONTEXT` listed columns and section labels that are not in the real schema (e.g. balance-sheet fields we never load), so even a correct guardrail could still produce broken SQL. That is fixed in code, but I need to keep the documented schema aligned with the problem we are actually solving—not a generic “full filing” fantasy schema.

### Dead ends

- **2026-10 — MLflow, Docker, SEC EDGAR connector (never built).** These appeared in the old `plan.md` and dependency list as if they were part of v1; there is no `sec_edgar.py`, no Dockerfile, and MLflow was removed once I checked imports. They stay on [TODO.md](TODO.md) only if I add a real eval or ingestion story later.

- **2026-10 — No live filing retrieval (clarification for myself).** I never pulled 10-K/10-Q or transcripts from SEC EDGAR for this repo. All numbers and dialogue are fictional JSON under `data/benchmark/`, authored in [src/db/generate_benchmark_data.py](src/db/generate_benchmark_data.py) (regenerate with `make generate-data`). DuckDB only **loads** those files in memory via [src/db/schema.py](src/db/schema.py). [src/connectors/README.md](src/connectors/README.md) states that explicitly; `.env.example` still has a placeholder `SEC_EDGAR_USER_AGENT` for a future opt-in connector, not something that ran.

- **2026-10 — Optimism-only margin guardrail path.** Before remediation, gross-margin checks ran only for EXPANSION / “high” / “stable” wording, so Aura’s analyst CONTRACTION line missed `gross_margin` reconciliation. Killed when Bugbot/review showed audited GM still computed but the claim fell through to generic fallback; see [notebooks/01_margin_guardrail_polarity.ipynb](notebooks/01_margin_guardrail_polarity.ipynb) and [baseline_dee729f/](baseline_dee729f/).

### Open questions

<!-- HUMAN: at least two — e.g. worth building JEV evaluator on this corpus? live EDGAR connector scope? golden cases vs end-to-end agent eval? -->
