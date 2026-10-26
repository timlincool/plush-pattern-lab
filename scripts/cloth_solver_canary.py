"""Run the Blender Cloth canary; only execute inside the Blender process."""

import runpy
import sys
from pathlib import Path

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

if __name__ == "__main__":
    runpy.run_module(
        "plush_pattern_lab.blender.cloth_solver_canary", run_name="__main__"
    )
