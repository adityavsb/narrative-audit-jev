# Contributing

## Before merge

1. `make test`
2. `make data-check`
3. `make grep-gate`
4. `make metrics` (append [metrics_log.csv](metrics_log.csv) when outputs change)
5. `make secret-scan-history` before release (requires [gitleaks](https://github.com/gitleaks/gitleaks))

OpenRouter raw checkpoints stay under `data/eval_runs/` (local-only). Public leaderboard evidence lives under `data/results/openrouter/` via `make package-openrouter-results`.

## Agent sessions

End with a local **HANDOFF.md** (gitignored): unverified items, `<!-- HUMAN: -->` placeholders, decisions to accept/reject, grep-gate output. Do not commit HANDOFF.

Author-maintained judgment lives in [NOTES.md](NOTES.md) (first person, dated).
