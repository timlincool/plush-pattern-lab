"""FreeCAD compiled solver is optional; fake it to test source integrity contracts."""

from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from run_stage6_freecad_flatmesh import SOURCE_SHA, run_study, source_disks


def _source():
    xyz = [[float(i), float(i * i % 17), 0.0] for i in range(24)]
    faces = [
        [0, (i % 22) + 1, ((i + 1) % 22) + 1]
        for i in range(32)
    ]
    disks = []
    for variant in ("N15", "N17"):
        for side in ("left", "right"):
            for slit in ("medial", "posterior", "lateral"):
                disks.append(
                    {
                        "source_variant": f"{variant}_sloped_source_band",
                        "original_source_side": side,
                        "source_slit_direction": slit,
                        "original_source_patch_sha256": variant + side,
                        "cut_disk_source_xyz_mm": xyz,
                        "cut_disk_original_source_triangle_indices": faces,
                    }
                )
    return {
        "schema": "stage6-ear-root-genuine-source-disk-lscm-research-v1",
        "original_public_blend_sha256": SOURCE_SHA,
        "factory_cutting_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
        "candidate_2d_research_disks": disks,
    }


class _NativeFlatmesh:
    class FaceUnwrapper:
        def __init__(self, xyz, faces):
            assert xyz.shape == (24, 3)
            assert faces.shape == (32, 3)
            self.ze_nodes = None
            self._original = xyz

        def findFlatNodes(self, steps, value):
            assert steps == 10 and value == 0.95
            self.ze_nodes = self._original[:, :2]


def test_reusing_external_compiled_freecad_module_preserves_all_source_ids():
    study = run_study(_source(), _NativeFlatmesh, "fixed-source-sha")
    assert len(study["entries"]) == 12
    assert all(row["status"] == "completed" for row in study["entries"])
    assert all(row["source_vertex_count"] == 24 for row in study["entries"])
    assert study["method"] == "FREECAD_FLATMESH_LSCM_RELAX_10_0_95"
    assert study["external_compiled_freecad_not_vendored"]
    assert study["factory_cutting_patterns_approved"] == 0
    assert study["P3_status"] == "in_progress"
    assert study["P4_status"] == "not_started"


@pytest.mark.parametrize(
    "fault",
    ("fake_approval", "duplicate", "not_twelve", "source_sha", "missing_p3"),
)
def test_source_identity_or_factory_tamper_must_fail(fault):
    source = deepcopy(_source())
    if fault == "fake_approval":
        source["factory_cutting_patterns_approved"] = 1
    elif fault == "duplicate":
        source["candidate_2d_research_disks"][0] = source[
            "candidate_2d_research_disks"
        ][1]
    elif fault == "not_twelve":
        source["candidate_2d_research_disks"].pop()
    elif fault == "source_sha":
        source["original_public_blend_sha256"] = "different"
    else:
        source["P3_status"] = "accepted"
    with pytest.raises(ValueError):
        source_disks(source)


def test_nonfinite_or_mismatched_compiled_uv_is_rejected():
    class Broken:
        class FaceUnwrapper:
            def __init__(self, xyz, faces):
                self.ze_nodes = np.full((len(xyz), 3), float("nan"))

            def findFlatNodes(self, steps, value):
                pass

    result = run_study(_source(), Broken, "sha")
    assert len(result["entries"]) == 12
    assert all(x["status"] == "solver_failed" for x in result["entries"])
    assert result["factory_cutting_patterns_approved"] == 0


def test_no_native_library_is_not_faked():
    with pytest.raises(ValueError):
        run_study(_source(), object(), "sha")
