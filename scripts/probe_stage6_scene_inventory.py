"""Blender 4.3.2 CLI: audit every object in the pinned public Stage6 scene."""

import sys
from importlib import import_module
from pathlib import Path

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
_impl = import_module("plush_pattern_lab.blender.probe_stage6_scene_inventory")


def __getattr__(name):
    """Preserve scripts/ CLI compatibility for the read-only audit."""
    return getattr(_impl, name)


if __name__ == "__main__":
    _impl.main()
