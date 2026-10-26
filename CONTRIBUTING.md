# Contributing

## Before merge

1. `make test`
2. `make data-check`
3. `make grep-gate`
4. `make metrics` (append [metrics_log.csv](metrics_log.csv) when outputs change)

## Agent sessions

End with a local **HANDOFF.md** (gitignored): unverified items, `<!-- HUMAN: -->` placeholders, decisions to accept/reject, grep-gate output. Do not commit HANDOFF.

Author-maintained judgment lives in [NOTES.md](NOTES.md) (first person, dated).
