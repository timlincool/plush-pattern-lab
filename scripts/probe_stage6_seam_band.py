"""Blender 4.3.2 CLI: survey the actual faces next to Stage 6 hoof seams."""

import sys
from importlib import import_module
from pathlib import Path

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
_impl = import_module("plush_pattern_lab.blender.probe_stage6_seam_band")


def __getattr__(name):
    """Preserve the scripts/ CLI convention for Blender tools."""
    return getattr(_impl, name)


if __name__ == "__main__":
    _impl.main()
