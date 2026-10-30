"""History secret scan wiring (requires gitleaks on PATH for integration test)."""

import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(shutil.which("gitleaks") is None, reason="gitleaks not installed")
def test_gitleaks_detects_removed_secret_in_history(tmp_path):
    repo = tmp_path / "leak_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)

    secret_file = repo / "note.txt"
    secret_file.write_text("OPENROUTER_API_KEY=sk-or-v1-deadbeefdeadbeefdeadbeefdeadbeef\n")
    subprocess.run(["git", "add", "note.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "add secret"], cwd=repo, check=True)
    secret_file.write_text("clean\n")
    subprocess.run(["git", "add", "note.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "remove secret"], cwd=repo, check=True)

    config = Path(__file__).resolve().parent.parent / ".gitleaks.toml"
    proc = subprocess.run(
        [
            "gitleaks",
            "detect",
            "--source",
            str(repo),
            "--log-opts",
            "--all",
            "--config",
            str(config),
            "--redact",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
