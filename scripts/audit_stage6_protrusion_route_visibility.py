"""Run reviewed original Stage6 X/Y meridian 41-Mesh visibility in Blender."""

import sys
from importlib import import_module
from pathlib import Path

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
_impl = import_module("plush_pattern_lab.blender.audit_stage6_protrusion_route_visibility")


def __getattr__(name):
    return getattr(_impl, name)


if __name__ == "__main__":
    _impl.main()
