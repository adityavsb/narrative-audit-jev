#!/usr/bin/env bash
# Append one row to metrics_log.csv (repo root). Requires .venv and prior make install.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
VENV="${VENV:-.venv}"
PY="$VENV/bin/python"
commit="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
utc="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

pytest_out="$("$PY" -m pytest -q 2>&1 | tail -1)"
if [[ "$pytest_out" =~ ([0-9]+)\ passed ]]; then
  passed="${BASH_REMATCH[1]}"
else
  passed=0
fi
collect_line="$("$PY" -m pytest --collect-only -q 2>/dev/null | tail -1)"
if [[ "$collect_line" =~ ([0-9]+)\ tests\ collected ]]; then
  total="${BASH_REMATCH[1]}"
else
  total="$passed"
fi

if "$PY" -m src.db.schema --validate >/dev/null 2>&1; then
  dc_ok=true
else
  dc_ok=false
fi

stats="$("$PY" - <<'PY'
from src.db.schema import validate_benchmark
errors, stats = validate_benchmark()
if errors:
    raise SystemExit(1)
print(
    stats.get("golden_cases", 0),
    stats["companies_count"],
    stats["quarters_count"],
    stats["transcripts_count"],
)
PY
)"
read -r golden companies quarters transcripts <<< "$stats"

line="$utc,$commit,$passed,$total,$dc_ok,$golden,$companies,$quarters,$transcripts,make metrics"
if [[ ! -f metrics_log.csv ]]; then
  echo "run_utc,commit,pytest_passed,pytest_total,data_check_ok,golden_cases,companies_count,quarters_count,transcripts_count,notes" > metrics_log.csv
fi
echo "$line" >> metrics_log.csv
echo "Appended: $line"
