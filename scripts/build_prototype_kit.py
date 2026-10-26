"""Thin compatibility entrypoint for the printable synthetic-toile kit."""

from importlib import import_module
from pathlib import Path
import sys

_SOURCE = str(Path(__file__).resolve().parents[1] / "src")
if _SOURCE not in sys.path:
    sys.path.insert(0, _SOURCE)


if __name__ == "__main__":
    import_module("plush_pattern_lab.patterns.fabrication_kit").main()
