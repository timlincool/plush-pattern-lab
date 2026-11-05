"""Blender 4.3.2 CLI: verified Stage6 protected core-shell proxy candidates."""

import sys
from importlib import import_module
from pathlib import Path

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
_impl = import_module("plush_pattern_lab.blender.build_stage6_core_proxy")


def __getattr__(name):
    """Keep all implementation in the Blender source package."""
    return getattr(_impl, name)


if __name__ == "__main__":
    _impl.main()
