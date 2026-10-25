"""Fail-closed static policy for GitHub Actions executing trusted project code.

Regression checks only: repository Actions settings, branch protection and human
review are separate mandatory controls.
"""
from pathlib import Path
import re

import pytest
import yaml

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE / ".github" / "workflows"
EXPECTED = {"ci.yml", "sewing-poc.yml", "capped-sewing.yml", "selfcollision-ab.yml"}
MAIN_REF = "github.ref == 'refs/heads/main'"
PIN = re.compile(r"^actions/[A-Za-z0-9_.-]+@[0-9a-f]{40}$")


def check_workflows(files: dict[str, str]) -> None:
    # Both extensions count; new workflow files must be reviewed explicitly.
    assert set(files) == EXPECTED, "Added/renamed workflow requires security review"
    for filename, content in files.items():
        cfg = yaml.load(content, Loader=yaml.BaseLoader)
        assert isinstance(cfg, dict), filename
        assert isinstance(cfg.get("on"), dict), (filename, "trigger type")
        assert set(cfg["on"]) == {"push", "workflow_dispatch"}, (filename, "events")
        push = cfg["on"]["push"]
        assert isinstance(push, dict) and push.get("branches") == ["main"], (filename, "branch")
        assert cfg["permissions"] == {"contents": "read"}, (filename, "token")
        assert not any(key in content for key in (
            "github.event.pull_request", "github.event.issue",
            "github.event.comment", "secrets.", "permissions: write-all")), filename
        jobs = cfg.get("jobs")
        assert isinstance(jobs, dict) and jobs, (filename, "jobs")
        for job_name, job in jobs.items():
            assert isinstance(job, dict), (filename, job_name)
            assert job.get("runs-on") == "ubuntu-24.04", (filename, job_name, "runner")
            assert MAIN_REF in str(job.get("if", "")), (filename, job_name, "main-only")
            assert "environment" not in job and "container" not in job, (filename, job_name)
            assert job.get("permissions", {"contents": "read"}) == {"contents": "read"}, filename
            steps = job.get("steps")
            assert isinstance(steps, list) and steps, filename
            checkouts = 0
            for step in steps:
                assert isinstance(step, dict), (filename, "malformed step")
                if "uses" not in step:
                    continue
                action = step["uses"]
                assert isinstance(action, str) and PIN.fullmatch(action), (filename, action)
                if action.startswith("actions/checkout@"):
                    checkouts += 1
                    settings = step.get("with", {})
                    assert settings.get("persist-credentials") == "false", filename
                    assert "ref" not in settings and "repository" not in settings, filename
            assert checkouts == 1, (filename, job_name, "checkout identity")


def workflows_on_disk():
    return {p.name: p.read_text(encoding="utf8")
            for p in ROOT.iterdir() if p.suffix in {".yml", ".yaml"}}


def test_workflows_fail_closed():
    check_workflows(workflows_on_disk())


def test_codeowner_review_scope():
    owners = (BASE / ".github" / "CODEOWNERS").read_text(encoding="utf8")
    for path in ("/.github/workflows/", "/requirements-dev.txt",
                 "/scripts/", "/tests/", "/.github/CODEOWNERS"):
        assert path in owners
    assert "@timlincool" in owners


def _reject(filename, old, new):
    files = workflows_on_disk()
    assert old in files[filename], ("fixture drifted", filename, old)
    files[filename] = files[filename].replace(old, new, 1)
    with pytest.raises((AssertionError, yaml.YAMLError)):
        check_workflows(files)


def test_reject_pr_trigger_shorthand():
    _reject("ci.yml", "on:\n", "on: [push, pull_request]\n")


def test_reject_untrusted_branch():
    _reject("ci.yml", "branches: [main]", "branches: [main, contributor-pr]")


def test_reject_write_token():
    _reject("ci.yml", "contents: read", "contents: write")


def test_reject_self_hosted_runner():
    _reject("ci.yml", "runs-on: ubuntu-24.04", "runs-on: self-hosted")


def test_reject_unpinned_action():
    old = re.search(r"actions/checkout@[0-9a-f]{40}", workflows_on_disk()["ci.yml"])
    assert old
    _reject("ci.yml", old.group(), "actions/checkout@v4")


def test_reject_checkout_credentials():
    _reject("ci.yml", "persist-credentials: false", "persist-credentials: true")


def test_reject_new_yaml_workflow():
    files = workflows_on_disk()
    files["evil.yaml"] = "on: [pull_request]\njobs: {}\n"
    with pytest.raises(AssertionError):
        check_workflows(files)
