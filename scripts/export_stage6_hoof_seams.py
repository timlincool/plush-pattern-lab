"""从已验 SHA 的 Stage 6 Blender 场景提取四蹄接缝研究参考。"""

import sys
from importlib import import_module
from pathlib import Path

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
_impl = import_module("plush_pattern_lab.blender.export_stage6_hoof_seams")


def __getattr__(name):
    """与现有 Blender CLI 一致，保持实现与入口分离。"""
    return getattr(_impl, name)


if __name__ == "__main__":
    _impl.main()
