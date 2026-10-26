"""Compatibility entrypoint for verify_cloth_physics_snapshot; implementation is in the package."""

from importlib import import_module
from pathlib import Path
import sys

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
_impl = import_module("plush_pattern_lab.blender.verify_cloth_physics_snapshot")


def __getattr__(name):
    """Preserve existing script imports during the package migration."""
    return getattr(_impl, name)


if __name__ == "__main__":
    _impl.main()
