"""Regression gates for maintainer-controlled GitHub Actions execution.

Static inspection of TRUSTED main source, not a way to prove PR binaries safe.
"""
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE / ".github" / "workflows"
DANGEROUS_EVENTS = ("pull_request", "pull_request_target", "workflow_run",
                    "issue_comment", "issues", "repository_dispatch")
EXPECTED = {"ci.yml", "sewing-poc.yml", "capped-sewing.yml", "selfcollision-ab.yml"}
SHA = re.compile(r"^\s*- uses:\s+actions/[a-z-]+@[0-9a-f]{40}\s*$", re.M)


def inspect_workflows():
    files = {p.name: p.read_text(encoding="utf8") for p in ROOT.glob("*.yml")}
    assert files.keys() == EXPECTED, "New workflows require explicit security review"
    for filename, text in files.items():
        assert re.search(r"^on:\s*$", text, re.M), filename
        for event in DANGEROUS_EVENTS:
            assert not re.search(rf"^\s*{event}\s*:", text, re.M), (filename, event)
        assert re.search(r"^  push:\s*$", text, re.M), filename
        assert re.search(r"^    branches:\s*\[main\]\s*$", text, re.M), filename
        assert re.search(r"^  workflow_dispatch:\s*$", text, re.M), filename
        assert re.search(r"^permissions:\s*\n  contents:\s*read\s*$", text, re.M), filename
        assert not re.search(r"(?m)^\s*(?:id-token|actions|checks|pull-requests):\s*write\s*$", text), filename
        assert re.search(r"(?m)^\s+if:\s+.*github.ref == 'refs/heads/main'", text), filename
        assert "persist-credentials: false" in text, filename
        uses = re.findall(r"(?m)^\s*- uses:\s*(.*)$", text)
        assert uses and len(SHA.findall(text)) == len(uses), (filename, uses)
    return files


def test_every_job_is_trusted_only():
    inspect_workflows()


def test_no_unsafe_pr_event_in_maintainer_workflows():
    data = inspect_workflows()
    assert all("  pull_request:" not in c for c in data.values())
    assert all("  pull_request_target:" not in c for c in data.values())
    assert all("  workflow_run:" not in c for c in data.values())


def test_security_owner_defined_for_sensitive_paths():
    owners = (BASE / ".github" / "CODEOWNERS").read_text(encoding="utf8")
    for item in ("/.github/workflows/", "/requirements-dev.txt",
                 "/scripts/", "/tests/"):
        assert item in owners
    assert "@timlincool" in owners
