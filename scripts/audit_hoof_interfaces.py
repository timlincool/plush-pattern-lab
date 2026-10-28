"""Blender 几何接口审计兼容命令，真实实现位于 Python 包。"""

import sys
from importlib import import_module
from pathlib import Path

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

_impl = import_module("plush_pattern_lab.blender.audit_hoof_interfaces")


def __getattr__(name):
    """保留脚本入口到包实现的向后兼容访问。"""
    return getattr(_impl, name)


if __name__ == "__main__":
    _impl.main()
