"""Full 24-piece Panel/Interface graph for the existing Stage6 split head/torso trials.

Reuses the verified lower 13 research panels. These are proposed 2D seams,
not flattened source triangles, sewability evidence, or industrial patterns.
The separate-head option has a *manual surface attachment*, not a matched
machine-sewing edge. Do not silently promote it to a numerical seam.
"""

from __future__ import annotations

from collections import deque


from plush_pattern_lab.patterns.stage6_research_panel_interface import (
    SOURCE_SHA,
    _hoof_seams,
    _insert_pair,
    _open_segments,
    _outer_band_seams,
    _part_inventory,
    _ring_segments,
    _station_segments,
)
from plush_pattern_lab.validation.stage6_lower_mother_toile_qc import (
    inspect_source_lower_toile,
)
from plush_pattern_lab.validation.stage6_split_volume_toile_qc import (
    audit_separated_stage6_toile,
)

SCHEMA = "stage6-split-head-torso-24piece-panel-interface-trial-v1"
OPTIONS = ("A_separate_stuffed_head", "B_integrated_neck_port")
RESEARCH_SOURCE = "new_envelope_surrogate_not_original_stage6_cut_edge"


def _inventory(name):
    lower = [
        dict(part)
        for part in _part_inventory()
        if part["id"] == "YOKE-01"
        or part["id"].startswith(("LEG-", "SOLE-", "BAND-"))
    ]
    if len(lower) != 13:
        raise ValueError("source-hoof lower panel inventory changed")
    roles = (
        [(f"TORSO-{i}", i) for i in range(1, 5)]
        + [(f"HEADNECK-{i}", i + 4) for i in range(1, 5)]
        + [("SHOULDER-CAP-TRIAL", 9), ("HEAD-TOP-CAP-TRIAL", 10)]
    )
    roles.append(
        ("CLOSED-NECK-BASE-TRIAL" if name == OPTIONS[0] else "COLLAR-TRIAL", 11)
    )
    upper = [
        {
            "id": label,
            "quantity": 1,
            "source_grade": RESEARCH_SOURCE,
            "paper": f"{name}/page-{page:02d}.svg",
        }
        for label, page in roles
    ]
    return lower + upper


def _pair(pairs, claimed, first, second, segments_a, segments_b, kind):
    _insert_pair(
        pairs,
        claimed,
        first,
        second,
        segments_a,
        segments_b,
        kind,
        RESEARCH_SOURCE,
    )


def _new_edges(trial, pairs, claimed):
    torso = trial["torso_gore_pieces"]
    head = trial["headneck_gore_pieces"]
    shoulder = trial["shoulder_cap"]
    top = trial["head_top_cap"]
    shoulder_segments = _ring_segments(shoulder["outer_stitch_xy_mm"])
    top_segments = _ring_segments(top["outer_stitch_xy_mm"])
    for i in range(4):
        nxt = (i + 1) % 4
        _pair(
            pairs,
            claimed,
            f"TORSO-{i + 1}.right",
            f"TORSO-{nxt + 1}.left",
            _open_segments(torso[i]["right_stitch_xy_mm"]),
            _open_segments(torso[nxt]["left_stitch_xy_mm"]),
            "torso_side",
        )
        _pair(
            pairs,
            claimed,
            f"TORSO-{i + 1}.top",
            f"SHOULDER-CAP-TRIAL.quarter-{i + 1}",
            _open_segments(torso[i]["upper_stitch_xy_mm"]),
            shoulder_segments[i * 16 : (i + 1) * 16],
            "torso_to_shoulder",
        )
        _pair(
            pairs,
            claimed,
            f"HEADNECK-{i + 1}.right",
            f"HEADNECK-{nxt + 1}.left",
            _open_segments(head[i]["right_stitch_xy_mm"]),
            _open_segments(head[nxt]["left_stitch_xy_mm"]),
            "headneck_side",
        )
        _pair(
            pairs,
            claimed,
            f"HEADNECK-{i + 1}.top",
            f"HEAD-TOP-CAP-TRIAL.quarter-{i + 1}",
            _open_segments(head[i]["upper_stitch_xy_mm"]),
            top_segments[i * 16 : (i + 1) * 16],
            "headneck_to_top_cap",
        )


def _lower_to_torso(lower, trial, pairs, claimed):
    for i, torso in enumerate(trial["torso_gore_pieces"]):
        band = lower["outer_quarter_bands"][i]
        if (
            torso["id"] != f"TORSO-{i + 1}"
            or torso["source_surrogate_16_ring_edge_ids"]
            != band["source_ring_edge_indices"]
        ):
            raise ValueError("lower 16-index band to torso source order changed")
        _pair(
            pairs,
            claimed,
            f"BAND-{i + 1}.top",
            f"TORSO-{i + 1}.bottom",
            _station_segments(band["stitch_bottom_station_x_mm"]),
            _open_segments(torso["lower_stitch_xy_mm"]),
            "original_lower_surrogate_band_to_torso",
        )


def _neck_A(trial, pairs, claimed):
    base = trial["head_bottom_cap_if_separate"]
    if base is None or trial["neck_collar_if_integrated"] is not None:
        raise ValueError("A separate head must have a closed neck base, no collar")
    segments = _ring_segments(base["outer_stitch_xy_mm"])
    for i, head in enumerate(trial["headneck_gore_pieces"]):
        _pair(
            pairs,
            claimed,
            f"HEADNECK-{i + 1}.bottom",
            f"CLOSED-NECK-BASE-TRIAL.quarter-{i + 1}",
            _open_segments(head["lower_stitch_xy_mm"]),
            segments[i * 16 : (i + 1) * 16],
            "separate_head_closed_base",
        )
    first, second = (
        "SHOULDER-CAP-TRIAL.surface-neck-guide",
        "CLOSED-NECK-BASE-TRIAL.outer-face",
    )
    if first in claimed or second in claimed:
        raise ValueError("manual surface guide was already claimed")
    claimed.update((first, second))
    pairs.append(
        {
            "id": f"S{len(pairs) + 1:02d}",
            "kind": "UNPROVEN_MANUAL_SURFACE_ATTACHMENT",
            "first": first,
            "second": second,
            "segment_count": None,
            "first_2d_netline_mm": None,
            "second_2d_netline_mm": None,
            "max_segment_disagreement_mm": None,
            "source_reference": RESEARCH_SOURCE,
            "numerical_netline_pair": False,
            "fabric_face_orientation_proven": False,
            "physical_stitching_proven": False,
        }
    )


def _neck_B(trial, pairs, claimed):
    collar = trial["neck_collar_if_integrated"]
    shoulder = trial["shoulder_cap"]
    if collar is None or trial["head_bottom_cap_if_separate"] is not None:
        raise ValueError("B open-neck trial must use an actual collar")
    inner = shoulder["upper_head_opening_stitch_xy_mm"]
    if len(inner) != 1:
        raise ValueError("B shoulder must expose one real study cut hole")
    port = _ring_segments(inner[0])
    stations = _station_segments(collar["lower_and_upper_stitch_station_x_mm"])
    if len(port) != 64 or len(stations) != 64:
        raise ValueError("B collar root lost its 64 indexed segments")
    _pair(
        pairs,
        claimed,
        "SHOULDER-CAP-TRIAL.inner-port",
        "COLLAR-TRIAL.bottom",
        port,
        stations,
        "shoulder_port_to_collar",
    )
    for i, head in enumerate(trial["headneck_gore_pieces"]):
        _pair(
            pairs,
            claimed,
            f"HEADNECK-{i + 1}.bottom",
            f"COLLAR-TRIAL.top-quarter-{i + 1}",
            _open_segments(head["lower_stitch_xy_mm"]),
            stations[i * 16 : (i + 1) * 16],
            "collar_top_to_headneck",
        )
    height = float(collar["height_mm"])
    _pair(
        pairs,
        claimed,
        "COLLAR-TRIAL.side-left",
        "COLLAR-TRIAL.side-right",
        [height],
        [height],
        "collar_self_close",
    )


def _components(parts, edges):
    nodes = {item["id"] for item in parts}
    if len(nodes) != len(parts):
        raise ValueError("duplicate paper panel IDs")
    adjacent = {name: set() for name in nodes}
    for edge in edges:
        a, b = edge["first"].split(".", 1)[0], edge["second"].split(".", 1)[0]
        if a not in nodes or b not in nodes:
            raise ValueError("unknown panel interface in assembly")
        adjacent[a].add(b)
        adjacent[b].add(a)
    remaining, components = set(nodes), []
    while remaining:
        start = min(remaining)
        seen, todo = set(), deque([start])
        while todo:
            node = todo.popleft()
            if node in seen:
                continue
            seen.add(node)
            todo.extend(sorted(adjacent[node] - seen))
        remaining -= seen
        components.append(sorted(seen))
    return sorted(components, key=lambda group: group[0])


def build_split_24piece_assembly_graphs(lower, study):
    """Recount all lower and split-volume interfaces independently.

    A has two numerical components joined only by an *unverified* hand seam;
    B has one numerically connected component. Neither proves a sewn sample.
    """
    low_qc = inspect_source_lower_toile(lower)
    if low_qc["factory_patterns_approved"] != 0:
        raise ValueError("industrial lower pattern was not audited")
    audit_separated_stage6_toile(lower, study)
    names = [item["name"] for item in study["options"]]
    if names != list(OPTIONS):
        raise ValueError("split two-volume alternative identity changed")
    result = {}
    for trial in study["options"]:
        name = trial["name"]
        pieces = _inventory(name)
        pairs, claimed = [], set()
        _hoof_seams(lower, pairs, claimed)
        _outer_band_seams(lower, pairs, claimed)
        _lower_to_torso(lower, trial, pairs, claimed)
        _new_edges(trial, pairs, claimed)
        if name == OPTIONS[0]:
            _neck_A(trial, pairs, claimed)
        else:
            _neck_B(trial, pairs, claimed)
        numeric = [
            edge
            for edge in pairs
            if edge["kind"] != "UNPROVEN_MANUAL_SURFACE_ATTACHMENT"
        ]
        numeric_components = _components(pieces, numeric)
        connected_components = _components(pieces, pairs)
        expected = (45, 44, 2) if name == OPTIONS[0] else (46, 46, 1)
        if (
            len(pieces) != 24
            or len(pairs) != expected[0]
            or len(numeric) != expected[1]
            or len(numeric_components) != expected[2]
            or len(connected_components) != 1
            or len(claimed) != len(pairs) * 2
        ):
            raise ValueError(
                "24-piece trial assembly topology or interface count changed"
            )
        result[name] = {
            "schema": SCHEMA,
            "variant": name,
            "source_public_stage6_blend_sha256": SOURCE_SHA,
            "units": "mm",
            "total_research_pieces": 24,
            "print_sheet_count": 15,
            "original_source_hoof_edge_count": 2048,
            "lower_original_research_pieces_unchanged": 13,
            "all_pieces": pieces,
            "sewing_interfaces": pairs,
            "numerically_paired_interface_count": len(numeric),
            "manual_unverified_surface_attachment_count": len(pairs) - len(numeric),
            "components_without_unverified_manual_join": numeric_components,
            "all_24_research_parts_connected_including_manual_attachment": True,
            "source_3d_surface_flattened": False,
            "two_stitched_anatomic_volumes_physically_verified": False,
            "physical_toile_produced": False,
            "factory_cut_patterns_approved": 0,
            "P3_status": "in_progress",
            "P4_status": "not_started",
        }
    return result
