"""Security regression tests for non-executing recovery-source and NPZ inspection."""

from __future__ import annotations

import io
import zipfile

import numpy as np

from plush_pattern_lab.validation.archive_static import (
    inspect_archive,
    inspect_npz,
    inspect_python,
)


def _npz(values) -> bytes:
    blob = io.BytesIO()
    np.savez(blob, part=values)
    return blob.getvalue()


def test_ast_detects_patch_execution_without_executing_it(tmp_path):
    code = b"raise RuntimeError('MUST NOT RUN')\nexec('print(1)')\n"
    result = inspect_python("rebuild.py", code)
    assert result == [{"file": "rebuild.py", "line": 2, "risk": "DYNAMIC_EXECUTION"}]


def test_ast_detects_sensitive_process_without_source_leak():
    code = b"import subprocess\nsubprocess.run(['false'])\nimport os\nos.system('true')\n"
    findings = inspect_python("rebuild.py", code)
    assert [row["risk"] for row in findings] == [
        "PROCESS_INVOCATION",
        "PROCESS_INVOCATION",
    ]
    assert all("command" not in row for row in findings)


def test_invalid_python_source_is_reported_not_executed():
    assert inspect_python("broken.py", b"def nope(:\n")[0]["risk"] == "PYTHON_UNPARSEABLE"


def test_numeric_npz_inspects_headers_without_array_deserialization():
    data = _npz(np.arange(8, dtype=np.float32))
    result = inspect_npz("numeric.npz", data)
    assert result["risks"] == []
    assert result["array_count"] == 1


def test_object_array_is_flagged_for_pickle_risk():
    data = _npz(np.array([{"unsafe": "object-data"}], dtype=object))
    result = inspect_npz("object.npz", data)
    assert result["array_count"] == 0
    assert result["risks"] == ["OBJECT_ARRAY_UNSAFE_FOR_PICKLE"]


def test_malformed_npz_is_rejected():
    assert inspect_npz("bad.npz", b"fake ZIP")["risks"] == [
        "CORRUPT_NPZ_ARCHIVE"
    ]


def test_unexpected_members_in_npz_do_not_get_deserialized():
    blob = io.BytesIO()
    with zipfile.ZipFile(blob, "w") as package:
        package.writestr("nested-code.py", "raise RuntimeError('MUST NOT RUN')")
    assert inspect_npz("untrusted.npz", blob.getvalue())["risks"] == [
        "UNEXPECTED_NPZ_MEMBER"
    ]


def test_realistic_source_zip_can_be_scanned_without_running_patch(tmp_path):
    source = tmp_path / "stage.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("patches/rebuild.py", "exec('malicious command')\n")
        archive.writestr("payload.npz", _npz(np.arange(4, dtype=np.int32)))
    result = inspect_archive(source)
    assert result["scripts_inspected"] == 1
    assert result["npz_archives_inspected"] == 1
    assert result["numeric_arrays_checked"] == 1
    assert [row["risk"] for row in result["risk_findings"]] == [
        "DYNAMIC_EXECUTION"
    ]


def test_source_zip_invalid_path_cannot_be_interpreted(tmp_path):
    source = tmp_path / "path.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("../escape.py", "pass\n")
    try:
        inspect_archive(source)
    except ValueError as exc:
        assert "member path" in str(exc)
    else:
        raise AssertionError("Unsafe path should be refused")
