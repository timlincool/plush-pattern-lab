"""Verify a same-run R3 stage without pinning nondeterministic NPZ bytes.

The signed Stage6 source PLY remains byte-locked. A new R3 snapshot needs its
same-run R3 QA binding and the canonical, narrowly quantized geometry fingerprint.
The reference fingerprint was independently checked against genuine runs
44265926278 and 44267489157 with ≤2.4e-11 m coordinate differences.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

SOURCE_SHA = "5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd"
R3_TRUSTED_BLOBS = {
    "d93afe5667bc2c808e4700c5554a858b1df9b1574c9e23de1cb2c08b42c27fc3",
    "faf7dfa2129e7a1ce63d4829cb49b0ef85608fa0c39cd7271ef36a5c53a9a2e5",
}
R3_CANONICAL_FINGERPRINT = (
    "655354f11df17b858e9c9038d35f1defe1d69523182193a004a2f4b4f77892f5"
)
FLOAT_ARRAYS = (
    "initial_3d_prepositioned_vertices_m",
    "true_independent_flat_2d_rest_xy_m",
)
TOPOLOGY_ARRAYS = (
    "face_lengths",
    "face_vertex_ids",
    "face_material_roles",
    "original_sewing_spring_vertex_pairs",
)
EXPECTED_SHAPES = ((2635, 3), (2635, 2), (1990,), (7314,), (1990,), (986, 2))


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _check_r3_qa(stage_sha, qa_path):
    if qa_path is None or not qa_path.is_file() or qa_path.is_symlink():
        raise ValueError("unverified R3: new bytes require same-run QA")
    data = json.loads(qa_path.read_text(encoding="utf8"))
    expected = {
        "schema": "stage6-r3-matched-material-2d-body-5-station-trial-v1",
        "R3_stage_npz_sha256": stage_sha,
        "R3_pieces": 24,
        "R3_springs_total": 986,
        "R3_faces": 1990,
        "new_yoke_cdt_triangles": 326,
        "original_hoof_stitch_holes_unchanged": True,
        "factory_cut_patterns_approved": 0,
        "P3": "in_progress",
        "P4": "not_started",
    }
    if any(data.get(k) != v for k, v in expected.items()):
        raise ValueError("unverified R3 same-run QA or research provenance")
    if (
        not 0 <= data["rest_edge_strain_p95_percent"] < 10.5
        or not 0 <= data["rest_edge_strain_max_percent"] < 75
        or data["new_yoke_outer_min_bridge_mm"] < 12.7
    ):
        raise ValueError("unverified R3 seam and 2D material research gate")


def require_verified_r3(stage, source, qa=None):
    """Only accept a signed source and an equivalent R3 stage geometry.

    7-decimal meter coordinates = 0.0001 mm display precision, not a
    manufacturing tolerance. All integer topology arrays remain byte-exact.
    """
    stage, source = Path(stage), Path(source)
    if any(not path.is_file() or path.is_symlink() for path in (stage, source)):
        raise ValueError("unverified R3 source paths")
    if sha256_file(source) != SOURCE_SHA:
        raise ValueError("unverified original Stage6 source PLY SHA")
    stage_sha = sha256_file(stage)
    with np.load(stage, allow_pickle=False) as data:
        ordered = FLOAT_ARRAYS + TOPOLOGY_ARRAYS
        if any(data[k].shape != shape for k, shape in zip(ordered, EXPECTED_SHAPES)):
            raise ValueError("unverified original R3 24-panel geometry or topology")
        fingerprint = hashlib.sha256()
        for key in FLOAT_ARRAYS:
            points = data[key]
            if not np.isfinite(points).all():
                raise ValueError("unverified nonfinite original R3 geometry")
            fingerprint.update(np.round(points, 7).astype("<f8").tobytes())
        for key in TOPOLOGY_ARRAYS:
            fingerprint.update(data[key].tobytes())
        if fingerprint.hexdigest() != R3_CANONICAL_FINGERPRINT:
            raise ValueError("unverified R3 canonical source geometry fingerprint")
    if stage_sha not in R3_TRUSTED_BLOBS:
        _check_r3_qa(stage_sha, Path(qa) if qa is not None else None)
    return stage_sha