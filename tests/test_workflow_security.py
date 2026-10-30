"""Fail-closed static policy for GitHub Actions executing trusted project code.

Regression checks only: repository Actions settings, branch protection and human
review are separate mandatory controls.
"""

import re
from pathlib import Path

import pytest
import yaml

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE / ".github" / "workflows"
EXPECTED = {
    "ci.yml",
    "sewing-poc.yml",
    "capped-sewing.yml",
    "selfcollision-ab.yml",
    "stage6-hoof-seam-reference.yml",
}
ALLOWED_IF = {
    "ci.yml": "github.event_name == 'workflow_dispatch' || (github.event_name == 'push' && github.ref == 'refs/heads/main')",
    "sewing-poc.yml": "github.ref == 'refs/heads/main' && (github.event_name == 'push' || github.event_name == 'workflow_dispatch')",
    "capped-sewing.yml": "github.ref == 'refs/heads/main' && (github.event_name == 'push' || github.event_name == 'workflow_dispatch')",
    "selfcollision-ab.yml": "github.ref == 'refs/heads/main' && (github.event_name == 'push' || github.event_name == 'workflow_dispatch')",
    "stage6-hoof-seam-reference.yml": "github.ref == 'refs/heads/main' && (github.event_name == 'push' || github.event_name == 'workflow_dispatch')",
}
ALLOWED_JOBS = {
    "ci.yml": {"python-tests"},
    "sewing-poc.yml": {"blender-sewing"},
    "capped-sewing.yml": {"sewn-caps"},
    "selfcollision-ab.yml": {"collision-study"},
    "stage6-hoof-seam-reference.yml": {"stage6-hoof-reference"},
}
BLENDER_SHA256 = "4da1c956673c0485e63054e563ee69198cc8f80d8157dd7592dffc8a6a5592e6"
STAGE6_SHA256 = "38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a"
STAGE6_PUBLIC_URL = (
    "https://github.com/timlincool/plush-pattern-lab/releases/download/"
    "cloud-alpaca-stage6-visuals-20261028/cloud-alpaca-stage6.blend"
)
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
        assert isinstance(push, dict) and push.get("branches") == ["main"], (
            filename,
            "branch",
        )
        if filename != "ci.yml":
            assert "src/plush_pattern_lab/**" in push.get("paths", []), (
                filename,
                "src trigger",
            )
        assert cfg["permissions"] == {"contents": "read"}, (filename, "token")
        assert not any(
            key in content
            for key in (
                "github.event.pull_request",
                "github.event.issue",
                "github.event.comment",
                "secrets.",
                "permissions: write-all",
            )
        ), filename
        if filename != "ci.yml":
            # The official Blender 4.3.2 binary must be checked before tar extraction.
            assert BLENDER_SHA256 in content, (filename, "Blender SHA256")
            assert "sha256sum -c -" in content, (filename, "Blender hash check")
        if filename == "stage6-hoof-seam-reference.yml":
            assert STAGE6_PUBLIC_URL in content, (filename, "public input")
            assert f'echo "{STAGE6_SHA256}  $RUNNER_TEMP/stage6.blend"' in content, (
                filename,
                "pinned Stage6 sha256",
            )
            assert "--disable-autoexec" in content, (filename, "autoexec disabled")
            assert "cloud-alpaca-plush" not in content, (filename, "private source")
        jobs = cfg.get("jobs")
        assert isinstance(jobs, dict) and set(jobs) == ALLOWED_JOBS[filename], (
            filename,
            "jobs",
        )
        for job_name, job in jobs.items():
            assert isinstance(job, dict), (filename, job_name)
            assert job.get("runs-on") == "ubuntu-24.04", (filename, job_name, "runner")
            assert job.get("if") == ALLOWED_IF[filename], (
                filename,
                job_name,
                "main-only",
            )
            assert "environment" not in job and "container" not in job, (
                filename,
                job_name,
            )
            assert job.get("permissions", {"contents": "read"}) == {
                "contents": "read"
            }, filename
            steps = job.get("steps")
            assert isinstance(steps, list) and steps, filename
            checkouts = 0
            for step in steps:
                assert isinstance(step, dict), (filename, "malformed step")
                if filename == "stage6-hoof-seam-reference.yml":
                    script = step.get("run", "")
                    if isinstance(script, str):
                        for command in script.splitlines():
                            if command.strip().startswith('"$BLENDER" '):
                                assert "--disable-autoexec" in command, (
                                    filename,
                                    "every Blender script must disable autoexec",
                                )
                if "uses" not in step:
                    continue
                action = step["uses"]
                assert isinstance(action, str) and PIN.fullmatch(action), (
                    filename,
                    action,
                )
                if action.startswith("actions/checkout@"):
                    checkouts += 1
                    settings = step.get("with", {})
                    assert settings.get("persist-credentials") == "false", filename
                    assert "ref" not in settings and "repository" not in settings, (
                        filename
                    )
            assert checkouts == 1, (filename, job_name, "checkout identity")


def workflows_on_disk():
    return {
        p.name: p.read_text(encoding="utf8")
        for p in ROOT.iterdir()
        if p.suffix in {".yml", ".yaml"}
    }


def test_workflows_fail_closed():
    check_workflows(workflows_on_disk())


def test_codeowner_review_scope():
    owners = (BASE / ".github" / "CODEOWNERS").read_text(encoding="utf8")
    for path in (
        "/.github/workflows/",
        "/requirements-dev.txt",
        "/scripts/",
        "/tests/",
        "/.github/CODEOWNERS",
    ):
        assert path in owners
    assert "@timlincool" in owners
    # GitHub resolves the *last* matching CODEOWNERS pattern.
    # Refuse both missing global ownership and delegated ownership overrides.
    rules = [
        line.split("#", 1)[0].split()
        for line in owners.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert ["*", "@timlincool"] in rules
    assert all(fields[1:] == ["@timlincool"] for fields in rules)


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


def test_reject_malicious_or_true_job_condition():
    guard = ALLOWED_IF["ci.yml"]
    _reject("ci.yml", "if: " + guard, "if: " + guard + " || true")


def test_reject_unpinned_action():
    old = re.search(r"actions/checkout@[0-9a-f]{40}", workflows_on_disk()["ci.yml"])
    assert old
    _reject("ci.yml", old.group(), "actions/checkout@v4")


def test_reject_checkout_credentials():
    _reject("ci.yml", "persist-credentials: false", "persist-credentials: true")


def test_reject_missing_blender_hash_check():
    _reject("sewing-poc.yml", BLENDER_SHA256, "0" * 64)


def test_reject_new_yaml_workflow():
    files = workflows_on_disk()
    files["evil.yaml"] = "on: [pull_request]\njobs: {}\n"
    with pytest.raises(AssertionError):
        check_workflows(files)


def test_reject_unpinned_public_stage6_asset():
    target = "stage6-hoof-seam-reference.yml"
    original = f'echo "{STAGE6_SHA256}  $RUNNER_TEMP/stage6.blend"'
    tampered = f'echo "{"0" * 64}  $RUNNER_TEMP/stage6.blend"'
    _reject(target, original, tampered)


def test_reject_stage6_autoexec():
    _reject(
        "stage6-hoof-seam-reference.yml",
        "--disable-autoexec --python-exit-code",
        "--python-exit-code",
    )
