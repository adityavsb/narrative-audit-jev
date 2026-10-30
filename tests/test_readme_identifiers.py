"""README synthetic ticker disclaimer must match leakage verifier allowlist."""

import re
from pathlib import Path

from src.security.leakage_verifier import FICTIONAL_TICKERS


def _readme_ticker_disclaimer_set(readme_text: str) -> set[str]:
    match = re.search(
        r"Tickers `([A-Z]+)`, `([A-Z]+)`, `([A-Z]+)`, and `([A-Z]+)`",
        readme_text,
    )
    if not match:
        raise AssertionError("Could not parse four-ticker disclaimer from README.md")
    return {match.group(i) for i in range(1, 5)}


def test_readme_tickers_match_fictional_allowlist():
    repo_root = Path(__file__).resolve().parent.parent
    readme = (repo_root / "README.md").read_text()
    disclaimer_tickers = _readme_ticker_disclaimer_set(readme)
    assert disclaimer_tickers == FICTIONAL_TICKERS
