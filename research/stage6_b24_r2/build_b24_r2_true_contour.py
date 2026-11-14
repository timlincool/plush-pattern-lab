"""Contour-aware B24 R2 research pattern, not a physically sewn plush.

Only modify synthetic body/head gores using genuine Stage6 source sections.
The 13 lower source-linked pieces, 46 numerical interfaces, 974 sewing springs,
shoulder connector and neck-port sewing clearance stay unchanged.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import LineString, Polygon

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from research.stage6_b24_r1.design_b24_r1_source_informed import (  # noqa: E402
    BODY_STATIONS,
    HEAD_STATIONS,
    RESEARCH_VARIANT,
    cap,
    edge_segments,
    gore,
    meridian_steps,
)

SOURCE_SHA = "5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd"
BASE_R1_SHA = "cf87ccb0330763e04c948f69396b0b7322ab59ca723832dad88028979e38bd4e"
CHANGES = {"body": (115, 125), "head": (155, 180, 205, 230)}
ALPHA = {115: 0.25, 125: 0.40, 155: 0.70, 180: 0.70, 205: 0.70, 230: 0.70}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def true_section(mesh, z):
    section = mesh.section(plane_origin=(0, 0, z), plane_normal=(0, 0, 1))
    if section is None:
        raise ValueError("actual source Stage6 section missing")
    loops = []
    for points in section.discrete:
        if len(points) > 10 and np.linalg.norm(points[0] - points[-1]) < 0.001:
            polygon = Polygon(points[:, :2])
            if polygon.is_valid and polygon.area > 50:
                loops.append(polygon)
    expected = {125: 2, 230: 3}.get(z, 1)
    if len(loops) != expected:
        raise ValueError("Stage6 source loop identity changed")
    return max(loops, key=lambda p: p.area), len(loops)


def source_radial_ring(old, source):
    old = np.asarray(old, dtype=float)
    if old.shape != (64, 2) or not Polygon(old).is_valid:
        raise ValueError("nonvalid indexed 64-station paper ring")
    center = np.asarray(source.centroid.coords[0])
    old_center = old.mean(axis=0)
    result = []
    for point in old:
        vector = point - old_center
        direction = vector / np.linalg.norm(vector)
        crossing = source.exterior.intersection(
            LineString((center, center + direction * 500))
        )
        pieces = list(crossing.geoms) if hasattr(crossing, "geoms") else [crossing]
        hits = []
        for item in pieces:
            if item.geom_type in {"Point", "LineString"}:
                hits.extend(np.asarray(item.coords))
        valid = [
            (float(np.dot(hit - center, direction)), hit)
            for hit in hits
            if np.dot(hit - center, direction) > 1e-6
        ]
        if not valid:
            raise ValueError("source contour ray has no positive crossing")
        result.append(max(valid, key=lambda pair: pair[0])[1])
    ring = np.asarray(result)
    if not Polygon(ring).is_valid:
        raise ValueError("source radial sample is self-intersecting")
    return ring


def change_stations(mesh, original, group, heights):
    baseline = np.asarray(original, dtype=float)
    revised = baseline.copy()
    report = []
    for row, z in enumerate(heights):
        if z not in CHANGES[group]:
            continue
        target, loops = true_section(mesh, z)
        fitted = source_radial_ring(baseline[row], target)
        revised[row] = (1 - ALPHA[z]) * baseline[row] + ALPHA[z] * fitted
        old, new = Polygon(baseline[row]), Polygon(revised[row])
        if not new.is_valid:
            raise ValueError("revised physical ring crosses itself")
        before = old.intersection(target).area / old.union(target).area
        after = new.intersection(target).area / new.union(target).area
        if after <= before + 0.01:
            raise ValueError("new source contour alignment did not improve")
        report.append(
            {
                "group": group,
                "height_mm": z,
                "original_closed_source_loops": loops,
                "fit_fraction": ALPHA[z],
                "R1_source_xy_IoU": before,
                "R2_source_xy_IoU": after,
                "revised_area_to_original_source": new.area / target.area,
                "mean_3d_ring_move_mm": float(
                    np.linalg.norm(revised[row] - baseline[row], axis=1).mean()
                ),
            }
        )
    return revised, report


def recreate_sewable_surfaces(trial, body, head):
    body_steps = meridian_steps(body, BODY_STATIONS)
    head_steps = meridian_steps(head, HEAD_STATIONS)
    for item in trial["torso_gore_pieces"]:
        item.update(gore(item["id"], body, BODY_STATIONS, body_steps))
    for item in trial["headneck_gore_pieces"]:
        item.update(gore(item["id"], head, HEAD_STATIONS, head_steps))
    trial["body_synthetic_rings_xy_mm"] = body.tolist()
    trial["head_synthetic_rings_xy_mm"] = head.tolist()
    trial["body_meridian_step_mm"] = body_steps.tolist()
    trial["head_meridian_step_mm"] = head_steps.tolist()
    trial["head_top_cap"] = cap(head[-1], "HEAD-TOP-CAP-TRIAL")


def confirm_immutable_interfaces(original, changed, graph):
    for group, indices in (("body", (0, -1)), ("head", (0,))):
        before = original[f"{group}_synthetic_rings_xy_mm"]
        after = changed[f"{group}_synthetic_rings_xy_mm"]
        for index in indices:
            if not np.array_equal(before[index], after[index]):
                raise ValueError("cannot mutate protected lower or neck source ring")
    if changed["shoulder_cap"] != original["shoulder_cap"]:
        raise ValueError("shoulder allowance changed")
    if changed["neck_collar_if_integrated"] != original["neck_collar_if_integrated"]:
        raise ValueError("neck collar physical interface changed")
    checked = 0
    for pair in graph["sewing_interfaces"]:
        first = edge_segments(pair["first"], changed, pair)
        second = edge_segments(pair["second"], changed, pair)
        if first is None or second is None:
            continue
        if first.shape != second.shape or np.max(abs(first - second)) > 1e-4:
            raise ValueError("R2 seam mismatch " + pair["id"])
        pair["first_2d_netline_mm"] = float(first.sum())
        pair["second_2d_netline_mm"] = float(second.sum())
        pair["max_segment_disagreement_mm"] = float(np.max(abs(first - second)))
        checked += 1
    if len(graph["sewing_interfaces"]) != 46 or checked < 22:
        raise ValueError("R2 did not preserve the seam graph")
    return checked


def build(source, baseline, graph_path, out):
    if sha(source) != SOURCE_SHA or sha(baseline) != BASE_R1_SHA:
        raise ValueError("R2 needs exact original PLY and same-run R1 source JSON")
    mesh = trimesh.load(source, force="mesh")
    if len(mesh.faces) != 116568:
        raise ValueError("Stage6 source 25-percent triangle count changed")
    upper = json.loads(Path(baseline).read_text(encoding="utf8"))
    graph = json.loads(Path(graph_path).read_text(encoding="utf8"))
    trial = next(x for x in upper["options"] if x["name"] == RESEARCH_VARIANT)
    old = copy.deepcopy(trial)
    body, b_report = change_stations(
        mesh, trial["body_synthetic_rings_xy_mm"], "body", BODY_STATIONS
    )
    head, h_report = change_stations(
        mesh, trial["head_synthetic_rings_xy_mm"], "head", HEAD_STATIONS
    )
    recreate_sewable_surfaces(trial, body, head)
    checked = confirm_immutable_interfaces(old, trial, graph)
    if graph["factory_cut_patterns_approved"] != 0:
        raise ValueError("R2 cannot be promoted to factory patterns")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    payloads = {
        "B24_R2_upper_RESEARCH_ONLY.json": upper,
        "B24_R2_seam_graph_46_RESEARCH_ONLY.json": graph,
    }
    for name, obj in payloads.items():
        (out / name).write_text(
            json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
        )
    report = {
        "schema": "stage6-B24-R2-contour-station-research-v1",
        "original_25pct_ply_sha256": SOURCE_SHA,
        "original_R1_source_sha256": BASE_R1_SHA,
        "24_independent_panel_roles_preserved": True,
        "13_lower_source_anchored_panels_unmodified": True,
        "original_974_sewing_pairs_reused": True,
        "number_of_numerical_seam_interfaces": 46,
        "both_sides_verified": checked,
        "real_source_sections": b_report + h_report,
        "two_true_side_head_protrusions_not_sewn": True,
        "new_physical_blender_simulation_executed": False,
        "factory_patterns_approved": 0,
        "P3": "in_progress",
        "P4": "not_started",
    }
    (out / "B24_R2_true_source_ring_QA.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("source", "baseline", "graph", "out"):
        parser.add_argument("--" + arg, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.baseline, args.graph, args.out), indent=2))


if __name__ == "__main__":
    main()
