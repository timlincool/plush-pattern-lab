"""Source-guided R5 two side-lobe cloth grafts attached to R3 head crown.

Research only: two cap holes are newly designed, not original Stage6 3D seams.
The original 41 visual accessories are NOT part of the sewn geometry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from shapely import constrained_delaunay_triangles
from shapely.geometry import Point, Polygon

R3_SHA = "d93afe5667bc2c808e4700c5554a858b1df9b1574c9e23de1cb2c08b42c27fc3"
R3_EQUIVALENT_SHA = "faf7dfa2129e7a1ce63d4829cb49b0ef85608fa0c39cd7271ef36a5c53a9a2e5"
SOURCE_SHA = "5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd"
CAP_BEGIN = 876
CAP_OUTER = 64
CAP_CENTER = CAP_BEGIN + CAP_OUTER
HOLE_CENTERS_X = (-10.0, 10.0)
HOLE_CENTER_Y = -47.0
HOLE_RADIUS_MM = 2.5
HOLE_STATIONS = 32
SOURCE_LEVELS_MM = (230.0, 235.0, 245.0)
SOURCE_R3_PANELS = 24
R5_PANELS = SOURCE_R3_PANELS + 16
SEAM_ALLOWANCE_REQUIREMENT_MM = 12.7


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_inputs(r3_path, source_path):
    if (
        _sha(r3_path) not in {R3_SHA, R3_EQUIVALENT_SHA}
        or _sha(source_path) != SOURCE_SHA
    ):
        raise ValueError("unverified R3 native input or Stage6 source PLY")
    with np.load(r3_path, allow_pickle=False) as prior:
        inp = {key: prior[key].copy() for key in prior.files}
    if (
        inp["initial_3d_prepositioned_vertices_m"].shape != (2635, 3)
        or len(inp["face_lengths"]) != 1990
        or inp["original_sewing_spring_vertex_pairs"].shape != (986, 2)
    ):
        raise ValueError("R3 topology changed; cannot weld R5 research geometry")
    import trimesh

    mesh = trimesh.load(source_path, force="mesh")
    if len(mesh.faces) != 116568:
        raise ValueError("original Stage6 source has unexpected triangles")
    return inp, mesh


def _source_loop(mesh, height_mm, side):
    section = mesh.section(plane_origin=(0, 0, height_mm), plane_normal=(0, 0, 1))
    if section is None:
        raise ValueError("missing genuine Stage6 horizontal source section")
    candidates = []
    for raw in section.discrete:
        if len(raw) < 15 or np.linalg.norm(raw[0] - raw[-1]) > 1e-5:
            continue
        poly = Polygon(raw[:, :2])
        if poly.is_valid and poly.area > 10:
            candidates.append(poly)
    if len(candidates) != (3 if height_mm in (230, 235) else 2):
        raise ValueError("original side high protrusion loop identity changed")
    side_loops = [poly for poly in candidates if poly.centroid.x * side > 40]
    if len(side_loops) != 1:
        raise ValueError("ambiguous original Stage6 left/right source cap")
    return side_loops[0]


def _resample_source_loop(poly, count):
    coords = np.asarray(poly.exterior.coords[:-1], dtype=float)
    # Every station has a fixed geometric ordering around the true source loop.
    if poly.exterior.is_ccw is False:
        coords = coords[::-1]
    start = int(np.argmax(coords[:, 1]))
    coords = np.roll(coords, -start, axis=0)
    closed = np.vstack((coords, coords[0]))
    arc = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(closed, axis=0), axis=1))]
    at = np.linspace(0, arc[-1], count, endpoint=False)
    out = np.column_stack([np.interp(at, arc, closed[:, k]) for k in (0, 1)])
    if not Polygon(out).is_valid or not Polygon(out).exterior.is_ccw:
        raise ValueError("new source lobe ring is not a valid CCW silhouette")
    return out


def _make_hole(center_x):
    t = np.linspace(0, 2 * np.pi, HOLE_STATIONS, endpoint=False)
    # Begin at positive Y, same CCW traversal as the original source side loops.
    t = t + np.pi / 2
    return np.column_stack(
        (
            center_x + HOLE_RADIUS_MM * np.cos(t),
            HOLE_CENTER_Y + HOLE_RADIUS_MM * np.sin(t),
        )
    )


def _split_r3_faces(staging):
    sizes = staging["face_lengths"]
    indices = staging["face_vertex_ids"]
    materials = staging["face_material_roles"]
    faces, roles, old_count = [], [], 0
    offset = 0
    for size, role in zip(sizes, materials):
        face = [int(v) for v in indices[offset : offset + int(size)]]
        offset += int(size)
        if set(face) <= set(range(CAP_BEGIN, CAP_CENTER + 1)):
            old_count += 1
        else:
            faces.append(face)
            roles.append(int(role))
    if old_count != 64 or offset != len(indices):
        raise ValueError("R3 top cap fan is not the exact old 64-triangle geometry")
    return faces, roles


def _cap_clearances(outer, holes):
    crown = Polygon(outer, holes)
    if not crown.is_valid or not Polygon(outer).is_valid:
        raise ValueError("new R5 two-hole crown is not valid planar topology")
    outer_min = min(
        Polygon(outer).exterior.distance(Polygon(h).exterior) for h in holes
    )
    gap = Polygon(holes[0]).distance(Polygon(holes[1]))
    if min(outer_min, gap) < SEAM_ALLOWANCE_REQUIREMENT_MM:
        raise ValueError("R5 research head-cap sewing allowances are insufficient")
    return crown, float(outer_min), float(gap)


def _cdt_faces(crown, positions, global_ids):
    result = []
    for triangle in constrained_delaunay_triangles(crown).geoms:
        points = np.asarray(triangle.exterior.coords[:-1])
        indices = []
        for point in points:
            delta = np.linalg.norm(positions - point, axis=1)
            if delta.min() > 1e-6 or (delta < 1e-6).sum() != 1:
                raise ValueError("GEOS inserted an unexpected cap hole corner")
            indices.append(int(global_ids[np.argmin(delta)]))
        if len(set(indices)) != 3:
            raise ValueError("invalid constrained Delaunay source corner identity")
        result.append(indices)
    return result


def _cap_with_two_real_openings(staging, holes, vertex_offset):
    orig = staging["initial_3d_prepositioned_vertices_m"]
    outer = orig[CAP_BEGIN:CAP_CENTER, :2] * 1000
    polygon, outer_gap, hole_gap = _cap_clearances(outer, holes)
    coords = np.vstack((outer, holes[0], holes[1], orig[CAP_CENTER, :2] * 1000))
    ids = np.r_[
        np.arange(CAP_BEGIN, CAP_CENTER),
        np.arange(vertex_offset, vertex_offset + 2 * HOLE_STATIONS),
        [CAP_CENTER],
    ]
    if len(coords) != len(ids):
        raise ValueError("new R5 crown source vertex map mismatch")
    faces = _cdt_faces(polygon, coords, ids)
    # Retain the existing R3 top cap center and split exactly one CDT triangle.
    apex = Point(orig[CAP_CENTER, :2] * 1000)
    selected = next(
        (
            i
            for i, face in enumerate(faces)
            if Polygon(orig[np.asarray(face), :2] * 1000).covers(apex)
        ),
        None,
    )
    if selected is None:
        raise ValueError("old R3 apex is not interior to new crown")
    a, b, c = faces.pop(selected)
    faces.extend([(a, b, CAP_CENTER), (b, c, CAP_CENTER), (c, a, CAP_CENTER)])

    def signed(face):
        x, y, z = orig[np.asarray(face), :2]
        return (y[0] - x[0]) * (z[1] - x[1]) - (y[1] - x[1]) * (z[0] - x[0])

    old_sign = signed((CAP_CENTER, CAP_BEGIN, CAP_BEGIN + 1))
    if old_sign == 0:
        raise ValueError("R3 source head cap winding is degenerate")
    faces = [f if signed(f) * old_sign > 0 else [f[0], f[2], f[1]] for f in faces]
    if len(faces) != 132:
        raise ValueError("expected two-hole CDT crown with 132 triangles")
    return faces, outer_gap, hole_gap


def _add_vertex(arrays, xyz_mm, uv_m):
    start = len(arrays["initial_3d_prepositioned_vertices_m"])
    arrays["initial_3d_prepositioned_vertices_m"] = np.vstack(
        (arrays["initial_3d_prepositioned_vertices_m"], np.asarray(xyz_mm) / 1000)
    )
    arrays["true_independent_flat_2d_rest_xy_m"] = np.vstack(
        (arrays["true_independent_flat_2d_rest_xy_m"], np.asarray(uv_m))
    )
    return np.arange(start, len(arrays["initial_3d_prepositioned_vertices_m"]))


def _fabric_unfold_gore(arc):
    """Unfold a narrow 3D lobe gore with matching lengths on both shared sides."""
    cols = arc.shape[1]
    lengths = []
    for row in arc:
        edge = np.linalg.norm(np.diff(row[:, :2], axis=0), axis=1)
        lengths.append(np.r_[0.0, np.cumsum(edge)])
    rest = np.zeros((len(arc), cols, 2))
    rest[0, :, 0] = lengths[0] - lengths[0][-1] / 2
    for station in range(1, len(arc)):
        old = rest[station - 1]
        vec = old[-1] - old[0]
        angle = np.arctan2(vec[1], vec[0])
        normal = np.array((-np.sin(angle), np.cos(angle)))
        vertical = np.linalg.norm(arc[station] - arc[station - 1], axis=1)
        initial = np.r_[
            (old[0] + old[-1]) / 2 + normal * (vertical[0] + vertical[-1]) / 2, angle
        ]
        current_width = lengths[station][-1]

        def placed(parameters):
            axis = np.array((np.cos(parameters[2]), np.sin(parameters[2])))
            return (
                parameters[:2]
                + (lengths[station] - current_width / 2)[:, None] * axis[None, :]
            )

        def residual(parameters):
            top = placed(parameters)
            gaps = np.array(
                (np.linalg.norm(top[0] - old[0]), np.linalg.norm(top[-1] - old[-1]))
            )
            return np.r_[
                1000.0 * (gaps - vertical[[0, -1]]),
                1.5 * (parameters[2] - angle),
                0.005 * (parameters[:2] - initial[:2]),
            ]

        fitted = least_squares(residual, initial, max_nfev=250)
        rest[station] = placed(fitted.x)
        gap = max(abs(residual(fitted.x)[:2])) / 1000
        if gap >= 0.0001:
            raise ValueError("2D gore side seam cannot be matched exactly")
        base_edge = old[-1] - old[0]
        apex = rest[station][0] - old[0]
        if float(base_edge[0] * apex[1] - base_edge[1] * apex[0]) <= 0:
            raise ValueError("R5 2D gore strip turned over")
    return rest


def _append_side_gores(arrays, faces, roles, springs, hole_ids, side, full, heights):
    all_ids = []
    for gore_i in range(4):
        columns = (gore_i * 8 + np.arange(9)) % HOLE_STATIONS
        three = np.asarray(
            [
                np.column_stack((ring[columns], np.full(9, z)))
                for ring, z in zip(full, heights)
            ]
        )
        two = _fabric_unfold_gore(three)
        shift = [2.6 + (side > 0) * 1.0 + gore_i * 0.2, 0.35]
        ids = _add_vertex(
            arrays, three.reshape(-1, 3), two.reshape(-1, 2) * 0.001 + shift
        ).reshape(5, 9)
        for k in range(4):
            for col in range(8):
                faces.append(
                    [
                        int(ids[k, col]),
                        int(ids[k, col + 1]),
                        int(ids[k + 1, col + 1]),
                        int(ids[k + 1, col]),
                    ]
                )
                roles.append(1)
        for col in range(8):
            springs.append((int(hole_ids[columns[col]]), int(ids[0, col])))
        all_ids.append(ids)
    return all_ids


def _append_tip_wedges(arrays, faces, roles, springs, side, full, heights, all_ids):
    ring = np.asarray(full[-1])
    center = ring.mean(axis=0)
    tip_z = 248.67
    wedges = []
    for gore_i, gore in enumerate(all_ids):
        columns = (gore_i * 8 + np.arange(9)) % HOLE_STATIONS
        corner = ring[columns]
        height = tip_z - heights[-1]
        radius = np.sqrt(np.sum((corner - center) ** 2, axis=1) + height**2)
        edge = np.linalg.norm(np.diff(corner, axis=0), axis=1)
        cosine = (radius[:-1] ** 2 + radius[1:] ** 2 - edge**2) / (
            2 * radius[:-1] * radius[1:]
        )
        if np.any(abs(cosine) > 1 + 1e-7):
            raise ValueError("true source tip wedge is not intrinsically unfoldable")
        theta = np.r_[0.0, np.cumsum(np.arccos(np.clip(cosine, -1, 1)))]
        flat = np.column_stack((radius * np.cos(theta), radius * np.sin(theta)))
        shift = [4.5 + (side > 0) * 1 + gore_i * 0.15, 0.65]
        uv = np.vstack((flat, [[0.0, 0.0]])) * 0.001 + shift
        xyz = np.vstack(
            (
                np.column_stack((corner, np.full(9, heights[-1]))),
                [[center[0], center[1], tip_z]],
            )
        )
        wedge = _add_vertex(arrays, xyz, uv)
        wedges.append(wedge)
        for col in range(8):
            faces.append([int(wedge[-1]), int(wedge[col]), int(wedge[col + 1])])
            roles.append(1)
            springs.append((int(gore[-1, col]), int(wedge[col])))
    for k, wedge in enumerate(wedges):
        successor = wedges[(k + 1) % 4]
        springs.append((int(wedge[-2]), int(successor[0])))
        springs.append((int(wedge[-1]), int(successor[-1])))


def _append_bridge(arrays, faces, roles, springs, hole_ids, side, rings):
    """Use source-derived four gores and four fitted tip darts per side."""
    arch = 0.52 * rings[1] + 0.48 * rings[0]
    full = [rings[0], arch, *rings[1:]]
    heights = (230.0, 240.0, 230.0, 235.0, 245.0)
    all_ids = _append_side_gores(
        arrays, faces, roles, springs, hole_ids, side, full, heights
    )
    for k, gore in enumerate(all_ids):
        follower = all_ids[(k + 1) % 4]
        springs.extend((int(a), int(b)) for a, b in zip(gore[:, -1], follower[:, 0]))
    _append_tip_wedges(arrays, faces, roles, springs, side, full, heights, all_ids)
    return {
        "side": "L" if side < 0 else "R",
        "gore_panels": 4,
        "vertices_per_gore": 45,
        "tip_wedge_panels": 4,
        "vertices_per_wedge": 10,
        "source_high_lobe_real_z_sections_mm": list(SOURCE_LEVELS_MM),
        "intermediate_arch_is_a_research_synthetic_preposition": True,
    }


def generate(stage, source, output):
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("refuse to overwrite earlier research output")
    arrays, mesh = _load_inputs(stage, source)
    faces, roles = _split_r3_faces(arrays)
    springs = [
        tuple(map(int, edge)) for edge in arrays["original_sewing_spring_vertex_pairs"]
    ]
    orig = arrays["initial_3d_prepositioned_vertices_m"]
    cap_xy = orig[CAP_BEGIN:CAP_CENTER, :2] * 1000
    hole_xy = [_make_hole(x) for x in HOLE_CENTERS_X]
    min_bridge = min(
        Polygon(cap_xy).exterior.distance(Polygon(h).exterior) for h in hole_xy
    )
    if min_bridge < SEAM_ALLOWANCE_REQUIREMENT_MM:
        raise ValueError("not enough shoulder/ear-hole 2D seam allowance")
    shift = (
        arrays["true_independent_flat_2d_rest_xy_m"][CAP_BEGIN] - orig[CAP_BEGIN, :2]
    )
    hole_ids = [
        _add_vertex(
            arrays,
            np.column_stack((ring, np.full(HOLE_STATIONS, 230.0))),
            ring * 0.001 + shift,
        )
        for ring in hole_xy
    ]
    # _add_vertex must occur before remeshing to build the exact hole index map.
    crown, outer_clearance, hole_clearance = _cap_with_two_real_openings(
        arrays, hole_xy, len(orig)
    )
    faces.extend(crown)
    roles.extend([1] * len(crown))
    panels = []
    for side, ids in zip((-1, 1), hole_ids):
        target = [
            _resample_source_loop(_source_loop(mesh, z, side), HOLE_STATIONS)
            for z in SOURCE_LEVELS_MM
        ]
        panels.append(
            _append_bridge(
                arrays, faces, roles, springs, ids, side, [hole_xy[(side > 0)], *target]
            )
        )
    xyz = arrays["initial_3d_prepositioned_vertices_m"]
    rest = arrays["true_independent_flat_2d_rest_xy_m"]
    spring_arr = np.asarray(springs, dtype=np.int32)
    lengths = np.asarray([len(p) for p in faces], dtype=np.int32)
    ids = np.asarray([v for face in faces for v in face], dtype=np.int32)
    mat = np.asarray(roles, dtype=np.int8)
    if (
        xyz.shape != (3139, 3)
        or rest.shape != (3139, 2)
        or spring_arr.shape != (1170, 2)
        or len(faces) != 2378
    ):
        raise ValueError("R5 research bridge source vertex / sewing topology drifted")
    if len(set(map(tuple, map(sorted, springs)))) != len(springs):
        raise ValueError("R5 duplicated sewing constraints")
    if not np.array_equal(
        spring_arr[:986], arrays["original_sewing_spring_vertex_pairs"]
    ):
        raise ValueError("R3 986 source sewing connections were modified")
    if not np.isfinite(xyz).all() or not np.isfinite(rest).all():
        raise ValueError("R5 source true mesh rest is nonfinite")
    output.mkdir(parents=True, exist_ok=True)
    path = output / "R5_SOURCE_TWO_SIDE_LOBES_2D_REST_3D_PREPOSITION_NOT_SIMULATED.npz"
    np.savez_compressed(
        path,
        initial_3d_prepositioned_vertices_m=xyz,
        true_independent_flat_2d_rest_xy_m=rest,
        face_lengths=lengths,
        face_vertex_ids=ids,
        face_material_roles=mat,
        original_sewing_spring_vertex_pairs=spring_arr,
    )
    report = {
        "schema": "stage6-R5-source-two-side-lobe-open-headcap-40pieces-v1",
        "input_R3_snapshot_sha256": _sha(stage),
        "input_true_Stage6_source_SHA256": _sha(source),
        "source_R3_original_vertices_unchanged": bool(np.array_equal(xyz[:2635], orig)),
        "total_research_panels": R5_PANELS,
        "source_true_side_lobe_sections_mm": list(SOURCE_LEVELS_MM),
        "original_940_pairwise_2d_seams_still_need_independent_audit": True,
        "sewing_springs": len(springs),
        "R3_986_source_sewing_springs_identical": True,
        "crown_two_new_holes_clearance_to_outer_mm": outer_clearance,
        "crown_hole_to_hole_clearance_mm": hole_clearance,
        "research_min_double_seam_allowance_mm": SEAM_ALLOWANCE_REQUIREMENT_MM,
        "added_original_real_eared_visual_meshes_sewn": 0,
        "added_original_high_source_lobe_surrogate_fabric_panels": 16,
        "new_R5_ear_attachment_method": "source_guided_8_narrow_gores_8_tip_dart_wedges_2_new_headcap_holes",
        "new_head_cap_hole_is_actual_source_cut": False,
        "source_real_3d_to_2d_ear_root_intrinsic_ABF": False,
        "true_stuffing_self_collision_tested": False,
        "Blender_R5_real_Cloth_simulation_run": False,
        "factory_approved_cut_patterns": 0,
        "side_lobe_panels": panels,
        "R5_stage_npz_SHA256": _sha(path),
    }
    (output / "R5_RESEARCH_TOPOLOGY_QA.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", required=True, type=Path)
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    print(json.dumps(generate(a.stage, a.source, a.out), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
