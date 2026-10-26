"""Compatibility entrypoint for probe_grey_cloud_split; implementation is in the package."""

from importlib import import_module
from pathlib import Path
import sys

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
_impl = import_module("plush_pattern_lab.blender.probe_grey_cloud_split")


def __getattr__(name):
    """Preserve existing script imports during the package migration."""
    return getattr(_impl, name)


if __name__ == "__main__":
    _impl.main()
