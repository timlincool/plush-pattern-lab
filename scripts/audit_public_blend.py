"""Compatibility entrypoint for audit_public_blend; implementation is in the package."""

import sys
from importlib import import_module
from pathlib import Path

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
_impl = import_module("plush_pattern_lab.blender.audit_public_blend")


def __getattr__(name):
    """Preserve existing script imports during the package migration."""
    return getattr(_impl, name)


if __name__ == "__main__":
    _impl.main()
