# narrative-audit-jev

Research prototype: compare **synthetic** earnings-call-style text to structured quarterly line items in DuckDB. Not a PCAOB/GAAS audit, not financial or legal advice. All companies and dialogue in `data/` are fictional; synthetic tickers `AURA` and `SYNX` have no connection to NASDAQ: AURA, NYSE American: SYNX, or Synthetix (SNX).

## How to run

```bash
make install
make test
make data-check    # schema, accounting identities, 52 golden cases
make generate-data # optional: regenerate fixtures
make metrics       # append metrics_log.csv row
make grep-gate     # language register check (see scripts/grep_gate.sh)
```

## What ships today

- DuckDB schema and JSON loaders ([src/db/schema.py](src/db/schema.py))
- Rule-based claim extraction from transcripts ([src/agents/claim_extractor.py](src/agents/claim_extractor.py))
- Numeric guardrail vs GAAP rows ([src/agents/numeric_guardrail.py](src/agents/numeric_guardrail.py))
- Text2SQL helper with AST read-only SQL guard ([src/agents/text2sql_agent.py](src/agents/text2sql_agent.py), [src/security/sql_guardrail.py](src/security/sql_guardrail.py))
- Semantic metric helpers and divergence flags ([src/db/semantic_metrics.py](src/db/semantic_metrics.py))
- Synthetic benchmark + 52-case golden metadata ([data/](data/), [data/golden_ground_truth.json](data/golden_ground_truth.json))
- Publication hygiene scan ([tests/test_privacy_leakage.py](tests/test_privacy_leakage.py))

## Benchmark scale

| Item | Count | Source |
|---|---:|---|
| Companies | 4 | [CLAIMS.md](CLAIMS.md); `make data-check` |
| Quarters (financial rows) | 32 | same |
| Transcript snippets | 12 | same |
| Golden labeled claims | 52 | [data/golden_ground_truth.json](data/golden_ground_truth.json) |

Scenario intent (synthetic): Aura margin compression vs optimistic narrative; Nexus capex vs negative FCF; Synthetix AI ARR vs reclassification footnotes; Vortex control with stable margins. Details in [data/DATA_CATALOG.md](data/DATA_CATALOG.md).

## Scope and limitations

**Not implemented:** JEV calibrated evaluator, generative LLM baseline, orchestrator graph, Narrative Divergence Index dossier, ECE/Brier eval harness, Docker image, live SEC EDGAR ingestion. See [TODO.md](TODO.md).

Golden JSON labels cases for future eval; the repo does **not** yet run all 52 through a single CLI pipeline.

Design notes and corrections: [NOTES.md](NOTES.md) (author-maintained). Verified numbers: [CLAIMS.md](CLAIMS.md). File-level map: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). ADRs: [docs/decisions.md](docs/decisions.md).

Pre-remediation baseline outputs: [baseline_dee729f/](baseline_dee729f/).

## Citation & References

See [REFERENCES.bib](REFERENCES.bib) for canonical literature (Loughran & McDonald 2011, SEC SAB 99, Brier 1950, Guo et al. 2017) and [CITATION.cff](CITATION.cff) for repository citation metadata.

## License

MIT — see [LICENSE](LICENSE).
