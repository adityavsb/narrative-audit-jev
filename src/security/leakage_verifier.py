"""Publication hygiene scanner for the synthetic benchmark corpus.

Ensures committed fixtures use only fictional tickers and that source/docs do not contain
accidental third-party identifiers (real issuers, CIKs, or branded analyst firms in dialogue).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

FICTIONAL_TICKERS: Set[str] = {"AURA", "NXUS", "SYNX", "VORS"}

FICTIONAL_COMPANY_NAMES: Set[str] = {
    "AuraCloud Systems Inc.",
    "NexusEnterprise Corp",
    "Synthetix Data Systems Inc.",
    "Vortex Analytics Inc.",
}

# Flat denylist for accidental re-introduction (no executive names or issuer-to-scenario maps).
FORBIDDEN_PUBLICATION_TERMS: List[str] = [
    "Snowflake Inc.",
    "C3.ai",
    "UiPath Inc.",
    "0001640147",
    "0001577526",
    "0001734722",
    "data.sec.gov/api/xbrl",
    "admin@university-research.edu",
    "Goldman Sachs",
    "Morgan Stanley",
    "JPMorgan",
    "Bernstein",
]

SCAN_SUFFIXES = {".py", ".md", ".json", ".toml", ".txt", ".yml", ".yaml"}
SKIP_DIR_NAMES = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "htmlcov", "dist", "build"}


class LeakageVerifier:
    """Scans repository text for publication hygiene violations."""

    def __init__(self, forbidden_terms: Iterable[str] = FORBIDDEN_PUBLICATION_TERMS):
        self.forbidden_terms = list(forbidden_terms)

    def scan_text_for_forbidden_terms(self, text: str) -> List[str]:
        leaks: List[str] = []
        for term in self.forbidden_terms:
            pattern = r"\b" + re.escape(term) + r"\b"
            if re.search(pattern, text, flags=re.IGNORECASE):
                leaks.append(term)
        return list(set(leaks))

    def audit_benchmark_directory(self, benchmark_dir: Path) -> Dict[str, Any]:
        """Verify benchmark JSON uses only fictional tickers."""
        results: Dict[str, Any] = {
            "total_files_scanned": 0,
            "invalid_tickers": {},
            "forbidden_term_leaks": {},
            "audit_passed": True,
        }

        for path in benchmark_dir.rglob("*.json"):
            results["total_files_scanned"] += 1
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            forbidden = self.scan_text_for_forbidden_terms(content)
            if forbidden:
                results["forbidden_term_leaks"][str(path)] = forbidden
                results["audit_passed"] = False

            try:
                payload = json.loads(content)
            except json.JSONDecodeError:
                continue

            bad_tickers: Set[str] = set()
            if isinstance(payload, dict) and "ticker" in payload:
                items = [payload]
            elif isinstance(payload, list):
                items = payload
            else:
                items = []

            for row in items:
                if isinstance(row, dict) and "ticker" in row:
                    t = row["ticker"]
                    if t not in FICTIONAL_TICKERS:
                        bad_tickers.add(str(t))

            if bad_tickers:
                results["invalid_tickers"][str(path)] = sorted(bad_tickers)
                results["audit_passed"] = False

        return results

    def audit_publication_tree(self, repo_root: Path) -> Dict[str, Any]:
        """Scan source, docs, and data for forbidden publication terms."""
        results: Dict[str, Any] = {
            "total_files_scanned": 0,
            "forbidden_term_leaks": {},
            "audit_passed": True,
        }

        self_path = Path(__file__).resolve()

        for path in repo_root.rglob("*"):
            if not path.is_file():
                continue
            if path.resolve() == self_path:
                continue
            if any(part in SKIP_DIR_NAMES for part in path.parts):
                continue
            if path.suffix.lower() not in SCAN_SUFFIXES:
                continue

            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            forbidden = self.scan_text_for_forbidden_terms(content)
            if forbidden:
                results["forbidden_term_leaks"][str(path)] = forbidden
                results["audit_passed"] = False
            results["total_files_scanned"] += 1

        return results


def run_leakage_audit() -> None:
    repo_root = Path(__file__).resolve().parent.parent.parent
    bench_dir = repo_root / "data" / "benchmark"
    verifier = LeakageVerifier()

    print("=" * 80)
    print("PUBLICATION HYGIENE SCAN (SYNTHETIC BENCHMARK)")
    print("=" * 80)

    bench_report = verifier.audit_benchmark_directory(bench_dir)
    tree_report = verifier.audit_publication_tree(repo_root)

    passed = bench_report["audit_passed"] and tree_report["audit_passed"]
    print(f"[*] Benchmark JSON files scanned: {bench_report['total_files_scanned']}")
    print(f"[*] Repository text files scanned:  {tree_report['total_files_scanned']}")
    print(f"    Audit Status:                   {'PASSED' if passed else 'FAILED'}")
    print("=" * 80)

    if not passed:
        print("\n[!] DETAILS:")
        for label, report in [("benchmark", bench_report), ("repository", tree_report)]:
            for file, leaks in report.get("forbidden_term_leaks", {}).items():
                print(f"    [{label}] {file} -> {leaks}")
            for file, tickers in report.get("invalid_tickers", {}).items():
                print(f"    [benchmark] {file} -> invalid tickers: {tickers}")


if __name__ == "__main__":
    run_leakage_audit()
