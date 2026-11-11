"""Read-only trusted Blender original section / 41-product-Mesh association."""

import sys
from importlib import import_module
from pathlib import Path

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
_impl = import_module(
    "plush_pattern_lab.blender.audit_stage6_section_mesh_correspondence"
)


def __getattr__(name):
    """Expose pinned Blender adapter without duplicating code."""
    return getattr(_impl, name)


if __name__ == "__main__":
    _impl.main()
