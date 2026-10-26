"""Adversarial tests for the architectural dependency contract."""

from pathlib import Path

from check_quality import architecture_errors, imports, package_files


def _write(root: Path, name: str, content: str) -> None:
    path = root / "src" / "plush_pattern_lab" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_real_package_has_no_dependency_cycles():
    assert architecture_errors(Path(__file__).resolve().parents[1]) == []


def test_required_import_package():
    paths = package_files(Path(__file__).resolve().parents[1])
    assert "plush_pattern_lab.patterns.capped_gore_pattern" in paths
    assert "plush_pattern_lab.blender.sewing_poc_blender" in paths


def test_architecture_rejects_cycle(tmp_path):
    _write(tmp_path, "__init__.py", "")
    _write(tmp_path, "patterns/__init__.py", "")
    _write(tmp_path, "patterns/a.py", "from plush_pattern_lab.patterns.b import b\n")
    _write(tmp_path, "patterns/b.py", "from plush_pattern_lab.patterns.a import a\n")
    assert any("circular" in issue for issue in architecture_errors(tmp_path))


def test_architecture_rejects_blender_dependency(tmp_path):
    _write(tmp_path, "__init__.py", "")
    _write(tmp_path, "patterns/__init__.py", "")
    _write(
        tmp_path, "patterns/a.py", "from plush_pattern_lab.blender import renderer\n"
    )
    assert any("depends on Blender" in issue for issue in architecture_errors(tmp_path))


def test_architecture_rejects_cli_dependency(tmp_path):
    _write(tmp_path, "__init__.py", "")
    _write(tmp_path, "validation/__init__.py", "")
    _write(tmp_path, "validation/a.py", "import scripts.sewing_quality\n")
    assert any(
        "must not import scripts" in issue for issue in architecture_errors(tmp_path)
    )


def test_relative_import_resolution(tmp_path):
    path = tmp_path / "a.py"
    path.write_text("from ..patterns import capped_gore_pattern\n")
    assert "plush_pattern_lab.patterns.capped_gore_pattern" in imports(
        "plush_pattern_lab.validation.a", path
    )
