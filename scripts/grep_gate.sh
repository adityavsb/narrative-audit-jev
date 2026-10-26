#!/usr/bin/env bash
# Playbook §3.4 register check on public-facing markdown (not fixture JSON).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PATTERN='robust|rigorous|comprehensive|state-of-the-art|publication-grade|production-ready|undeniable|confirmed|discover|novel|seamless|leverage|cutting-edge|testament|delve|worth noting|realm of'

targets=(README.md CONTRIBUTING.md CLAIMS.md TODO.md docs/ARCHITECTURE.md docs/decisions.md)
hits="$(grep -niE "$PATTERN" "${targets[@]}" 2>/dev/null || true)"
if [[ -n "$hits" ]]; then
  echo "grep-gate FAIL:"
  echo "$hits"
  exit 1
fi
echo "grep-gate: OK (0 hits in public markdown)"
