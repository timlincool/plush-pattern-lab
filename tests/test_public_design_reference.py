"""Audit v25 public reference data without running legacy reconstruction code."""

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "design" / "reference-v25"
EXPECTED = {
    "APPEARANCE_CONTRACT_v25.md",
    "candidate25_manifest.json",
    "drop_tab_registration23.json",
    "face_embroidery_registration_v14.json",
    "ear_fibre_sampling_analysis23.json",
    "structural_invariance_25_vs12.json",
    "reproduction_verification25.json",
}


def load(name: str) -> dict:
    return json.loads((REFERENCE / name).read_text(encoding="utf-8"))


def test_migration_provenance_is_precise_and_does_not_claim_binary_copy():
    origin = load("PROVENANCE.json")
    assert origin["public_repo"] == "timlincool/plush-pattern-lab"
    assert set(item["file"] for item in origin["files"]) == EXPECTED
    assert not origin["actual_blend_included"]
    assert not origin["original_png_included"]
    assert not origin["release_archives_migrated"]
    assert all(
        re.fullmatch(r"[0-9a-f]{40}", item["source_blob_sha"])
        for item in origin["files"]
    )


def test_ten_drops_and_embroidery_contract_not_machine_ready():
    drops = load("drop_tab_registration23.json")
    assert len(drops["drops"]) == 10
    assert Counter(item["color"] for item in drops["drops"]) == {
        "blue": 5,
        "slate": 3,
        "aqua": 2,
    }
    assert [item["id"] for item in drops["drops"]] == list(range(10))
    assert all(item["tab_cut_width_mm"] == 8 for item in drops["drops"])
    embroidery = load("face_embroidery_registration_v14.json")
    assert embroidery["units"] == "mm"
    assert len(embroidery["eyes"]) == 2
    assert (
        "not" in embroidery["status"].lower()
        or "require" in embroidery["status"].lower()
    )


def test_historical_rebuild_report_not_current_production_certificate():
    record = load("reproduction_verification25.json")
    assert record["object_count"] == 461
    assert record["status"] == "PASS"
    contract = (REFERENCE / "APPEARANCE_CONTRACT_v25.md").read_text(encoding="utf-8")
    assert "製作前仍需成立的證據" in contract
    assert "非動物" in contract or "動物製品" in contract
    assert "非生產" in contract or "不是" in contract
