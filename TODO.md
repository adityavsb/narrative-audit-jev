# Not done (explicit backlog)

Items from the earlier product sketch but **not implemented** in this repository (see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for what exists).

| Item | Acceptance hint |
|---|---|
| Generative LLM baseline (`src/evaluators/token_llm.py`) | Comparable outputs on same 52 cases |
| Claim-to-metric orchestrator / state graph | End-to-end run: ticker+quarter → verdict dossier |
| NDI calculator + dossier generator | `ndi_score` from [src/agents/state.py](src/agents/state.py) computed in code |
| MLflow benchmark runner | Optional; remove from deps until used |
| Dockerfile + docker-compose | Reproducible CI image matching lockfile |
| Live SEC EDGAR connector (`src/connectors/sec_edgar.py`) | Opt-in CLI, rate limits, tests with mocks |
| Audit logger process isolation | Tests use injected `AuditLogger` instances (see [src/security/audit_logger.py](src/security/audit_logger.py)) |
