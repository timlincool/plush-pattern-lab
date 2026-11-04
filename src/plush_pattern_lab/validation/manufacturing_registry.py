"""Draft manufacturing roles for the 42 measured public Stage6 Mesh objects.

An engineering planning registry is not a set of cuttable sewing patterns or BOM.
Every proposed relation must be reviewed against physical fabrics and viewpoints.
"""

from __future__ import annotations

from collections import Counter

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

BODY = "PRIMARY continuous sculpt | new anatomy"
FLOOR = "Studio floor"
POLICY = {
    "core_body_mesh": ("main_shell_source", "retopologize_and_design_seams"),
    "decorative_cloud_layers": ("cloud_overlay_candidate", "design_attachment_and_pile"),
    "four_hooves": ("hoof_piece_candidate", "develop_complete_leg_and_hoof_panels"),
    "tail_overlay": ("tail_overlay_candidate", "design_hidden_root_attachment"),
    "facial_markers": ("embroidery_location_reference", "digitize_on_real_head_panels"),
    "ears": ("ear_outer_or_inset_candidate", "design_double_layer_and_ear_root"),
    "fabric_drops": ("fabric_drop_candidate", "design_soft_drop_pattern"),
    "flat_connectors": ("tab_visual_proxy", "rebuild_real_fabric_tab"),
    "studio_floor_not_plush": ("excluded_render_equipment", "no_fabrication"),
}
EXPECTED_COUNTS = {
    "core_body_mesh": 1,
    "decorative_cloud_layers": 7,
    "four_hooves": 4,
    "tail_overlay": 1,
    "facial_markers": 4,
    "ears": 4,
    "fabric_drops": 10,
    "flat_connectors": 10,
    "studio_floor_not_plush": 1,
}


def _verified_source(scene, seams):
    if scene.get("schema") != "stage6-whole-scene-inventory-evidence-v1":
        raise ValueError("requires verified public Stage6 whole-scene inventory")
    if seams.get("schema") != "stage6-hoof-seam-summary-v1":
        raise ValueError("requires the measured four-hoof geometry reference")
    if scene["source"]["source_sha256"] != SOURCE_SHA256:
        raise ValueError("unexpected scene source SHA256")
    if seams["source"]["sha256"] != SOURCE_SHA256:
        raise ValueError("hoof seam evidence does not match the scene")
    if not seams["quality"]["all_3d_interfaces_match"]:
        raise ValueError("original four-hoof interface proof must pass")


def _mesh_rows(scene):
    rows = scene["geometry_entries"]
    if len(rows) != 42 or scene["mesh_objects_total"] != 42:
        raise ValueError("unexpected mesh set; review the new source first")
    names = [entry["name"] for entry in rows]
    if len(set(names)) != 42 or BODY not in names or FLOOR not in names:
        raise ValueError("main body, floor or unique mesh identity missing")
    counts = Counter(entry["provisional_group"] for entry in rows)
    if dict(counts) != EXPECTED_COUNTS:
        raise ValueError("source mesh grouping has changed")
    if any(entry["production_pattern_confirmed"] for entry in rows):
        raise ValueError("a source triage entry claims unknown approved patterns")
    return rows


def _draft_parts(rows):
    parts = []
    for row in rows:
        group = row["provisional_group"]
        role, task = POLICY[group]
        parts.append(
            {
                "source_mesh": row["name"],
                "source_faces": row["faces"],
                "source_bbox_extent_mm": row["bbox_extent_mm"],
                "scene_group": group,
                "proposed_manufacturing_role": role,
                "next_engineering_task": task,
                "review_state": "DESIGN_CONFIRMATION_REQUIRED",
                "cut_pattern_id": None,
                "pieces_to_cut": None,
                "approved_material_sku": None,
                "non_product_scene_asset": group == "studio_floor_not_plush",
            }
        )
    return parts


def _hoof_map(seams):
    hooves = seams["hoofs"]
    names = [row["hoof"] for row in hooves]
    if len(names) != 4 or len(set(names)) != 4:
        raise ValueError("four unique hoof interfaces required")
    for row in hooves:
        if row["vertices"] != 512 or row["matched_3d_max_gap_mm"] != 0:
            raise ValueError("hoof boundary identity not proven")
    rings = [row["body_ring_index"] for row in hooves]
    if len(set(rings)) != 4 or set(rings) != set(range(4)):
        raise ValueError("hoof pairing is incomplete")
    return {row["hoof"]: row for row in hooves}


def _parent_for(row):
    name, group = row["name"], row["provisional_group"]
    if group == "flat_connectors":
        return None
    if group == "fabric_drops":
        return name.replace("Fabric rain drop ", "Connected short flat fabric tab ")
    if group == "ears" and name.startswith("Pink inset ear "):
        return name.replace("Pink inset ear ", "Slender upright ivory ear ")
    return BODY


def _draft_joins(rows, seams):
    hooves = _hoof_map(seams)
    names = {row["name"] for row in rows}
    joins = []
    for row in rows:
        name, group = row["name"], row["provisional_group"]
        if name in (BODY, FLOOR):
            continue
        target = _parent_for(row)
        if target is not None and target not in names:
            raise ValueError("an assembly anchor was invented")
        matched = group == "four_hooves"
        seam = hooves.get(name)
        if matched != (seam is not None):
            raise ValueError("hoof geometric proof cannot be guessed")
        joins.append(
            {
                "child_mesh": name,
                "target_mesh": target,
                "relation": (
                    "verified_3d_boundary_only"
                    if matched
                    else "proposed_attachment_not_verified"
                ),
                "body_open_ring_index": (
                    seam["body_ring_index"] if matched else None
                ),
                "verified_boundary_vertices": 512 if matched else None,
                "production_seam_approved": False,
                "fabric_assembly_verified": False,
                "anchor_missing": target is None,
            }
        )
    joins.sort(key=lambda row: row["child_mesh"])
    if len(joins) != 40 or len({row["child_mesh"] for row in joins}) != 40:
        raise ValueError("every non-root product mesh requires a join plan")
    return joins


def build_draft_register(scene, seams):
    """Use pinned evidence; do not infer a single cuttable pattern."""
    _verified_source(scene, seams)
    rows = _mesh_rows(scene)
    parts = _draft_parts(rows)
    joins = _draft_joins(rows, seams)
    group_counts = dict(sorted(Counter(p["scene_group"] for p in parts).items()))
    if group_counts != dict(sorted(EXPECTED_COUNTS.items())):
        raise ValueError("mesh groups were lost during registry generation")
    return {
        "schema": "stage6-draft-manufacturing-component-registry-v1",
        "status": "P2_DESIGN_REVIEW_NOT_A_FACTORY_TECH_PACK",
        "source_sha256": SOURCE_SHA256,
        "source_scene_evidence": "experiments/stage6_scene_inventory_20261103/summary.json",
        "source_hoof_evidence": "experiments/stage6_hoof_seams_20261030/summary.json",
        "model_mesh_count": len(parts),
        "non_product_scene_mesh_count": 1,
        "provisional_group_counts": group_counts,
        "component_rows": parts,
        "assembly_intents": joins,
        "joins_with_measured_3d_boundary_only": sum(
            item["relation"] == "verified_3d_boundary_only" for item in joins
        ),
        "unresolved_attachment_target_count": sum(
            item["anchor_missing"] for item in joins
        ),
        "approved_cut_patterns": 0,
        "materials_confirmed": False,
        "all_attachments_sewable": False,
        "human_approved_component_classification": False,
        "manufacturing_handoff_ready": False,
        "next_gate": "Design-review 42 meshes, select real core shell panels and attachment paths",
        "limitations": [
            "One visual 3D Mesh is not necessarily one physical part or cut piece",
            "Only the four body-hoof boundary rings have measured 3D registration",
            "Ten fabric-tab support surfaces have not been identified or verified",
            "Core 466278-face visual shell still needs manufacturable partitioning",
        ],
    }
