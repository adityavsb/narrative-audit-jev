"""Tests for packaging local eval_runs into tracked result bundles."""

import json
import subprocess
from pathlib import Path

import pytest

from scripts.package_openrouter_results import package_results


def test_package_results_writes_checksums(tmp_path):
    repo = Path(__file__).resolve().parent.parent
    source = repo / "data" / "eval_runs"
    if not (source / "openrouter_comparison_summary.json").is_file():
        pytest.skip("local eval_runs not present")

    bundle = package_results(source, tmp_path / "openrouter")
    assert (bundle / "summary.json").is_file()
    assert (bundle / "manifest.json").is_file()
    assert (bundle / "SHA256SUMS").is_file()
    manifest = json.loads((bundle / "manifest.json").read_text())
    assert manifest["no_api_rerun"] is True
    assert manifest["contains_fail_open_fallbacks"] is False
    summary = json.loads((bundle / "summary.json").read_text())
    for block in summary["results"]:
        if block["model"] == "deepseek/deepseek-v4.1-flash":
            assert block["telemetry"]["median_tokens_per_case"] > 0

    check = subprocess.run(
        ["sha256sum", "-c", "SHA256SUMS"],
        cwd=bundle,
        capture_output=True,
        text=True,
    )
    assert check.returncode == 0, check.stderr
