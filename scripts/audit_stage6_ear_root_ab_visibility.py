"""Run reviewed Blender-only source ear-root 41-Mesh BVH audit."""

import sys
from importlib import import_module
from pathlib import Path

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
_impl = import_module("plush_pattern_lab.blender.audit_stage6_ear_root_ab_visibility")


def __getattr__(name):
    """Expose audited Blender entry points without duplicating code."""
    return getattr(_impl, name)


if __name__ == "__main__":
    _impl.main()
