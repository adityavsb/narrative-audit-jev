"""Automated tests for canonical bibliography, citation metadata, and ticker disambiguation."""

from pathlib import Path


def test_references_bib_exists_and_has_canonical_keys():
    repo_root = Path(__file__).resolve().parent.parent
    bib_file = repo_root / "REFERENCES.bib"
    assert bib_file.exists(), "REFERENCES.bib must exist in repo root"

    content = bib_file.read_text()
    required_keys = [
        "LoughranMcDonald2011",
        "SECSAB99",
        "Brier1950",
        "Guo2017Calibration",
    ]
    for key in required_keys:
        assert key in content, f"Missing required BibTeX key '{key}' in REFERENCES.bib"

    # Verify canonical DOIs are included
    assert "10.1111/j.1540-6261.2010.01625.x" in content, "Missing Loughran-McDonald DOI"
    assert "10.1175/1520-0493(1950)078<0001:vofeit>2.0.co;2" in content, "Missing Brier DOI"


def test_citation_cff_exists_and_has_required_fields():
    repo_root = Path(__file__).resolve().parent.parent
    cff_file = repo_root / "CITATION.cff"
    assert cff_file.exists(), "CITATION.cff must exist in repo root"

    content = cff_file.read_text()
    required_fields = [
        "cff-version:",
        "message:",
        "authors:",
        "family-names:",
        "given-names:",
        "title:",
        "version:",
        "date-released:",
        "url:",
        "license: MIT",
    ]
    for field in required_fields:
        assert field in content, f"Missing required CFF field '{field}' in CITATION.cff"

    assert "Bhadoria" in content and "Aditya" in content


def test_ticker_disambiguation_present_in_docs():
    repo_root = Path(__file__).resolve().parent.parent
    catalog = (repo_root / "data" / "DATA_CATALOG.md").read_text()
    readme = (repo_root / "README.md").read_text()

    # Verify DATA_CATALOG.md disambiguation note
    assert "Ticker Disambiguation Note" in catalog
    assert "Aura Biosciences, Inc. (NASDAQ: AURA)" in catalog
    assert "Silynxcom Ltd. (NYSE American: SYNX)" in catalog

    # Verify README.md disclaimer and citation pointers
    assert "AURA" in readme and "SYNX" in readme
    assert "REFERENCES.bib" in readme
    assert "CITATION.cff" in readme
