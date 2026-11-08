"""Run the reviewed Blender 4.3.2 full product-Mesh seam visibility audit."""

import sys
from importlib import import_module
from pathlib import Path

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
_impl = import_module("plush_pattern_lab.blender.audit_stage6_full_mesh_visibility")


def __getattr__(name):
    """Expose validated Blender-only audit functions without code duplication."""
    return getattr(_impl, name)


if __name__ == "__main__":
    _impl.main()
