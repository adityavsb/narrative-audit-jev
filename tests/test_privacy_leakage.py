"""Validate publication hygiene for the synthetic benchmark corpus."""

from pathlib import Path

from src.security.leakage_verifier import LeakageVerifier


def test_benchmark_uses_fictional_tickers_only():
    bench_dir = Path(__file__).resolve().parent.parent / "data" / "benchmark"
    assert bench_dir.exists()

    verifier = LeakageVerifier()
    report = verifier.audit_benchmark_directory(bench_dir)

    assert report["audit_passed"] is True, f"Benchmark hygiene failed: {report}"
    assert len(report.get("invalid_tickers", {})) == 0
    assert len(report.get("forbidden_term_leaks", {})) == 0
    assert report["total_files_scanned"] >= 16


def test_repository_publication_hygiene():
    repo_root = Path(__file__).resolve().parent.parent
    verifier = LeakageVerifier()
    report = verifier.audit_publication_tree(repo_root)

    assert report["audit_passed"] is True, f"Repository hygiene failed: {report}"
    assert len(report.get("forbidden_term_leaks", {})) == 0
    assert len(report.get("secret_leaks", {})) == 0
    assert report["total_files_scanned"] >= 20
