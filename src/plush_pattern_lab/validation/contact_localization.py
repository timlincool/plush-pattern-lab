"""Read-only, bounded spatial attribution of triangle intersection witnesses.

This is not another intersection detector: Blender BVH decides candidate pairs.
Use the SAVED mesh face indices to map witnesses to the original sewn panels,
upper/lower caps and the last two rows adjacent to each cap.
"""

from __future__ import annotations

from collections import Counter

MAX_DIAGNOSTIC_PAIRS = 100000
MAX_PANEL_GROUPS = 80
MAX_WITNESSES = {"other": 64, "seam": 24}


def _polygon_identity(polygon: int, panels: int, gores: int) -> tuple[str, str]:
    if polygon >= gores:
        return ("UPPER", "upper_cap") if polygon < gores + panels else (
            "LOWER",
            "lower_cap",
        )
    per_panel = gores // panels
    row = (polygon % per_panel) // 2
    rows = per_panel // 2
    zone = "upper_join" if row < 2 else "lower_join" if row >= rows - 2 else "body"
    return f"P{polygon // per_panel + 1:02d}", zone


def polygon_identities(
    polygon_ids: list[int], *, panels: int, gore_faces: int, face_count: int
) -> tuple[list[str], list[str]]:
    """Map each Blender loop-triangle polygon_index to its saved cloth role.

    _append_gores creates two quads per lateral row, one panel at a time.
    _append_caps then creates exactly N upper and N lower quads.
    Refuse attribution if any part of that declared layout is inconsistent.
    """
    if not (6 <= panels <= 24) or gore_faces < 8 * panels:
        raise ValueError("Unexpected capped mesh panel topology")
    if gore_faces % (2 * panels) or face_count != gore_faces + 2 * panels:
        raise ValueError("Face layout does not match capped sewing evidence")
    if len(polygon_ids) != face_count * 2:
        raise ValueError("Expected two loop triangles for every capped quad")
    if any(type(index) is not int or not 0 <= index < face_count for index in polygon_ids):
        raise ValueError("Invalid triangle to polygon attribution")
    identities = [_polygon_identity(index, panels, gore_faces) for index in polygon_ids]
    return [ident[0] for ident in identities], [ident[1] for ident in identities]


def _category(a: tuple[int, ...], b: tuple[int, ...], neighbors: dict) -> str:
    if set(a) & set(b):
        return "shared"
    return "seam" if any(v in neighbors[u] for u in a for v in b) else "other"


def _center_mm(vertices: list, triangle: tuple[int, ...]) -> list[float]:
    return [
        round(sum(float(vertices[index][axis]) for index in triangle) * 1000 / 3, 5)
        for axis in range(3)
    ]


def _witness(pair: tuple[int, int], vertices: list, faces: list, labels: list, zones: list) -> dict:
    a, b = pair
    return {
        "triangle_indices": [a, b],
        "panel_names": [labels[a], labels[b]],
        "zones": [zones[a], zones[b]],
        "triangle_centroids_mm": [
            _center_mm(vertices, faces[a]),
            _center_mm(vertices, faces[b]),
        ],
    }


def _summary(groups: Counter, maximum: int) -> tuple[list[dict], bool]:
    ordered = sorted(groups.items(), key=lambda row: (-row[1], row[0]))
    return (
        [
            {
                "category": category,
                "region_pair": list(pair),
                "intersecting_pairs": count,
            }
            for (category, pair), count in ordered[:maximum]
        ],
        len(ordered) > maximum,
    )


def describe_contacts(
    candidates: set[tuple[int, int]],
    vertices: list,
    faces: list,
    neighbors: dict,
    labels: list[str],
    zones: list[str],
) -> dict:
    """Produce reproducible evidence without changing any BVH classification.

    Regions come from saved polygon ordering, not an inferred visual surface.
    Triangle centroid coordinates are representative locations, NOT exact
    intersection points. Caps and seam-related intersections remain vetoed.
    """
    if len(faces) != len(labels) or len(faces) != len(zones):
        raise ValueError("Triangle labels must cover every triangle")
    if len(candidates) > MAX_DIAGNOSTIC_PAIRS:
        raise ValueError("Diagnostic pair budget exceeded")
    panel_groups: Counter = Counter()
    zone_groups: Counter = Counter()
    counts: Counter = Counter()
    examples: dict[str, list[dict]] = {"seam": [], "other": []}
    for pair in sorted(candidates):
        a, b = pair
        if not (0 <= a < len(faces) and 0 <= b < len(faces) and a < b):
            raise ValueError("Invalid or noncanonical triangle pair")
        category = _category(faces[a], faces[b], neighbors)
        counts[category] += 1
        if category == "shared":
            continue
        panel_groups[category, tuple(sorted((labels[a], labels[b])))] += 1
        zone_groups[category, tuple(sorted((zones[a], zones[b])))] += 1
        if len(examples[category]) < MAX_WITNESSES[category]:
            examples[category].append(_witness(pair, vertices, faces, labels, zones))
    panel_rows, truncated = _summary(panel_groups, MAX_PANEL_GROUPS)
    zone_rows, _ = _summary(zone_groups, MAX_PANEL_GROUPS)
    return {
        "schema": "plush-capped-contact-localization-v1",
        "basis": "Blender 4.3.x saved quad polygon_index and finite BVH witnesses",
        "representative_coordinates": "triangle centroids in mm, not exact intersection points",
        "counts": {key: counts[key] for key in ("shared", "seam", "other")},
        "by_panel_pair": panel_rows,
        "panel_groups_truncated": truncated,
        "by_zone_pair": zone_rows,
        "witnesses": examples,
        "witness_sample_limited": {
            key: counts[key] > MAX_WITNESSES[key] for key in ("seam", "other")
        },
    }
