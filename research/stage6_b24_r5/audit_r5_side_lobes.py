"""Independent R5 seam, material and topological research gate.

Never accepts a visually plausible 3D preposition as actually sewn fabric.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union

BASE_R3_VERTICES = 2635
OLD_SPRINGS = 986


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    with np.load(path, allow_pickle=False) as data:
        return {k: data[k].copy() for k in data.files}


def unpack(sizes, ids):
    faces, offset = [], 0
    for n in sizes:
        face = np.asarray(ids[offset:offset + int(n)], dtype=int)
        if len(set(face)) != len(face):
            raise ValueError("repeated polygon vertex inside R5 fabric face")
        faces.append(face)
        offset += int(n)
    if offset != len(ids):
        raise ValueError("packed face length inconsistent")
    return faces


def all_edges(faces):
    counter = Counter()
    for f in faces:
        counter.update(tuple(sorted((int(a), int(b)))) for a, b in zip(f, np.roll(f, -1)))
    if set(counter.values()) - {1, 2}:
        raise ValueError("fabric has edge incidence over 2 or missing")
    return counter


def strain(xyz, rest, edges):
    xyzlen = np.linalg.norm(xyz[edges[:, 0]] - xyz[edges[:, 1]], axis=1)
    uvlen = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)
    if xyzlen.min() <= 1e-10 or uvlen.min() <= 1e-10:
        raise ValueError("collapsed 2D/3D material edge")
    delta = abs(xyzlen / uvlen - 1) * 100
    return {"count": len(edges), "P95_pct": float(np.percentile(delta, 95)),
            "mean_pct": float(delta.mean()), "max_pct": float(delta.max())}


def comparison(uv, left, right):
    a = np.linalg.norm(np.diff(uv[left], axis=0), axis=1)
    b = np.linalg.norm(np.diff(uv[right], axis=0), axis=1)
    if len(a) != len(b):
        raise ValueError("unequal R5 paired sewing segment counts")
    return float(np.max(abs(a - b)) * 1000)


def detailed_new_seams(uv, all_springs):
    side_data, errors = [], []
    for side_index in range(2):
        holes = np.arange(2635 + 32 * side_index, 2667 + 32 * side_index)
        base = 2699 + side_index * 220
        gores = [np.arange(base + j * 45, base + (j + 1) * 45).reshape(5, 9)
                 for j in range(4)]
        caps = [np.arange(base + 180 + j * 10, base + 190 + j * 10)
                for j in range(4)]
        predicted = []
        for gore_index, gore in enumerate(gores):
            for col in range(8):
                predicted.append((int(holes[gore_index * 8 + col]), int(gore[0, col])))
        for gore_index, gore in enumerate(gores):
            following = gores[(gore_index + 1) % 4]
            predicted.extend((int(a), int(b)) for a, b in zip(gore[:, -1], following[:, 0]))
        for gore, cap in zip(gores, caps):
            predicted.extend((int(gore[-1, col]), int(cap[col])) for col in range(8))
        for wedge_index, cap in enumerate(caps):
            follower = caps[(wedge_index + 1) % 4]
            predicted.extend(((int(cap[-2]), int(follower[0])),
                              (int(cap[-1]), int(follower[-1]))))
        start = OLD_SPRINGS + 92 * side_index
        actual = all_springs[start:start + 92]
        if set(map(tuple, map(sorted, actual))) != set(map(tuple, map(sorted, predicted))):
            raise ValueError("wrong R5 sewing identities for 4 side-gores and 4 tip wedges")
        data = {"side": "L" if side_index == 0 else "R"}
        for gore_index, gore in enumerate(gores):
            data[f"headcap_to_gore_{gore_index+1}_mm"] = comparison(
                uv, np.r_[holes[gore_index * 8:gore_index * 8 + 9] if gore_index < 3 else
                          np.r_[holes[24:], holes[0]]], gore[0]
            )
            following = gores[(gore_index + 1) % 4]
            data[f"gore_side_to_{(gore_index+1)%4+1}_mm"] = comparison(
                uv, gore[:, -1], following[:, 0]
            )
            data[f"gore_to_wedge_{gore_index+1}_mm"] = comparison(
                uv, gore[-1], caps[gore_index][:9]
            )
            follower_cap = caps[(gore_index + 1) % 4]
            data[f"tip_radial_{gore_index+1}_mm"] = abs(
                np.linalg.norm(uv[caps[gore_index][-1]] - uv[caps[gore_index][-2]])
                - np.linalg.norm(uv[follower_cap[-1]] - uv[follower_cap[0]])
            ) * 1000
        errors.extend(value for key, value in data.items() if key.endswith("_mm"))
        side_data.append(data)
    max_error = max(errors)
    if max_error > 1e-4:
        raise ValueError(f"R5 netline mismatch {max_error:.6f} mm exceeds 1e-4 mm")
    return side_data, max_error


def validate_surfaces(faces, rest):
    # Each of the 8 source-guided cloth gores must be unfoldable without 2D overlap.
    overlapping = []
    for side in range(2):
        base = 2699 + side * 220
        for part in range(4):
            lo = base + 45 * part
            polygons = [Polygon(rest[f]) for f in faces
                        if len(f) == 4 and min(f) >= lo and max(f) < lo + 45]
            if len(polygons) != 32 or any(not p.is_valid or p.area <= 1e-12 for p in polygons):
                raise ValueError("R5 newly flattened gore has invalid planar quad")
            sum_area = sum(p.area for p in polygons)
            union = unary_union(polygons).area
            if sum_area - union > 1e-10:
                overlapping.append({"side": side, "panel": part,
                                    "intersection_m2": sum_area - union})
    if overlapping:
        raise ValueError("R5 narrow fabric gores self-overlap in material space")


def audit(stage, old_stage):
    n = load(stage)
    old = load(old_stage)
    v = n["initial_3d_prepositioned_vertices_m"]
    uv = n["true_independent_flat_2d_rest_xy_m"]
    springs = n["original_sewing_spring_vertex_pairs"]
    faces = unpack(n["face_lengths"], n["face_vertex_ids"])
    if v.shape != (3139, 3) or uv.shape != (3139, 2):
        raise ValueError("R5 source-guided side lobe vertices changed")
    if len(faces) != 2378 or springs.shape != (1170, 2):
        raise ValueError("R5 sources do not represent 40 separately sewable panels")
    if not np.array_equal(v[:2635], old["initial_3d_prepositioned_vertices_m"]):
        raise ValueError("R3 original 3D preposition mutated")
    if not np.array_equal(uv[:2635], old["true_independent_flat_2d_rest_xy_m"]):
        raise ValueError("R3 original 2D material rest mutated")
    if not np.array_equal(springs[:986], old["original_sewing_spring_vertex_pairs"]):
        raise ValueError("R3 986 sewing spring pairs changed")
    if len(set(map(tuple, map(sorted, springs)))) != 1170:
        raise ValueError("R5 duplicated sewing spring vertex pair")
    edge_counts = all_edges(faces)
    edge_pairs = np.asarray(sorted(edge_counts), dtype=int)
    material_strain = strain(v, uv, edge_pairs)
    new_pairs = edge_pairs[(edge_pairs >= 2699).all(axis=1)]
    new_strain = strain(v, uv, new_pairs)
    validate_surfaces(faces, uv)
    side_details, max_diff = detailed_new_seams(uv, springs)
    if material_strain["P95_pct"] >= 10.5 or material_strain["max_pct"] >= 75:
        raise ValueError("R5 material preposition did not pass existing research gate")
    return {
        "schema": "stage6-R5-independent-40-piece-matched-netline-and-strain-v1",
        "original_R3_2635_vertices_2d_rest_exactly_unchanged": True,
        "original_R3_986_springs_exactly_unchanged": True,
        "new_research_panels": 16,
        "total_research_panels": 40,
        "actual_evaluated_Cloth_not_yet_run": True,
        "full_unique_fabric_edges": len(edge_pairs),
        "num_2D_material_boundary_edges": sum(n == 1 for n in edge_counts.values()),
        "new_R5_narrow_gores_do_not_self_overlap": True,
        "new_2d_paired_line_length_max_mismatch_mm": max_diff,
        "preposition_global_edge_strain": material_strain,
        "preposition_new_fabric_edge_strain": new_strain,
        "source_guided_2_ear_high_protrusions_not_actual_original_ear_Mesh": True,
        "source_original_4_ear_meshes_physically_sewn": 0,
        "self_collision_contact_and_materials_not_tested": True,
        "factory_cutting_patterns_approved": 0,
        "sides": side_details,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", required=True, type=Path)
    p.add_argument("--r3", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError("R5 independent QA must not overwrite prior result")
    result = audit(a.stage, a.r3)
    a.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
