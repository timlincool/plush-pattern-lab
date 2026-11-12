"""Visual review atlas of 12 slitted Stage6 source disks, not paper patterns."""

from __future__ import annotations

from collections import defaultdict

from plush_pattern_lab.validation.stage6_ear_slit_lscm import (
    SCHEMA,
    _oriented_disk_boundary_edges,
)


def _source_boundary(seam):
    # A topological disk must have exactly one closed boundary.
    triangles = seam["cut_disk_original_source_triangle_indices"]
    from numpy import asarray

    edges = _oriented_disk_boundary_edges(asarray(triangles))
    adjacency = defaultdict(list)
    for a, b in edges:
        adjacency[int(a)].append(int(b))
        adjacency[int(b)].append(int(a))
    if not adjacency or any(len(nodes) != 2 for nodes in adjacency.values()):
        raise ValueError("source 2D pattern drawing has branched boundary")
    loop = [min(adjacency)]
    while True:
        previous = loop[-2] if len(loop) > 1 else None
        nxt = min(i for i in adjacency[loop[-1]] if i != previous)
        if nxt == loop[0]:
            break
        if nxt in loop or len(loop) > len(adjacency):
            raise ValueError("source disk border is not one simple loop")
        loop.append(nxt)
    if len(loop) != len(adjacency):
        raise ValueError("source disk has multiple boundary components")
    return loop


def _geometry_preview(candidate, left, top):
    uv = candidate["real_2d_research_coordinates_mm"]
    boundary = _source_boundary(candidate)
    minx = min(p[0] for p in uv)
    maxx = max(p[0] for p in uv)
    miny = min(p[1] for p in uv)
    maxy = max(p[1] for p in uv)
    size = 6.0
    cx = left + 255
    cy = top + 150

    def position(index):
        x, y = uv[index]
        return cx + size * (x - (minx + maxx) / 2), cy - size * (
            y - (miny + maxy) / 2
        )

    contour = " ".join(
        f"{x:.2f},{y:.2f}" for x, y in map(position, boundary)
    )
    return [
        f'<polygon points="{contour}" fill="#e9f1f6" '
        'stroke="#2c5877" stroke-width="1.7"/>',
    ]


def _render_one(candidate, i):
    left, top = 12 + (i % 3) * 508, 89 + (i // 3) * 313
    strain = candidate["uniform_scale_normalized_edge_diagnostics"]
    seam = candidate["true_source_seam_3d_vs_lscm_2d_pairing"]
    face = candidate["original_source_planar_face_geometry_diagnostics"]
    gap = candidate["two_seams_2d_6mm_allowance_vertex_screen"]
    result = [
        f'<rect x="{left}" y="{top}" width="497" height="304" rx="9" '
        'fill="white" stroke="#cbd5e1"/>',
        f'<text x="{left + 13}" y="{top + 25}" '
        'font-size="15" font-family="sans-serif" fill="#1d3345">'
        f'{candidate["source_variant"]} / {candidate["original_source_side"]} '
        f'/ {candidate["source_slit_direction"]}</text>',
        *_geometry_preview(candidate, left, top),
        f'<text x="{left + 13}" y="{top + 249}" '
        'font-size="12" font-family="sans-serif" fill="#8d3530">'
        f'P95 edge distortion: {100 * strain["scaled_2d_p95_abs_edge_relative_error"]:.1f}%'
        f' | matched seam 2D mismatch: '
        f'{100 * seam["scaled_planar_2d_two_sides_length_mismatch_fraction_of_source_3d"]:.1f}%</text>',
        f'<text x="{left + 13}" y="{top + 274}" '
        'font-size="11" font-family="sans-serif" fill="#415c72">'
        f'2D min lower/upper vertex gap: '
        f'{gap["scaled_2d_min_sampled_lower_upper_vertex_gap_mm"]:.2f}mm'
        f' | flipped: {face["reversed_or_collapsed_triangle_count"]}'
        f' | overlap pairs: {face["overlapping_positive_area_triangle_pair_count"]}'
        '</text>',
    ]
    return result


def render_source_slit_lscm_atlas(report):
    """Show all 12 predefined variants without cherry-picked optimizations."""
    options = report.get("candidate_2d_research_disks", [])
    if (
        report.get("schema") != SCHEMA
        or len(options) != 12
        or report.get("factory_cutting_patterns_approved") != 0
    ):
        raise ValueError("twelve source-verified non-approved 2D trials required")
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1540" height="1380" '
        'viewBox="0 0 1540 1380">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<text x="20" y="36" font-family="sans-serif" font-size="22" '
        'fill="#172e43">Stage6 TRUE source annulus side-slit to 2D LSCM research</text>',
        '<text x="20" y="60" font-family="sans-serif" font-size="14" '
        'fill="#aa3b35">NO CUTTING PATTERNS / NO FABRIC REST SHAPE / NO APPROVAL</text>',
    ]
    for i, candidate in enumerate(options):
        out.extend(_render_one(candidate, i))
    out.extend(
        [
            '<text x="20" y="1370" font-family="sans-serif" font-size="12" '
            'fill="#354e63">6 px/mm after documented isotropic normalization. '
            'The lower + upper original-source ring and both slit copies form '
            'ONE original-source topological disk boundary.</text>',
            "</svg>",
        ]
    )
    return "\n".join(out) + "\n"
