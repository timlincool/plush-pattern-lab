"""Matched-material R3 research body band from pinned true Stage6 contours.

This script constructs 24 independently sewable trial panels with strict 2D
length correspondence. It never asserts cloth physics or factory acceptance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import cKDTree
from shapely import constrained_delaunay_triangles
from shapely.geometry import LineString, Polygon

SOURCE_SHA = "5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd"
LOWER_SHA = "1427c7bdfc376431378e516f90540cb56e3b9adfb4695a3d5858c584041eea59"
R2_STAGE_SHA = "14d8846692e4d60f2576d4784d02f42b64d5689be91ce2d82e5d9c1ee35fe479"
R2_UPPER_SHA = "1df8c0b791e54ef9c60e5535948aea6896c2545bc69841abbc37c34bd892e787"
Z = (60.0, 70.0, 80.0, 90.0, 100.0)
BAND_BLEND = (None, 0.29, 0.47, 0.48, 0.56)
MIN_YOKE_CLEARANCE_MM = 12.7
EPS = 1e-7


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def strict_input(path, sha):
    p = Path(path)
    if not p.is_file() or p.is_symlink() or digest(p) != sha:
        raise ValueError(f"source not pinned, regular or unchanged: {p.name}")
    return p


def pieces():
    names = [f"BAND-{i}" for i in range(1, 5)]
    sizes = [34] * 4
    names.extend(f"TORSO-{i}" for i in range(1, 5))
    sizes.extend([68] * 4)
    names.extend(f"HEADNECK-{i}" for i in range(1, 5))
    sizes.extend([85] * 4)
    names.extend(["SHOULDER-CAP-TRIAL", "HEAD-TOP-CAP-TRIAL", "COLLAR-TRIAL", "YOKE-01"])
    sizes.extend([128, 65, 130, 320])
    for hoof in ("FL", "FR", "RL", "RR"):
        names.extend((f"LEG-{hoof}", f"SOLE-{hoof}"))
        sizes.extend((195, 65))
    assert sum(sizes) == 2431 and len(names) == 24
    at = 0
    out = {}
    for name, size in zip(names, sizes):
        out[name] = np.arange(at, at + size)
        at += size
    return out


def largest_source_loop(mesh, z):
    section = mesh.section(plane_origin=(0, 0, z), plane_normal=(0, 0, 1))
    if section is None:
        raise ValueError("missing original source slice")
    loops = [Polygon(p[:, :2]) for p in section.discrete if
             len(p) > 20 and np.linalg.norm(p[0] - p[-1]) < 1e-4]
    valid = [p for p in loops if p.is_valid and p.area > 100]
    if len(valid) != 1:
        raise ValueError(f"expected single continuous original body at {z}: {len(valid)}")
    return valid[0]


def radial_fit(old, poly):
    original = np.asarray(old, dtype=float)
    if original.shape != (64, 2) or not Polygon(original).is_valid:
        raise ValueError("bad original 64-piece station ring")
    center = np.asarray(poly.centroid.coords[0])
    old_center = original.mean(axis=0)
    fitted = []
    for point in original:
        direction = point - old_center
        direction /= np.linalg.norm(direction)
        hit = poly.exterior.intersection(LineString((center, center + direction * 500)))
        geoms = list(hit.geoms) if hasattr(hit, "geoms") else [hit]
        candidates = []
        for geom in geoms:
            if geom.geom_type in {"LineString", "Point"}:
                candidates.extend(np.asarray(geom.coords).reshape(-1, 2))
        selected = [p for p in candidates if np.dot(p - center, direction) > EPS]
        if not selected:
            raise ValueError("non radial addressable true Stage6 source outline")
        fitted.append(max(selected, key=lambda p: float(np.dot(p - center, direction))))
    result = np.asarray(fitted)
    if not Polygon(result).is_valid:
        raise ValueError("radial resampling self-intersects")
    return result


def clearance(ring, holes):
    polygon = Polygon(ring)
    if not polygon.is_valid:
        return -1.0
    if any(not polygon.contains(p) for p in holes):
        return -1.0
    return float(min(polygon.exterior.distance(p.exterior) for p in holes))


def safe_yoke_blend(old, target, holes):
    if clearance(old, holes) < MIN_YOKE_CLEARANCE_MM:
        raise ValueError("original yoke bridge already unsafe")
    lo, hi = 0.0, 1.0
    for _ in range(40):
        middle = (lo + hi) / 2
        trial = old * (1 - middle) + target * middle
        if clearance(trial, holes) < MIN_YOKE_CLEARANCE_MM + 0.25:
            hi = middle
        else:
            lo = middle
    fraction = min(lo, 0.27)
    result = old * (1 - fraction) + target * fraction
    if clearance(result, holes) < MIN_YOKE_CLEARANCE_MM:
        raise ValueError("yoke double-seam clearance fails")
    return result, float(fraction)


def sample_rings(mesh, old_yoke, old_top, holes):
    results, diagnostics = [], []
    for z, alpha in zip(Z, BAND_BLEND):
        source = largest_source_loop(mesh, z)
        base = old_yoke * (1 - (z - 60) / 40) + old_top * ((z - 60) / 40)
        target = radial_fit(base, source)
        if z == 60:
            ring, alpha = safe_yoke_blend(old_yoke, target, holes)
        else:
            ring = base * (1 - alpha) + target * alpha
        p = Polygon(ring)
        if not p.is_valid or p.area <= 0 or np.any(~np.isfinite(ring)):
            raise ValueError("invalid R3 true-section blend ring")
        iou_old = Polygon(base).intersection(source).area / Polygon(base).union(source).area
        iou_new = p.intersection(source).area / p.union(source).area
        if iou_new <= iou_old + 0.02:
            raise ValueError("R3 band source IoU did not improve")
        results.append(ring)
        diagnostics.append({"z_mm":z,"blend":float(alpha),"source_area_mm2":float(source.area),
                            "R2_baseline_area_mm2":float(Polygon(base).area),
                            "R3_area_mm2":float(p.area),"R2_section_iou":float(iou_old),
                            "R3_section_iou":float(iou_new)})
    rings = np.asarray(results)
    if clearance(rings[0], holes) < MIN_YOKE_CLEARANCE_MM:
        raise ValueError("hoof hole yoke clearance broken")
    return rings, diagnostics


def _validate_yoke_cdt_edges(faces):
    counts = Counter(
        tuple(sorted((a, b)))
        for face in faces
        for a, b in zip(face, (face[1], face[2], face[0]))
    )
    boundary = {edge for edge, count in counts.items() if count == 1}
    expected = {
        tuple(sorted((start + i, start + (i + 1) % 64)))
        for start in (0, 64, 128, 192, 256)
        for i in range(64)
    }
    if boundary != expected or set(counts.values()) != {1, 2}:
        raise ValueError("original 320 hoof and outer boundary edges not preserved")


def _triangles_from_constrained_geometry(geometry, xy):
    nearest = cKDTree(xy)
    result = []
    for triangle in geometry.geoms:
        coords = np.asarray(triangle.exterior.coords)[:3]
        distance, indices = nearest.query(coords)
        if distance.max() > 1e-6 or len(set(indices)) != 3:
            raise ValueError("constrained triangulation inserted a new source point")
        result.append(tuple(int(index) for index in indices))
    return result


def yoke_triangulation(xy):
    outer = Polygon(xy[:64])
    holes = [Polygon(xy[i : i + 64]) for i in (64, 128, 192, 256)]
    if any(not outer.contains(hole) for hole in holes):
        raise ValueError("hoof holes cut through the 2D abdomen boundary")
    shape = Polygon(xy[:64], [xy[i : i + 64] for i in (64, 128, 192, 256)])
    if not shape.is_valid:
        raise ValueError("four-hole source fabric polygon invalid")
    faces = _triangles_from_constrained_geometry(constrained_delaunay_triangles(shape), xy)
    if len(faces) != 326:
        raise ValueError("original source 4-hoof yoke triangle count changed")
    _validate_yoke_cdt_edges(faces)
    return faces


def quarter_widths(rings):
    widths = np.zeros((len(rings),4))
    for k,ring in enumerate(rings):
        for i in range(4):
            arc=ring[(i*16+np.arange(17))%64]
            widths[k,i] = np.linalg.norm(np.diff(arc,axis=0),axis=1).sum()
    return widths


def gore_vertices(rings, heights, piece, i):
    """Flatten ring arcs with *one shared meridian net-length per transition*.

    Each band's left and right 2D sides have exactly the same vertical
    meridian length L, as do the neighboring pieces. The horizontal 2D
    netline segments exactly match the true XY ring chords by construction.
    This is a constrained 2D proposal, not a strain-free cloth flattening.
    """
    heights = np.asarray(heights, dtype=float)
    rings = np.asarray(rings, dtype=float)
    widths = quarter_widths(rings)
    bounds = np.stack(
        [np.column_stack((ring[[0, 16, 32, 48]], np.full(4, z)))
         for ring, z in zip(rings, heights)], axis=0
    )
    source_side = np.linalg.norm(np.diff(bounds, axis=0), axis=2)
    common_meridians = np.maximum(
        source_side.max(axis=1),
        0.5 * np.max(abs(np.diff(widths, axis=0)), axis=1),
    ) + 0.2
    half_shift = np.diff(widths[:, i]) * 0.5
    increments = np.sqrt(common_meridians**2 - half_shift**2)
    if not np.isfinite(increments).all() or (increments <= 0).any():
        raise ValueError("no possible shared 2D netline meridian")
    ys = np.r_[0.0, np.cumsum(increments)]
    xyz = []
    uv = []
    for k, (ring, z) in enumerate(zip(rings, heights)):
        arc = ring[(i * 16 + np.arange(17)) % 64]
        steps = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(arc, axis=0), axis=1))]
        x = steps - steps[-1] * 0.5
        xyz.append(np.column_stack((arc, np.full(17, z))))
        uv.append(np.column_stack((x, np.full(17, ys[k]))))
    return np.concatenate(xyz) / 1000, np.concatenate(uv) / 1000


def rework_torso(old_r2, new_ring100, initial, rest, item_ids):
    body=np.asarray(old_r2["body_synthetic_rings_xy_mm"],float).copy()
    body[0] = new_ring100
    for i in range(4):
        name = f"TORSO-{i + 1}"
        idx = item_ids[name]
        pos,pattern=gore_vertices(body,old_r2["body_rings_z_mm"],name,i)
        if pos.shape!=(68,3) or pattern.shape!=(68,2):
            raise ValueError("torso final vertices topology unexpectedly changed")
        offset=rest[idx[0]]-pattern[0]  # preserve source material layout position at first vertex
        initial[idx] = pos
        rest[idx] = pattern + offset
    return body


def _preserve_unmodified_faces(old_lengths, old_ids, roles, band_ids, yoke_ids):
    unaffected = []
    colors = []
    cursor = 0
    all_band = set(int(v) for part in band_ids for v in part)
    yoke = set(int(v) for v in yoke_ids)
    for count, role in zip(old_lengths, roles):
        face = tuple(int(v) for v in old_ids[cursor : cursor + int(count)])
        cursor += int(count)
        if set(face) <= all_band or set(face) <= yoke:
            continue
        unaffected.append(face)
        colors.append(int(role))
    if cursor != len(old_ids):
        raise ValueError("old R2 triangle/quad index stream corrupted")
    return unaffected, colors


def _rebuild_band_faces(band_ids, extra_rows):
    faces = []
    for index, part in enumerate(band_ids):
        layers = [part[:17], *extra_rows[index], part[17:]]
        for lower, upper in zip(layers, layers[1:]):
            for offset in range(16):
                faces.append(
                    (
                        int(lower[offset]),
                        int(upper[offset]),
                        int(upper[offset + 1]),
                        int(lower[offset + 1]),
                    )
                )
    return faces


def rebuild_faces(old_lengths, old_ids, roles, band_ids, yoke_ids, rows, yoke_faces):
    faces, colors = _preserve_unmodified_faces(
        old_lengths, old_ids, roles, band_ids, yoke_ids
    )
    new_faces = _rebuild_band_faces(band_ids, rows)
    faces.extend(new_faces)
    colors.extend([0] * len(new_faces))
    faces.extend(tuple(int(yoke_ids[i]) for i in face) for face in yoke_faces)
    colors.extend([0] * len(yoke_faces))
    lengths = np.asarray([len(face) for face in faces], dtype=np.int32)
    indices = np.asarray([index for face in faces for index in face], dtype=np.int32)
    return lengths, indices, np.asarray(colors, dtype=np.int8)


def _append_band_stations(initial, rest, rings):
    points = initial.tolist()
    material = rest.tolist()
    intermediate_ids = [[] for _ in range(4)]
    for level in range(1, 4):
        for quadrant in range(4):
            arc = rings[level][(quadrant * 16 + np.arange(17)) % 64]
            xyz = np.column_stack((arc, np.full(17, Z[level]))) / 1000
            for vertex in xyz:
                intermediate_ids[quadrant].append(len(points))
                points.append(vertex.tolist())
                material.append([0, 0])
    xyz_array = np.asarray(points, dtype=float)
    uv_array = np.asarray(material, dtype=float)
    rows = [
        [np.asarray(ids[k * 17 : (k + 1) * 17]) for k in range(3)]
        for ids in intermediate_ids
    ]
    return xyz_array, uv_array, rows


def _populate_band_material(xyz, uv, ids, rings, rows, prior_uv):
    for quadrant in range(4):
        label = f"BAND-{quadrant + 1}"
        part = ids[label]
        geometry, material = gore_vertices(rings, Z, label, quadrant)
        full = np.concatenate((part[:17], *rows[quadrant], part[17:]))
        shift = np.mean(prior_uv[part[:17]] - material[:17], axis=0)
        xyz[full] = geometry
        uv[full] = material + shift


def _append_band_side_springs(old_pairs, rows):
    new = [
        tuple(sorted((int(rows[i][k][16]), int(rows[(i + 1) % 4][k][0]))))
        for k in range(3)
        for i in range(4)
    ]
    paired = np.vstack((old_pairs, np.asarray(new, dtype=np.int32)))
    if len(new) != 12 or len({tuple(edge) for edge in paired}) != len(paired):
        raise ValueError("R3 added seam springs are missing or duplicated")
    return paired


def append_band_internal(initial, rest, old_pairs, ids, rings, trial):
    xyz, uv, rows = _append_band_stations(initial, rest, rings)
    _populate_band_material(xyz, uv, ids, rings, rows, rest)
    return xyz, uv, _append_band_side_springs(old_pairs, rows), rows


def physical_material_checks(init, rest, flens, fids, pairs):
    at = 0
    edges = set()
    for length in flens:
        face = fids[at:at + int(length)]
        at += int(length)
        for a,b in zip(face,np.roll(face,-1)):
            edges.add(tuple(sorted((int(a),int(b)))))
    edges=np.asarray(sorted(edges),int)
    planar=np.linalg.norm(rest[edges[:,0]]-rest[edges[:,1]],axis=1)
    physical=np.linalg.norm(init[edges[:,0]]-init[edges[:,1]],axis=1)
    valid=planar>1e-9
    strain=abs(physical[valid]/planar[valid]-1)*100
    gaps=np.linalg.norm(init[pairs[:,0]]-init[pairs[:,1]],axis=1)*1000
    return {"rest_edge_strain_p95_percent":float(np.percentile(strain,95)),
            "rest_edge_strain_max_percent":float(np.max(strain)),
            "initial_seam_mean_mm":float(gaps.mean()),"initial_seam_max_mm":float(gaps.max()),
            "undirected_surface_edges":len(edges),"invalid_zero_length_material_edges":int((~valid).sum())}


def _load_pinned_experiment(source, lower_file, upper_file, old_stage):
    for path, expected in (
        (source, SOURCE_SHA),
        (lower_file, LOWER_SHA),
        (upper_file, R2_UPPER_SHA),
        (old_stage, R2_STAGE_SHA),
    ):
        strict_input(path, expected)
    lower = json.loads(Path(lower_file).read_text(encoding="utf8"))
    upper = json.loads(Path(upper_file).read_text(encoding="utf8"))
    trial = next(
        part for part in upper["options"] if part["name"] == "B_integrated_neck_port"
    )
    with np.load(old_stage, allow_pickle=False) as snap:
        arrays = {
            key: snap[key].copy()
            for key in (
                "initial_3d_prepositioned_vertices_m",
                "true_independent_flat_2d_rest_xy_m",
                "face_lengths",
                "face_vertex_ids",
                "face_material_roles",
                "original_sewing_spring_vertex_pairs",
            )
        }
    return lower, trial, arrays


def _source_ring_and_yoke(mesh, lower, trial):
    outer = np.asarray(lower["yoke"]["outer_stitch_xy_mm"], dtype=float)
    holes = [
        np.asarray(
            lower["yoke"]["source_hoof_holes_stitch_xy_mm"][k], dtype=float
        )[::8]
        for k in ("FL", "FR", "RL", "RR")
    ]
    rings, diagnostics = sample_rings(
        mesh,
        outer,
        np.asarray(trial["body_synthetic_rings_xy_mm"][0]),
        [Polygon(p) for p in holes],
    )
    xy = np.vstack((rings[0], *holes))
    if xy.shape != (320, 2):
        raise ValueError("original four source hoof openings changed")
    return outer, rings, yoke_triangulation(xy), diagnostics


def _rebuild(source, lower, trial, old):
    mesh = trimesh.load(source, force="mesh")
    outer, rings, yoke_faces, diagnostics = _source_ring_and_yoke(
        mesh, lower, trial
    )
    ids = pieces()
    init = old["initial_3d_prepositioned_vertices_m"].copy()
    rest = old["true_independent_flat_2d_rest_xy_m"].copy()
    yoke_ids = ids["YOKE-01"]
    init[yoke_ids[:64], :2] = rings[0] / 1000
    rest[yoke_ids[:64]] += (rings[0] - outer) / 1000
    init, rest, springs, rows = append_band_internal(
        init, rest, old["original_sewing_spring_vertex_pairs"], ids, rings, trial
    )
    rework_torso(trial, rings[-1], init, rest, ids)
    lengths, indices, roles = rebuild_faces(
        old["face_lengths"],
        old["face_vertex_ids"],
        old["face_material_roles"],
        [ids[f"BAND-{i}"] for i in range(1, 5)],
        yoke_ids,
        rows,
        yoke_faces,
    )
    return (init, rest, springs, lengths, indices, roles), rings, diagnostics, yoke_faces


def _create_report(trial_arrays, rings, diagnostics, yoke_faces, lower):
    init, rest, springs, lengths, indices, roles = trial_arrays
    if init.shape != (2635, 3) or rest.shape != (2635, 2):
        raise ValueError("revised Stage6 24-piece vertex topology changed")
    if springs.shape != (986, 2) or len(lengths) != 1990:
        raise ValueError("sewing-spring or surface count changed")
    if int(sum(lengths)) != len(indices) or len(roles) != len(lengths):
        raise ValueError("face lengths or material roles inconsistent")
    if set(lengths) != {3, 4}:
        raise ValueError("not the expected 3/4-gon research cloth")
    meta = physical_material_checks(init, rest, lengths, indices, springs)
    meta.update(
        schema="stage6-r3-matched-material-2d-body-5-station-trial-v1",
        R3_pieces=24,
        R3_derived_body_band_layers=5,
        R3_main_body_panels_changed=9,
        R2_original_springs_preserved=974,
        R3_new_band_side_springs=12,
        R3_springs_total=986,
        R2_original_vertices=2431,
        R3_source_vertices=len(init),
        R3_faces=len(lengths),
        original_hoof_stitch_holes_unchanged=True,
        original_hoof_ring_edges_per_hole_source=512,
        new_yoke_cdt_triangles=len(yoke_faces),
        new_yoke_outer_min_bridge_mm=clearance(
            rings[0],
            [
                Polygon(np.asarray(lower["yoke"]["source_hoof_holes_stitch_xy_mm"][key])[::8])
                for key in ("FL", "FR", "RL", "RR")
            ],
        ),
        lower_body_Z_stations_mm=list(Z),
        constrained_ring_blends=list(BAND_BLEND[1:]),
        source_station_2d_iou=diagnostics,
        true_3d_source_used_only_as_geometric_reference=True,
        Blender_Cloth_R3_executed=False,
        physical_filling_or_selfcollision_proven=False,
        factory_cut_patterns_approved=0,
        P3="in_progress",
        P4="not_started",
    )
    return meta


def _save_reproducible_staging(output, arrays, meta):
    init, rest, springs, lengths, indices, roles = arrays
    root = Path(output)
    if root.exists() and (root.is_symlink() or any(root.iterdir())):
        raise ValueError("refuse to overwrite immutable research evidence")
    root.mkdir(parents=True, exist_ok=True)
    npz = root / "R3_MATCHED_24_PIECE_2D_REST_AND_3D_PREPOSITION_NOT_SIMULATED.npz"
    np.savez_compressed(
        npz,
        initial_3d_prepositioned_vertices_m=init,
        true_independent_flat_2d_rest_xy_m=rest,
        face_lengths=lengths,
        face_vertex_ids=indices,
        face_material_roles=roles,
        original_sewing_spring_vertex_pairs=springs,
    )
    meta["R3_stage_npz_sha256"] = digest(npz)
    (root / "R3_2d_geometry_QA.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    triangles = []
    cursor = 0
    for length in lengths:
        face = indices[cursor:cursor + int(length)]
        triangles.extend(
            (int(face[0]), int(face[k]), int(face[k + 1]))
            for k in range(1, int(length) - 1)
        )
        cursor += int(length)
    trimesh.Trimesh(
        vertices=init, faces=np.asarray(triangles), process=False
    ).export(root / "R3_PREPOSITION_NOT_A_SEWN_TOY.glb")


def build(source, lower_file, upper_file, old_stage, output):
    lower, trial, previous = _load_pinned_experiment(
        source, lower_file, upper_file, old_stage
    )
    arrays, rings, diagnostics, yoke_faces = _rebuild(
        source, lower, trial, previous
    )
    meta = _create_report(arrays, rings, diagnostics, yoke_faces, lower)
    _save_reproducible_staging(output, arrays, meta)
    return meta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "lower", "upper", "stage", "out"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    report = build(args.source, args.lower, args.upper, args.stage, args.out)
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "source_station_2d_iou"},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()