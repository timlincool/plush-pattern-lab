"""R4 negative seam and original crown topology tests (no Blender)."""

from __future__ import annotations

import numpy as np
import pytest

from research.stage6_b24_r4.audit_r4_staging import audit
from research.stage6_b24_r4.build_r4_source_crown import (
    _new_crown_topology,
    _read_pinned,
)


def test_r4_old_crown_cap_becomes64_quads_and64_triangles():
    outer = np.arange(64)
    cap = [((i, (i + 1) % 64, 64), 1) for i in range(64)]
    result = _new_crown_topology(cap, outer, 64, 200)
    assert len(result) == 128
    assert sum(len(face) == 4 for face, _ in result) == 64
    assert sum(len(face) == 3 for face, _ in result) == 64


def test_r4_rejects_missing_cap_fan():
    with pytest.raises(ValueError, match="original 64-face cap"):
        _new_crown_topology([], np.arange(64), 64, 200)


def test_r4_rejects_untrusted_stage_before_importing_external_mesh(tmp_path):
    fake = tmp_path / "fake_r3.npz"
    fake.write_bytes(b"not approved R3 data")
    with pytest.raises(ValueError, match="signed-off"):
        _read_pinned(fake, fake)


def test_r4_rejects_unpaired_nonexistent_research_input(tmp_path):
    with pytest.raises(FileNotFoundError):
        audit(tmp_path / "no_input.npz")
