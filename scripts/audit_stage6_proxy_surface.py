"""Trusted Blender 4.3.2 CLI: independent Stage6 proxy surface/shape checks."""

import sys
from importlib import import_module
from pathlib import Path

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
_impl = import_module("plush_pattern_lab.blender.audit_stage6_proxy_surface")


def __getattr__(name):
    """Keep the trusted CLI implementation in the Blender source package."""
    return getattr(_impl, name)


if __name__ == "__main__":
    _impl.main()
