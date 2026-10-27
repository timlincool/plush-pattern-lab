"""Read-only AST/NPZ scrutiny of already SHA-verified legacy ZIPs.

No patch execution, pickle loading, np.load(), Blender invocation or extraction.
Flags are bounded *review obligations*, not proof of malicious code.
"""

from __future__ import annotations

import ast
import io
import zipfile
from pathlib import PurePosixPath

import numpy as np
from numpy.lib import format as numpy_format

MAX_ARRAYS = 300
MAX_ARRAY_BYTES = 512 * 1024 * 1024
MAX_NPZ_BYTES = 1024 * 1024 * 1024
MAX_FINDINGS = 200


def _called_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _called_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _call_risk(called: str) -> str:
    if called in {"exec", "eval"}:
        return "DYNAMIC_EXECUTION"
    if called in {"os.system", "subprocess.run", "subprocess.Popen", "subprocess.call"}:
        return "PROCESS_INVOCATION"
    if called in {"pickle.load", "pickle.loads", "marshal.load", "marshal.loads"}:
        return "UNSAFE_DESERIALIZATION_REVIEW"
    if called in {"requests.get", "requests.post", "urllib.request.urlopen"}:
        return "NETWORK_ACCESS_REVIEW"
    return ""


def _pickle_enabled(item: ast.Call, called: str) -> bool:
    return called.endswith(".load") and any(
        kw.arg == "allow_pickle"
        and isinstance(kw.value, ast.Constant)
        and kw.value.value is True
        for kw in item.keywords
    )


def inspect_python(name: str, content: bytes) -> list[dict]:
    """Locate dynamic execution and sensitive runtime operations by AST."""
    try:
        root = ast.parse(content.decode("utf-8-sig"), filename=name)
    except (SyntaxError, UnicodeDecodeError):
        return [{"file": name, "line": 0, "risk": "PYTHON_UNPARSEABLE"}]
    risks = []
    for item in ast.walk(root):
        if not isinstance(item, ast.Call):
            continue
        called = _called_name(item.func)
        kind = _call_risk(called)
        if kind:
            risks.append({"file": name, "line": item.lineno, "risk": kind})
        if _pickle_enabled(item, called):
            risks.append(
                {"file": name, "line": item.lineno, "risk": "PICKLE_ENABLED_LOAD"}
            )
        if len(risks) > MAX_FINDINGS:
            raise ValueError("Python static risk finding budget exceeded")
    return risks


def _npy_header(stream) -> tuple[tuple, np.dtype, int]:
    version = numpy_format.read_magic(stream)
    if version == (1, 0):
        shape, _, dtype = numpy_format.read_array_header_1_0(
            stream, max_header_size=10000
        )
    elif version in {(2, 0), (3, 0)}:
        shape, _, dtype = numpy_format.read_array_header_2_0(
            stream, max_header_size=10000
        )
    else:
        raise ValueError("Unsupported NumPy binary array header")
    return shape, np.dtype(dtype), stream.tell()


def _array_risk(
    name: str, info: zipfile.ZipInfo, source: zipfile.ZipFile
) -> str | None:
    if not name.endswith(".npy") or info.is_dir():
        return "UNEXPECTED_NPZ_MEMBER"
    if info.file_size > MAX_ARRAY_BYTES or info.flag_bits & 1:
        return "OVERSIZED_OR_ENCRYPTED_ARRAY"
    try:
        with source.open(info, "r") as stream:
            shape, dtype, header_bytes = _npy_header(stream)
    except (ValueError, TypeError, OSError, EOFError, zipfile.BadZipFile):
        return "MALFORMED_ARRAY_HEADER"
    if dtype.hasobject:
        return "OBJECT_ARRAY_UNSAFE_FOR_PICKLE"
    count = 1
    for dimension in shape:
        if type(dimension) is not int or dimension < 0:
            return "INVALID_ARRAY_SHAPE"
        count *= dimension
        if count * dtype.itemsize > MAX_ARRAY_BYTES:
            return "OVERSIZED_ARRAY_SHAPE"
    if count * dtype.itemsize + header_bytes != info.file_size:
        return "ARRAY_PAYLOAD_SIZE_MISMATCH"
    return None


def inspect_npz(name: str, data: bytes) -> dict:
    """Inspect .npy headers inside .npz, never deserialize array payloads."""
    result = {"file": name, "array_count": 0, "risks": []}
    if len(data) > MAX_NPZ_BYTES:
        result["risks"] = ["OVERSIZED_NPZ"]
        return result
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as package:
            files = package.infolist()
            if len(files) > MAX_ARRAYS:
                result["risks"].append("TOO_MANY_ARRAYS")
                return result
            for member in files:
                risk = _array_risk(member.filename, member, package)
                if risk:
                    result["risks"].append(risk)
                else:
                    result["array_count"] += 1
    except (OSError, RuntimeError, zipfile.BadZipFile, EOFError):
        result["risks"].append("CORRUPT_NPZ_ARCHIVE")
    result["risks"] = sorted(set(result["risks"]))
    return result


def inspect_archive(path) -> dict:
    """Produce bounded static risk report from a trusted downloaded ZIP."""
    rows = []
    npz_count = 0
    arrays = 0
    script_count = 0
    with zipfile.ZipFile(path) as source:
        for member in source.infolist():
            name = member.filename
            if not name or name.startswith("/") or ".." in PurePosixPath(name).parts:
                raise ValueError("Unexpected member path in source ZIP")
            if member.is_dir():
                continue
            if name.endswith(".py"):
                script_count += 1
                rows.extend(inspect_python(name, source.read(member)))
            if name.endswith(".npz"):
                npz_count += 1
                result = inspect_npz(name, source.read(member))
                arrays += result["array_count"]
                rows.extend(
                    {"file": name, "line": 0, "risk": code} for code in result["risks"]
                )
            if len(rows) > MAX_FINDINGS:
                raise ValueError("Risk report exceeds bounded diagnostic size")
    return {
        "status": "STATIC_REVIEW_REQUIRED_NOT_EXECUTION_AUTHORIZATION",
        "scripts_inspected": script_count,
        "npz_archives_inspected": npz_count,
        "numeric_arrays_checked": arrays,
        "risk_findings": rows,
    }
