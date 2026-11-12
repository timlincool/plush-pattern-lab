"""Visual sewing-graph of 18 EXISTING Stage6 surrogate pieces (not production)."""

from __future__ import annotations

from html import escape

SCHEMA = "stage6-18piece-panel-interface-research-assembly-v1"
GROUPS = (
    ("TOP-CAP-TRIAL",),
    ("UPPER-1", "UPPER-2", "UPPER-3", "UPPER-4"),
    ("BAND-1", "BAND-2", "BAND-3", "BAND-4"),
    ("YOKE-01",),
    ("LEG-FL", "LEG-FR", "LEG-RL", "LEG-RR"),
    ("SOLE-FL", "SOLE-FR", "SOLE-RL", "SOLE-RR"),
)


def _locations():
    coords = {}
    for row, group in enumerate(GROUPS):
        width, gap = 190, 24
        total = len(group) * width + (len(group) - 1) * gap
        left = (920 - total) / 2
        for i, piece in enumerate(group):
            coords[piece] = (left + i * (width + gap), 111 + row * 111)
    return coords


def render_research_assembly_svg(graph):
    """Draw every piece and explain unresolved shape/fabric blockers."""
    if (
        graph.get("schema") != SCHEMA
        or len(graph.get("all_pieces", [])) != 18
        or len(graph.get("paired_stitch_interfaces", [])) != 32
        or graph.get("factory_cut_patterns_approved") != 0
    ):
        raise ValueError("source research graph not verified or factory state changed")
    coords = _locations()
    if {part["id"] for part in graph["all_pieces"]} != set(coords):
        raise ValueError("cannot draw a topology-mismatched 18-piece kit")
    result = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="920" height="840" '
        'viewBox="0 0 920 840">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<text x="24" y="34" font-family="sans-serif" font-size="21" '
        'fill="#1f3348">Stage6: 18-piece DIGITAL research sewing graph</text>',
        '<text x="24" y="57" font-family="sans-serif" font-size="12" '
        'fill="#a23d35">NOT original Stage6 appearance, NOT approved patterns, '
        "NOT sewn in fabric</text>",
    ]
    for edge in graph["paired_stitch_interfaces"]:
        left = edge["first"].split(".")[0]
        right = edge["second"].split(".")[0]
        if left == right:
            continue
        x0, y0 = coords[left]
        x1, y1 = coords[right]
        x0 += 95
        x1 += 95
        y0 += 35
        y1 += 35
        result.append(
            f'<path d="M{x0:.1f} {y0:.1f} L{x1:.1f} {y1:.1f}" '
            'stroke="#cad5e2" stroke-width="1.3" fill="none"/>'
        )
    for piece, (x, y) in coords.items():
        tone = "#e6eef7" if piece.startswith("UPPER") else "#fff"
        result.extend(
            [
                f'<rect x="{x:.1f}" y="{y:.1f}" width="190" height="66" rx="8" '
                f'fill="{tone}" stroke="#647e95" stroke-width="1.3"/>',
                f'<text x="{x + 95:.1f}" y="{y + 24:.1f}" '
                'font-family="sans-serif" font-size="15" '
                f'text-anchor="middle" fill="#213d55">{escape(piece)}</text>',
                f'<text x="{x + 95:.1f}" y="{y + 44:.1f}" '
                'font-family="sans-serif" font-size="10" '
                'text-anchor="middle" fill="#697989">research surrogate</text>',
            ]
        )
    result.extend(
        [
            '<text x="24" y="793" font-family="sans-serif" font-size="13" '
            'fill="#9d4239">Neck/head silhouette discrepancy, real rounded hoof, '
            "ears/clouds/tail/drops and fabric are UNVERIFIED.</text>",
            '<text x="24" y="814" font-family="sans-serif" font-size="11" '
            'fill="#465b71">32 numeric interface matches; 9 real-size A4 '
            "sheets; this graph is NOT evidence of physical sewing.</text>",
            "</svg>",
        ]
    )
    return "\n".join(result) + "\n"
