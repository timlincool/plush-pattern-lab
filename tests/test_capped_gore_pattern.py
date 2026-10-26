"""Cap pattern study tests: correct stitch matching is necessary, not sufficient."""

import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pytest

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "capped_gore_pattern.py"
s = importlib.util.spec_from_file_location("cap", SOURCE)
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)


@pytest.mark.parametrize("count", [6, 8, 12, 16, 24])
def test_transverse_cap_and_gore_stitches_match_piecewise(count):
    p = m.make(panels=count)
    assert p["quality"]["number_of_distinct_net_pieces"] == count + 2
    assert len(p["sewing_pairs"]) == 3 * count
    assert p["quality"]["max_cross_stitch_length_mismatch_mm"] < 1e-8
    for cap in ("upper", "lower"):
        c = p["caps"][cap]
        ring = np.asarray(c["stitch_ring_2d_mm"])
        assert len(ring) == 2 * count
        lengths = np.linalg.norm(np.roll(ring, -1, axis=0) - ring, axis=1)
        assert np.ptp(lengths) < 1e-8
        assert c["stitch_perimeter_mm"] == pytest.approx(2 * count * lengths[0])
        for i in range(count):
            q = next(x for x in p["sewing_pairs"] if x["a"] == f"P{i:02d}.{cap}")
            assert q["b_vertex_indices"] == [
                (2 * i + j) % (2 * count) for j in range(3)
            ]
            assert q["stitch_length_mm"] == pytest.approx(q["cap_stitch_length_mm"])


def test_trimmed_poles_remove_singular_zero_radius_but_not_make_it_real():
    v = m.make()
    r = np.asarray(v["geometry"]["radial_mm"])
    th = np.asarray(v["geometry"]["theta_radians"])
    assert r.min() > 0
    assert th[0] == pytest.approx(math.radians(8))
    assert th[-1] == pytest.approx(math.pi - math.radians(8))
    assert v["quality"]["zero_area_poles_eliminated_by_truncation"]
    assert not v["quality"]["virtual_sewing_executed"]
    assert not v["quality"]["real_material_measured"]


def test_fabric_cut_area_and_model_grain():
    v = m.make(panels=12, allowance_mm=6)
    assert v["gore"]["cut_area_mm2"] > v["gore"]["net_area_mm2"]
    assert v["caps"]["upper"]["cut_area_mm2"] > v["caps"]["upper"]["net_area_mm2"]
    assert v["caps"]["lower"]["cut_area_mm2"] > v["caps"]["lower"]["net_area_mm2"]
    assert v["gore"]["grain_direction"] == [0, 1]


def test_reject_invalid_poles_and_legacy_input():
    for kw in (
        {"pole_cut_deg": 0},
        {"pole_cut_deg": 90},
        {"panels": 4},
        {"allowance_mm": 30},
    ):
        with pytest.raises(ValueError):
            m.make(**kw)


def test_no_overwrite_cli(tmp_path):
    import subprocess
    import sys

    target = tmp_path / "cap_pattern.json"
    args = [sys.executable, str(SOURCE), "--out", str(target)]
    assert subprocess.run(args, capture_output=True).returncode == 0
    data = json.loads(target.read_text(encoding="utf8"))
    assert data["schema"] == "synthetic-capped-plush-pattern-v1"
    assert subprocess.run(args, capture_output=True).returncode != 0
