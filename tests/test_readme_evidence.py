"""README evidence paths must refer to tracked bundles when claiming measured results."""

import re
from pathlib import Path


def test_readme_openrouter_evidence_is_tracked():
    repo = Path(__file__).resolve().parent.parent
    readme = (repo / "README.md").read_text()
    match = re.search(r"data/results/openrouter/([A-Za-z0-9_-]+)/summary\.json", readme)
    assert match, "README must link to a versioned OpenRouter summary.json"
    run_id = match.group(1)
    bundle = repo / "data" / "results" / "openrouter" / run_id
    assert (bundle / "summary.json").is_file()
    assert (bundle / "SHA256SUMS").is_file()
