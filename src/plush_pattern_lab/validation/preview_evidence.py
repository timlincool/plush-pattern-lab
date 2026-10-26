"""Provenance and count checks for a rendered *synthetic* saved-cloth snapshot.

Read-only evidence checks are independent from Blender's Python API.
An image generated with these checks is never a manufactured physical sample.
"""

from __future__ import annotations


def _bounded_integer(value: object, name: str) -> int:
    if type(value) is not int or value < 0 or value > 100000:
        raise ValueError(f"{name}: invalid bounded count")
    return value


def verify_snapshot(trial: dict, intersection: dict, *, blend_sha: str, trial_sha: str) -> dict:
    if trial.get("status") != "ACTUAL_CAPPED_CLOTH_SEWING_RESEARCH_ONLY":
        raise ValueError("Expected real capped Blender trial evidence")
    if intersection.get("status") != "FINITE_ZERO_THICKNESS_TRIANGLE_INTERSECTION_SCREEN":
        raise ValueError("Expected saved-mesh triangle audit evidence")
    if intersection.get("case_sha256") != blend_sha:
        raise ValueError("Saved .blend does not match audited model SHA-256")
    if intersection.get("source_report_sha256") != trial_sha:
        raise ValueError("Trial report does not match audited report SHA-256")
    panels = _bounded_integer(trial.get("panels"), "panels")
    faces = _bounded_integer(trial.get("total_face_count"), "faces")
    vertices = _bounded_integer(trial.get("vertices"), "vertices")
    other = _bounded_integer(intersection.get("nonadjacent_other_pair_count"), "other")
    seam = _bounded_integer(intersection.get("nonadjacent_seam_related_pair_count"), "seam")
    total = _bounded_integer(intersection.get("nonadjacent_total_intersections"), "total")
    if not 6 <= panels <= 24 or faces < panels * 10 or vertices < panels * 10:
        raise ValueError("Unexpected bounded synthetic mesh geometry")
    if total != seam + other:
        raise ValueError("Audit intersection categories disagree")
    if intersection.get("triangle_count") != faces * 2:
        raise ValueError("Audited triangle count differs from trial faces")
    if intersection.get("vertex_count") != vertices:
        raise ValueError("Audited vertex count differs from trial")
    if intersection.get("research_trial_self_collision_enabled") is not trial.get(
        "self_collision_enabled"
    ):
        raise ValueError("Conflicting self-collision experiments")
    localization = intersection.get("localization")
    if not isinstance(localization, dict):
        raise ValueError("No saved-face attribution")
    counts = localization.get("counts")
    if not isinstance(counts, dict) or counts.get("other") != other or counts.get("seam") != seam:
        raise ValueError("Localized collision counts disagree")
    witnesses = localization.get("witnesses")
    if not isinstance(witnesses, dict) or not isinstance(witnesses.get("other"), list):
        raise ValueError("No inspectable nonseam witnesses")
    samples = witnesses["other"]
    if len(samples) != min(other, 64):
        raise ValueError("Nonseam witness sample coverage changed")
    for witness in samples:
        if not isinstance(witness, dict) or not isinstance(
            witness.get("triangle_indices"), list
        ):
            raise ValueError("Invalid triangle witness")
        pair = witness["triangle_indices"]
        if len(pair) != 2 or any(type(i) is not int or i < 0 or i >= faces * 2 for i in pair):
            raise ValueError("Invalid saved-mesh triangle index")
    return {
        "schema": "plush-synthetic-visual-inspection-v1",
        "status": "NUMERICAL_SYNTHETIC_CLOTH_NOT_REAL_PLUSH_OR_ORIGINAL_DESIGN",
        "blender_snapshot_sha256": blend_sha,
        "simulation_report_sha256": trial_sha,
        "panels": panels,
        "two_caps": True,
        "face_count": faces,
        "finite_nonseam_intersections": other,
        "finite_seam_related_intersections": seam,
        "research_contact_pass": total == 0,
        "geometry_not_manufacturing_certified": True,
        "limitations": [
            "Rendered saved Blender mesh, not a physical sewn or stuffed sample",
            "The original Alpaca design is not included or reproduced here",
            "Self intersections are not fixed by rendering or colored overlays",
            "Finite BVH witnesses are not continuous-time or fabric thickness certification",
        ],
    }
