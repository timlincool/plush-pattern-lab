"""Call reviewed Blender 4.3.2 Stage6 ear-dart Mesh audit, without code copy."""

import sys
from importlib import import_module
from pathlib import Path

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
_impl = import_module("plush_pattern_lab.blender.audit_stage6_ear_dart_paths_41mesh")


def __getattr__(name):
    """Expose Blender audit helpers without importing Bpy in ordinary Python CI."""
    return getattr(_impl, name)


if __name__ == "__main__":
    _impl.main()
