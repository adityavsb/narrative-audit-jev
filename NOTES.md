# Working notes

Dated, first-person record of decisions and corrections. Newest first. These are notes, not user documentation; see [README.md](README.md) for how to run the project.

## 2026-10-30 — OpenRouter sweep, evidence bundle, and push

### Decisions

- **2026-10-30 — Public leaderboard needs git-tracked evidence, not local `eval_runs/`.** I ran the 64×4 sweep locally and wrote checkpoints under `data/eval_runs/` (git-excluded). README numbers only become defensible after `make package-openrouter-results` copies a redacted bundle to `data/results/openrouter/<run-id>/` with `manifest.json` and `SHA256SUMS`. I imported the 2026-10-29 sweep without rerunning APIs.

- **2026-10-30 — Fail closed on OpenRouter retry exhaustion.** An earlier path returned `SUPPORTED` / `NONE` at 0.50 confidence when the API failed after retries—that could inflate metrics during outages. The evaluator now raises; the batch runner excludes failed cases unless `--allow-partial`.

- **2026-10-30 — Token columns instead of dollar cost in the README table.** Model pricing moves; prompt+completion tokens per case (mean and median over 64 cases) are what I can reproduce from checkpoints. Local baseline stays at 0 tokens.

- **2026-10-30 — Synthetic wording in external prompts.** OpenRouter payloads say “synthetic reference ledger,” not “audited financial ledger,” so the harness does not read like an assurance product. Pydantic `audited_value` on fact checks is unchanged (reconciliation field name, not a GAAS claim).

- **2026-10-30 — Tickers in docs match fixtures (`AURA`, `NXUS`, `SYNX`, `VORS`).** README had drifted to `NEXS`/`VRTX`; I aligned prose with [src/security/leakage_verifier.py](src/security/leakage_verifier.py) and added coincidental-resemblance / no-liability language under Scope & Limitations.

- **2026-10-30 — History scan before release.** `make secret-scan-history` (gitleaks + custom `sk-or-v1` rule) complements the fast [LeakageVerifier](src/security/leakage_verifier.py) tree scan. Commits use `adityavsb@users.noreply.github.com`; I stripped old `Co-authored-by: Cursor` trailers from history before the first push.

### Things I got wrong

- **2026-10-30 — Treating README live-model rows as reproducible without committed artifacts.** The comparison table pointed at `data/eval_runs/` paths that never shipped in git. That was the main gap in the pillars 4–5 review—not whether the local run happened.

- **2026-10-29 — Assuming one OpenRouter client shape.** PPLX Decider needs `/api/alpha/decisions`; chat models use `/chat/completions`. I wired both in [openrouter_decider.py](src/evaluators/openrouter_decider.py) after HTTP 400s on the wrong endpoint.

- **2026-10-29 — Free-router smoke tests looked like benchmark results.** `openrouter/free` sometimes routed to safety classifiers returning plain text, not JSON verdicts. Pinned model IDs and temperature 0 are non-negotiable for scored runs.

### Dead ends

- **2026-10-29 — Nemotron free-tier checkpoint in the same folder as paid sweeps.** `checkpoint_nvidia_nemotron-3.5-lightning_free.json` stays local exploration only; the published bundle excludes it.

### Open questions

- **2026-10-30 — Re-run vs. import-only for the next model revision.** When upstream slugs change, I can either spend API credits on a fresh 64-case sweep or package new local checkpoints—import does not replace pinning commit SHA in [CLAIMS.md](CLAIMS.md).

- **2026-10-30 — CI on GitHub.** Tests and `make secret-scan-history` are documented in [CONTRIBUTING.md](CONTRIBUTING.md) but not wired to Actions yet.

---

## 2026-10 — Authorship remediation

### Decisions

- **2026-10 — MLflow deferred, not shipped.** I had listed MLflow in dependencies early on; for this repo it was overkill with no runner or eval pipeline wired up. I removed it from `pyproject.toml` and moved experiment tracking to [TODO.md](TODO.md) until there is a real harness to log.

- **2026-10 — In-memory DuckDB for load and test.** I load the synthetic benchmark into `:memory:` via `get_default_db()` so CI stays fast and a fresh clone gets the same tables without a persistent warehouse. That matches the research purpose here; a file-backed or hosted DuckDB is something to revisit only if this moves toward production ingestion.

- **2026-10 — AST read-only SQL (`sqlglot`) before DuckDB.** Every generated query is parsed and restricted to read-only shapes before execution, to block the injection fixtures we ship (multi-statement payloads, comment tricks, and similar patterns that are becoming common in LLM-facing tools). This is a first cut at that class of issue—not a complete security audit—documented in ADR-01 and [tests/test_sql_guardrail.py](tests/test_sql_guardrail.py).

- **2026-10 — Rule-based `ClaimExtractor`, not LLM-by-default.** For this corpus I need deterministic claim types so pytest and `make data-check` can assert the same outcome every run; an LLM extractor would add cost and flake. I kept an optional LLM hook on Text2SQL for later, but the default path is keywords/rules—build what is needed for reliable behavior instead of putting an LLM on every step.

### Things I got wrong

- **2026-10 — README implied a full multi-agent + JEV pipeline.** Agent-assisted drafting made it look like orchestrator, calibrated JEV evaluators, and dossier reporting were already in the tree; they were not. I caught that on review, rewrote [README.md](README.md) to match what ships, and moved the rest to [TODO.md](TODO.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

- **2026-10 — Big-bang first build instead of a tight scope.** I let the initial drop read like a finished product (diagrams, roadmap file, one large commit), which invited more hallucinated surface area. I should have iterated: schema + fixtures → guardrails → agents → eval only when the previous layer was tested. The authorship branch is the correction pattern I want to keep.

- **2026-10 — `make data-check` did not actually validate.** The Makefile passed `--validate` but [src/db/schema.py](src/db/schema.py) ignored it and only printed counts, while the README said it verified golden cases. That was misleading until schema validation landed; now `--validate` checks identities, golden schema, and keyed numbers in `verified_numbers` (**64** cases today).

- **2026-10 — Text2SQL schema context did not match DuckDB.** `SCHEMA_CONTEXT` listed columns and section labels that are not in the real schema (e.g. balance-sheet fields we never load), so even a correct guardrail could still produce broken SQL. That is fixed in code, but I need to keep the documented schema aligned with the problem we are actually solving—not a generic “full filing” fantasy schema.

### Dead ends

- **2026-10 — MLflow, Docker, SEC EDGAR connector (never built).** These appeared in the old `plan.md` and dependency list as if they were part of v1; there is no `sec_edgar.py`, no Dockerfile, and MLflow was removed once I checked imports. They stay on [TODO.md](TODO.md) only if I add a real eval or ingestion story later.

- **2026-10 — No live filing retrieval (clarification for myself).** I never pulled 10-K/10-Q or transcripts from SEC EDGAR for this repo. All numbers and dialogue are fictional JSON under `data/benchmark/`, authored in [src/db/generate_benchmark_data.py](src/db/generate_benchmark_data.py) (regenerate with `make generate-data`). DuckDB only **loads** those files in memory via [src/db/schema.py](src/db/schema.py). [src/connectors/README.md](src/connectors/README.md) states that explicitly; `.env.example` still has a placeholder `SEC_EDGAR_USER_AGENT` for a future opt-in connector, not something that ran.

- **2026-10 — Optimism-only margin guardrail path.** Before remediation, gross-margin checks ran only for EXPANSION / “high” / “stable” wording, so Aura’s analyst CONTRACTION line missed `gross_margin` reconciliation. Killed when review showed audited GM still computed but the claim fell through to generic fallback; see [notebooks/01_margin_guardrail_polarity.ipynb](notebooks/01_margin_guardrail_polarity.ipynb) and [baseline_dee729f/](baseline_dee729f/).

### Open questions (updated 2026-10-30)

- **Synthetic vs. live SEC EDGAR.** Still deferred; the **64-case** synthetic suite is what I use for OpenRouter and local baselines (`make eval-golden`, `make eval-openrouter`).

- **Rules vs. LLMs on qualitative evasion.** The local rule baseline is ~**68.75%** verdict accuracy but ~**22%** on analyst Q&A deflection and footnote reclass cases (by design after de-overfitting). Pinned OpenRouter models score much higher on those categories in the tracked bundle—see README and `data/results/openrouter/2026-10-29T134211Z/summary.json`. Headline accuracy alone hid calibration differences (ECE / log loss).
