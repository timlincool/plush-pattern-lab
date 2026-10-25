"""Adversarial checks for fail-closed repository size limits."""

from pathlib import Path

import pytest

from scripts.check_quality_limits import MAX_PYTHON_LINES, check_limits


def test_repository_stays_below_limit():
    assert not check_limits(Path(__file__).resolve().parents[1])


def test_exact_boundary_is_allowed(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "scripts" / "ok.py").write_text("pass\n" * 3)
    assert not check_limits(tmp_path, max_lines=3)


def test_oversized_file_is_rejected(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "bad.py").write_text("pass\n" * 4)
    assert "4 lines exceeds hard limit 3" in check_limits(tmp_path, 3)[0]


def test_missing_source_directory_is_rejected(tmp_path):
    (tmp_path / "scripts").mkdir()
    assert "missing required source directory: tests/" in check_limits(tmp_path)


def test_invalid_limit_rejected(tmp_path):
    with pytest.raises(ValueError):
        check_limits(tmp_path, 0)


def test_symlinked_python_source_rejected(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "tests").mkdir()
    target = tmp_path / "outside.txt"
    target.write_text("pass\n")
    link = tmp_path / "scripts" / "via_link.py"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink unavailable")
    assert "symlinked Python" in check_limits(tmp_path)[0]


def test_project_limit_never_grows_without_review():
    assert MAX_PYTHON_LINES == 2000
