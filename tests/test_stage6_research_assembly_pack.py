"""Repackage existing 9 genuine A4 generator outputs, never factory paper."""

from __future__ import annotations

import hashlib
import json

import pytest
from build_stage6_18piece_sewing_pack import build_research_assembly_pack
from build_stage6_lower_mother_toile import _files as lower_files
from build_stage6_upper_mother_toile import _payloads as upper_files
from test_stage6_research_panel_interface import _trial

from plush_pattern_lab.validation.stage6_lower_mother_toile_qc import (
    inspect_source_lower_toile,
)
from plush_pattern_lab.validation.stage6_upper_mother_toile_qc import (
    audit_source_profile_upper_mother,
)


def _setup_research_assets(tmp_path):
    low, high = _trial()
    qa = inspect_source_lower_toile(low)
    lower = tmp_path / "lower"
    lower.mkdir()
    contents = lower_files(low, qa, {"synthetic_fixture_not_stage6": True})
    for name, body in contents.items():
        (lower / name).write_text(body, encoding="utf8")
    raw = (lower / "lower_toile_source_geometry.json").read_bytes()
    audit = audit_source_profile_upper_mother(high, low)
    upper = tmp_path / "upper"
    upper.mkdir()
    for name, body in upper_files(high, audit, hashlib.sha256(raw).hexdigest()).items():
        (upper / name).write_text(body, encoding="utf8")
    return lower, upper


def test_lower_plus_upper_original_13_and_5_a4_research_pieces_get_one_trial_pack(
    tmp_path,
):
    lower, upper = _setup_research_assets(tmp_path)
    destination = tmp_path / "pack"
    manifest = build_research_assembly_pack(lower, upper, destination)
    assert manifest["printed_A4_page_count"] == 9
    assert manifest["total_research_paper_parts"] == 18
    assert manifest["stitched_2d_interface_pairs"] == 32
    assert len(list((destination / "print").glob("*.svg"))) == 9
    assert manifest["P3_status"] == "in_progress"
    assert manifest["P4_status"] == "not_started"
    assert not manifest["factory_sewn_or_approved"]
    for name, digest in manifest["each_asset_SHA256"].items():
        assert hashlib.sha256((destination / name).read_bytes()).hexdigest() == digest
    graph = json.loads(
        (destination / "panel_interface_research_graph.json").read_text()
    )
    assert graph["factory_cut_patterns_approved"] == 0
    assert graph["critical_original_source_neck_center_jump_mm"] > 50
    assert graph["original_3d_meridian_vs_surrogate_2d_mismatch_mm"] > 50
    assert (
        "NOT approved patterns"
        in (destination / "assembly_map_RESEARCH_ONLY.svg").read_text()
    )
    with pytest.raises(ValueError, match="overwrite"):
        build_research_assembly_pack(lower, upper, destination)


@pytest.mark.parametrize("tamper", ("lower_json", "upper_svg", "crossrun", "not_A4"))
def test_modified_source_sheets_or_wrong_run_refused(tmp_path, tamper):
    lower, upper = _setup_research_assets(tmp_path)
    if tamper == "lower_json":
        path = lower / "lower_toile_source_geometry.json"
        path.write_bytes(path.read_bytes() + b" ")
    elif tamper == "upper_svg":
        path = upper / "upper-sheet-05.svg"
        path.write_bytes(path.read_bytes() + b" ")
    elif tamper == "crossrun":
        path = upper / "manifest.json"
        data = json.loads(path.read_text())
        data["same_run_lower_mother_source_json_sha256"] = "0" * 64
        path.write_text(json.dumps(data))
    else:
        path = lower / "sheet-01.svg"
        svg = path.read_text()
        altered = svg.replace('width="210mm"', 'width="200mm"')
        path.write_text(altered)
        index = lower / "manifest.json"
        data = json.loads(index.read_text())
        data["files_sha256"][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        index.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        build_research_assembly_pack(lower, upper, tmp_path / "pack")
