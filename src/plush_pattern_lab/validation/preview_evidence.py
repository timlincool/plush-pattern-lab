"""Read-only integrity checks for rendering actual synthetic sewn-cloth evidence."""

from __future__ import annotations


def _count(value: object, name: str) -> int:
    if type(value) is not int or not 0 <= value <= 100000:
        raise ValueError(f"{name}: invalid bounded count")
    return value


def _trial_shape(trial: dict, intersection: dict) -> tuple[int, int]:
    panels = _count(trial.get("panels"), "panels")
    faces = _count(trial.get("total_face_count"), "faces")
    vertices = _count(trial.get("vertices"), "vertices")
    if not 6 <= panels <= 24 or faces < panels * 10 or vertices < panels * 10:
        raise ValueError("Unexpected bounded synthetic mesh geometry")
    if intersection.get("triangle_count") != faces * 2:
        raise ValueError("Audited triangle count differs from trial faces")
    if intersection.get("vertex_count") != vertices:
        raise ValueError("Audited vertex count differs from trial")
    if intersection.get("research_trial_self_collision_enabled") is not trial.get(
        "self_collision_enabled"
    ):
        raise ValueError("Conflicting self-collision experiments")
    return panels, faces


def _intersection_counts(intersection: dict) -> tuple[int, int]:
    other = _count(intersection.get("nonadjacent_other_pair_count"), "other")
    seam = _count(intersection.get("nonadjacent_seam_related_pair_count"), "seam")
    total = _count(intersection.get("nonadjacent_total_intersections"), "total")
    if total != seam + other:
        raise ValueError("Audit intersection categories disagree")
    return other, seam


def _witnesses(intersection: dict, other: int, seam: int, faces: int) -> None:
    localization = intersection.get("localization")
    if not isinstance(localization, dict):
        raise ValueError("No saved-face attribution")
    counts = localization.get("counts")
    if not isinstance(counts, dict) or counts.get("other") != other:
        raise ValueError("Localized nonseam collision counts disagree")
    if counts.get("seam") != seam:
        raise ValueError("Localized seam collision counts disagree")
    witness_map = localization.get("witnesses")
    if not isinstance(witness_map, dict) or not isinstance(witness_map.get("other"), list):
        raise ValueError("No inspectable nonseam witnesses")
    samples = witness_map["other"]
    if len(samples) != min(other, 64):
        raise ValueError("Nonseam witness sample coverage changed")
    for record in samples:
        pair = record.get("triangle_indices") if isinstance(record, dict) else None
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError("Invalid triangle witness")
        if any(type(index) is not int or not 0 <= index < faces * 2 for index in pair):
            raise ValueError("Invalid saved-mesh triangle index")


def verify_snapshot(trial: dict, intersection: dict, *, blend_sha: str, trial_sha: str) -> dict:
    """Never claim an inspection image is a physical or certified toy."""
    if trial.get("status") != "ACTUAL_CAPPED_CLOTH_SEWING_RESEARCH_ONLY":
        raise ValueError("Expected real capped Blender trial evidence")
    if intersection.get("status") != "FINITE_ZERO_THICKNESS_TRIANGLE_INTERSECTION_SCREEN":
        raise ValueError("Expected saved-mesh triangle audit evidence")
    if intersection.get("case_sha256") != blend_sha:
        raise ValueError("Saved .blend does not match audited model SHA-256")
    if intersection.get("source_report_sha256") != trial_sha:
        raise ValueError("Trial report does not match audited report SHA-256")
    panels, faces = _trial_shape(trial, intersection)
    other, seam = _intersection_counts(intersection)
    _witnesses(intersection, other, seam, faces)
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
        "research_contact_pass": other + seam == 0,
        "geometry_not_manufacturing_certified": True,
        "limitations": [
            "Rendered saved Blender mesh, not a physical sewn or stuffed sample",
            "The original Alpaca design is not included or reproduced here",
            "Self intersections are not fixed by rendering or colored overlays",
            "Finite BVH witnesses do not certify fabric thickness or safety",
        ],
    }
