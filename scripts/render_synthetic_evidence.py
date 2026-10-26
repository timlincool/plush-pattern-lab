"""Blender compatibility CLI for rendering the saved synthetic cloth model."""

import sys
from importlib import import_module
from pathlib import Path

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


if __name__ == "__main__":
    import_module("plush_pattern_lab.blender.render_synthetic_evidence").main()
