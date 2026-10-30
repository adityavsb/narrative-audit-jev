# Not done (explicit backlog)

Shipped today: local golden eval (`make eval-golden`), staged OpenRouter harness (`make eval-openrouter`), evidence packaging (`make package-openrouter-results`), tracked bundle under `data/results/openrouter/`, dual-endpoint [openrouter_decider.py](src/evaluators/openrouter_decider.py). See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [README.md](README.md).

| Item | Acceptance hint |
|---|---|
| GitHub Actions CI | `make test`, `make data-check`, `make grep-gate`, optional `make secret-scan-history` on PR |
| Refresh `CLAIMS.md` commit SHAs | OpenRouter bundle row + pytest count point at post-push SHAs, not `740e670` / `unreviewed` |
| Generative LLM baseline without OpenRouter (`src/evaluators/token_llm.py`) | Same 64-case harness, vendor-agnostic optional path |
| Claim-to-metric orchestrator / state graph | End-to-end run: ticker+quarter → verdict dossier |
| NDI calculator + dossier generator | `ndi_score` from [src/agents/state.py](src/agents/state.py) computed in reporting code (ADR-03 still planned) |
| Dockerfile + docker-compose | Reproducible CI image matching lockfile |
| Live SEC EDGAR connector (`src/connectors/sec_edgar.py`) | Opt-in CLI, rate limits, tests with mocks |
| Audit logger process isolation | Tests use injected `AuditLogger` instances (see [src/security/audit_logger.py](src/security/audit_logger.py)) |
| OpenTelemetry / MLflow tracing | Spans on evaluators and guardrails; MLflow removed from deps until a runner exists |
| Temperature sweep + calibration post-processing | Documented in README “Possible next steps”; not scripted |

**Done (removed from backlog):** MLflow dependency (dropped from `pyproject.toml`); multi-model OpenRouter runner + comparison summary; publication hygiene (gitleaks, `CLAIMS.md` schema, synthetic disclaimers).
