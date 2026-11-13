"""Trace the source-locked Stage6 Z230 three loops against the old 24-piece cap.

This is a 1:1 millimetre design-review overlay, NOT an unwrapped fabric pattern.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union

SOURCE_SHA = "f99ddcb834b4e68bec2487b41730e805c14928953b768d41fc249efe44920717"
TRIAL_SHA = "eebda049ac34ee201a3251b363a915fa05ad6417394bc565bb4cc7942b4545ae"
WITNESS_SHA = "b561770a6cfeaea33abedc11bfb3992b2fe80b4bf83d10a66459682938af6571"
BLEND_SHA = "38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a"
SCHEMA = "stage6-real-z230-three-loop-vs-24piece-A-B-cap-1to1-v1"
Z = 230
# A rigid transformation from source X/Y millimetres to A4 X/Y millimetres.
PAGE_SHIFT_X = 105.0
PAGE_CENTER_Y = 99.0
SOURCE_CENTER_Y = -47.0


def _locked_json(path, expected):
    if not path.is_file() or path.is_symlink():
        raise ValueError("original Stage6 artifact member missing or symlinked")
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected:
        raise ValueError("original Stage6 source artifact SHA256 changed")
    return json.loads(payload)


def load_compact_witness(path):
    """Reopen source-locked original evidence after the Action Artifact expires."""
    saved = _locked_json(path, WITNESS_SHA)
    if (
        saved.get("schema")
        != "stage6-original-source-z230-crown-three-contour-review-witness-v1"
        or saved.get("original_public_blend_sha256") != BLEND_SHA
        or saved.get("original_contour_full_detail_sha256") != SOURCE_SHA
        or saved.get("original_A_B_trial_full_sha256") != TRIAL_SHA
        or saved.get("source_section_z_mm") != Z
        or saved.get("source_component_count") != 3
        or saved.get("factory_patterns_approved") != 0
        or saved.get("P3_status") != "in_progress"
        or saved.get("P4_status") != "not_started"
    ):
        raise ValueError("original trusted Source ID witness provenance changed")
    source = {
        "schema": "stage6-true-triangle-plane-component-loops-v1",
        "factory_cutting_approved": 0,
        "sections": [
            {
                "plane_z_mm": Z,
                "true_source_plane_intersection_component_count": 3,
                "source_contours": saved["source_contours"],
            }
        ],
    }
    entries = [
        {
            "name": name,
            "head_rings_z_mm": [145, 155, 180, 205, Z],
            "head_top_cap": {"outer_stitch_xy_mm": saved["old_A_B_head_top_cap_xy_mm"]},
        }
        for name in ("A_separate_stuffed_head", "B_integrated_neck_port")
    ]
    trial = {
        "schema": "stage6-separated-torso-headneck-mother-trial-ab-v1",
        "factory_cutting_patterns_approved": 0,
        "options": entries,
    }
    return source, trial


def _original_loop(row):
    xy = np.asarray(row["true_interpolated_contour_xy_mm"], dtype=np.float64)
    ids = np.asarray(row["crossed_original_mesh_vertex_id_edge_pairs"], dtype=np.int64)
    if (
        xy.ndim != 2
        or xy.shape[1] != 2
        or ids.shape != (len(xy), 2)
        or len(xy) < 4
        or not np.isfinite(xy).all()
        or np.any(ids < 0)
        or row.get("closed_loop") is not True
        or row.get("simple_polygon") is not True
    ):
        raise ValueError("real source crossing coordinates or edge IDs malformed")
    digest = hashlib.sha256(
        ids.astype("<i8").tobytes() + xy.astype("<f8").tobytes()
    ).hexdigest()
    if digest != row["original_source_edge_and_interpolated_xy_sha256"]:
        raise ValueError("source edge IDs and interpolated XY SHA do not match")
    polygon = Polygon(xy)
    if (
        not polygon.is_valid
        or polygon.area <= 0
        or abs(polygon.length - row["contour_perimeter_mm"]) > 1e-6
    ):
        raise ValueError("source perimeter or original contour no longer valid")
    return xy, polygon


def _old_cap(study):
    options = study.get("options", [])
    if (
        study.get("schema") != "stage6-separated-torso-headneck-mother-trial-ab-v1"
        or study.get("factory_cutting_patterns_approved") != 0
        or len(options) != 2
        or {x["name"] for x in options}
        != {"A_separate_stuffed_head", "B_integrated_neck_port"}
    ):
        raise ValueError("verified A/B split head old cap source required")
    candidates = []
    for option in options:
        if option["head_rings_z_mm"][-1] != Z:
            raise ValueError("old crown trial is not at the same Z230 source level")
        xy = np.asarray(option["head_top_cap"]["outer_stitch_xy_mm"], dtype=float)
        if xy.shape != (64, 2) or not np.isfinite(xy).all():
            raise ValueError("old A/B envelope 64-point cap changed")
        candidates.append(xy)
    if np.max(np.abs(candidates[0] - candidates[1])) > 1e-8:
        raise ValueError("A/B no longer share the same top cap envelope")
    polygon = Polygon(candidates[0])
    if not polygon.is_valid or polygon.area <= 0:
        raise ValueError("the old head crown surrogate polygon is invalid")
    return candidates[0], polygon


def _page_points(xy):
    x = PAGE_SHIFT_X + xy[:, 0]
    y = PAGE_CENTER_Y - (xy[:, 1] - SOURCE_CENTER_Y)
    if min(x) < 12 or max(x) > 198 or min(y) < 47 or max(y) > 155:
        raise ValueError("full-scale true source ring clips the A4 review region")
    return x, y


def measure(source, study):
    if (
        source.get("schema") != "stage6-true-triangle-plane-component-loops-v1"
        or source.get("factory_cutting_approved") != 0
    ):
        raise ValueError("actual original Stage6 triangle-plane source required")
    matching = [item for item in source["sections"] if item["plane_z_mm"] == Z]
    if (
        len(matching) != 1
        or matching[0]["true_source_plane_intersection_component_count"] != 3
        or len(matching[0]["source_contours"]) != 3
    ):
        raise ValueError("true Stage6 Z230 contains exactly three source rings")
    loops = [_original_loop(x) for x in matching[0]["source_contours"]]
    polygons = [poly for _, poly in loops]
    if any(
        not p.disjoint(q) for i, p in enumerate(polygons) for q in polygons[i + 1 :]
    ):
        raise ValueError("real source Z230 components overlap or intersect")
    if not polygons[1].centroid.x < polygons[0].centroid.x < polygons[2].centroid.x:
        raise ValueError("left, central, right original mesh identity changed")
    cap_xy, cap = _old_cap(study)
    for xy in [*(row[0] for row in loops), cap_xy]:
        _page_points(xy)
    return (
        {
            "schema": SCHEMA,
            "original_blend_sha256": BLEND_SHA,
            "source_detail_sha256": SOURCE_SHA,
            "source_trial_sha256": TRIAL_SHA,
            "plane_z_mm": Z,
            "real_original_source_components": 3,
            "source_original_boundary_edges_per_component": [
                len(xy) for xy, _ in loops
            ],
            "source_true_loop_perimeters_mm": [p.length for p in polygons],
            "old_A_B_single_surrogate_cap_perimeter_mm": cap.length,
            "old_A_B_single_surrogate_cap_to_actual_central_ratio": (
                cap.length / polygons[0].length
            ),
            "central_vs_surrogate_planar_boundary_hausdorff_mm": (
                polygons[0].boundary.hausdorff_distance(cap.boundary)
            ),
            "true_source_three_component_total_perimeter_mm": sum(
                poly.length for poly in polygons
            ),
            "true_source_three_component_area_mm2": unary_union(polygons).area,
            "old_surrogate_cap_area_mm2": cap.area,
            "original_section_3d_intersection_is_not_a_sewing_seam": True,
            "old_24piece_head_cap_rejected_as_anatomical_source_approximation": True,
            "geometry_unmodified": True,
            "projected_source_xy_is_not_a_flat_fabric_pattern": True,
            "notch_seam_allowance_grain_or_physical_trial_validated": False,
            "factory_cutting_patterns_approved": 0,
            "P3_status": "in_progress",
            "P4_status": "not_started",
        },
        loops,
        cap_xy,
    )


def _path(xy):
    x, y = _page_points(xy)
    return "M " + " L ".join(f"{a:.5f},{b:.5f}" for a, b in zip(x, y)) + " Z"


def render(loops, cap_xy, metrics):
    items = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="210mm" '
        'height="297mm" viewBox="0 0 210 297">',
        '<rect width="210" height="297" fill="white"/>',
        '<text x="13" y="12" font-size="6">STAGE6 REAL SOURCE CROWN | Z=230mm</text>',
        '<text x="13" y="19" font-size="3.4">1:1 ORIGINAL XY vs old A/B surrogate | STUDY ONLY</text>',
        '<text x="13" y="26" font-size="3.4" fill="#ae2626">'
        "NOT A CUT/SEW PATTERN - no allowance, stitch line or fabric model</text>",
        '<rect x="12" y="43" width="186" height="116" fill="#fbfbfb" '
        'stroke="#ccc" stroke-width=".3"/>',
        f'<path id="old-surrogate" d="{_path(cap_xy)}" stroke="#b75024" '
        'stroke-width=".65" stroke-dasharray="2 1.3" fill="none"/>',
    ]
    for (name, color), (xy, _) in zip(
        (("central", "#086f9a"), ("left", "#328a55"), ("right", "#8c58a0")),
        loops,
    ):
        items.append(
            f'<path id="actual-{name}" d="{_path(xy)}" fill="none" '
            f'stroke="{color}" stroke-width=".5" data-true-source-edges="{len(xy)}"/>'
        )
    gap = metrics["central_vs_surrogate_planar_boundary_hausdorff_mm"]
    items.extend(
        [
            '<text x="13" y="173" font-size="3.9" fill="#086f9a">BLUE actual central 153.09mm</text>',
            '<text x="13" y="180" font-size="3.9" fill="#328a55">GREEN actual left 45.52mm</text>',
            '<text x="13" y="187" font-size="3.9" fill="#8c58a0">PURPLE actual right 45.51mm</text>',
            '<text x="13" y="194" font-size="3.9" fill="#b75024">'
            "ORANGE dashed old A/B 319.77mm (one surrogate ring)</text>",
            '<text x="13" y="207" font-size="3.5">'
            "Original crown: 3 disconnected loops; trial: 1 cap.</text>",
            f'<text x="13" y="214" font-size="3.5">'
            f"2D XY boundary Hausdorff (central vs trial): {gap:.2f}mm</text>",
            '<text x="13" y="221" font-size="3.5">'
            "True 3D surface cross-sections are NOT unwrapped fabric shapes.</text>",
            '<path d="M 50,249 L 150,249 M 50,246 L 50,252 '
            'M 150,246 L 150,252" stroke="black" stroke-width=".45"/>',
            '<text x="80" y="245" font-size="4">100mm / print actual size</text>',
            '<rect x="17" y="240" width="10" height="10" fill="none" '
            'stroke="black" stroke-width=".4"/>',
            '<text x="17" y="257" font-size="3.1">10 x 10mm</text>',
            '<text x="13" y="273" font-size="3.5">'
            "SOURCE ORIGINAL | no cutting, stitching, filling or approval</text>",
            '<text x="13" y="282" font-size="3.5">'
            "P3 IN PROGRESS | P4 NOT STARTED | FACTORY APPROVED = 0</text>",
            "</svg>",
        ]
    )
    return "\n".join(items) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-detail", type=Path)
    parser.add_argument("--trial", type=Path)
    parser.add_argument(
        "--witness",
        type=Path,
        default=(
            Path(__file__).resolve().parents[1]
            / "experiments/stage6_z230_true_crown_20261113/witness.json"
        ),
    )
    parser.add_argument("--svg", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.svg.suffix != ".svg" or args.report.suffix != ".json":
        raise ValueError("output extensions must be svg and json")
    if args.svg.resolve() == args.report.resolve() or any(
        p.exists() or p.is_symlink() for p in (args.svg, args.report)
    ):
        raise ValueError("do not overwrite existing source review evidence")
    if args.source_detail is None and args.trial is None:
        source, trial = load_compact_witness(args.witness)
    elif args.source_detail is not None and args.trial is not None:
        source = _locked_json(args.source_detail, SOURCE_SHA)
        trial = _locked_json(args.trial, TRIAL_SHA)
    else:
        raise ValueError("provide both original full source and trial, or neither")
    metrics, loops, cap_xy = measure(source, trial)
    svg = render(loops, cap_xy, metrics)
    metrics["svg_sha256"] = hashlib.sha256(svg.encode("utf8")).hexdigest()
    args.svg.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.svg.write_text(svg, encoding="utf8")
    args.report.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(
        "STAGE6_SOURCE_CROWN_3_LOOPS_VS_ONE_24PIECE_CAP_NOT_FACTORY",
        json.dumps(
            {
                "true_source_components": 3,
                "old_cap_mm": round(
                    metrics["old_A_B_single_surrogate_cap_perimeter_mm"], 3
                ),
                "factory_approved": False,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
