"""1:1 printable synthetic toile: layout, seam correspondence and safety controls."""

from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

from plush_pattern_lab.patterns import capped_gore_pattern as capped
from plush_pattern_lab.patterns import fabrication_kit as kit

ROOT = Path(__file__).resolve().parents[1]
SVG = "{http://www.w3.org/2000/svg}"


@pytest.mark.parametrize("format_name", ["A4", "Letter"])
@pytest.mark.parametrize("panels", [8, 12, 24])
def test_actual_size_nesting_and_marked_pieces(format_name, panels):
    spec = capped.make(panels=panels)
    manifest, pages, guide = kit.build(spec, format_name)
    assert manifest["piece_count"] == panels + 2
    assert manifest["gore_count"] == panels
    assert manifest["print_scale"] == 1.0
    assert manifest["status"] == kit.STATUS
    assert len(pages) == len(manifest["sheets"])
    assert len(pages) >= 1
    if panels == 12:
        assert len(pages) == 4  # Both separate caps fit beside the final gores.
    assert manifest["total_cut_area_cm2"] > 0
    found = []
    regions = []
    for entry, text in zip(manifest["sheets"], pages):
        root = ET.fromstring(text)
        w, h = manifest["paper_size_mm"]
        assert root.attrib["width"] == f"{w:g}mm"
        assert root.attrib["height"] == f"{h:g}mm"
        assert root.attrib["viewBox"] == f"0 0 {w:g} {h:g}"
        assert "scale(" not in text
        assert "10 x 10 mm calibration" in text
        assert len(root.findall(f"{SVG}rect")) == 2
        groups = root.findall(f"{SVG}g")
        assert len(groups) == len(entry["pieces"])
        for group, placement in zip(groups, entry["pieces"]):
            found.append(group.attrib["data-piece"])
            assert group.attrib["data-piece"] == placement["id"]
            assert group.attrib["transform"].startswith("translate(")
            polygons = group.findall(f"{SVG}polygon")
            assert [p.attrib["class"] for p in polygons] == ["cut", "stitch"]
            left, top, right, bottom = placement["cut_bounds_mm"]
            assert kit.MARGIN_MM <= left < right <= w - kit.MARGIN_MM
            assert kit.MARGIN_MM + 20 <= top < bottom <= h - kit.MARGIN_MM - 18
            for prev in regions:
                if prev[0] != entry["file"]:
                    continue
                pl, pt, pr, pb = prev[1]
                assert right <= pl or pr <= left or bottom <= pt or pb <= top
            regions.append((entry["file"], placement["cut_bounds_mm"]))
    assert found == [*(f"P{i:02d}" for i in range(1, panels + 1)), "UPPER", "LOWER"]
    assert "100%" in guide
    assert f"{panels + 2} 片" in guide
    assert "40%" in guide and "60%" in guide
    assert "未通过验证" in guide


def test_notches_and_turning_opening_are_matched():
    count = 12
    spec = capped.make(panels=count)
    manifest, pages, _ = kit.build(spec)
    assert manifest["turning_opening"]["seam"] == "P12.right <-> P01.left"
    left = np.asarray(spec["gore"]["left_stitch_2d_mm"])
    right = np.asarray(spec["gore"]["right_stitch_2d_mm"])
    for fraction in (*kit.OPENING, 0.25, 0.5, 0.75):
        lp = kit._seam_at_fraction(left, fraction)
        rp = kit._seam_at_fraction(right, fraction)
        assert lp[1] == pytest.approx(rp[1], abs=1e-10)
    all_pages = "\n".join(pages)
    assert all_pages.count('class="opening"') == 4
    assert all_pages.count('class="notch"') == 6 * count + 2 * count
    assert all_pages.count('class="cap-start"') == 2
    assert all_pages.count('class="nap"') == 2 * count


def test_translation_keeps_shape_exactly_same_size():
    source = capped.make(panels=12)
    _, pages, _ = kit.build(source)
    root = ET.fromstring(pages[0])
    group = root.find(f"{SVG}g")
    outline = group.findall(f"{SVG}polygon")[0]
    transformed = np.array(
        [
            [float(value) for value in pair.split(",")]
            for pair in outline.attrib["points"].split()
        ]
    )
    reference = np.asarray(source["gore"]["cut_outline_2d_mm"])
    assert transformed.shape == reference.shape
    assert np.max(abs(transformed - reference)) < 1e-4
    assert np.linalg.norm(transformed[0] - transformed[1]) == pytest.approx(
        np.linalg.norm(reference[0] - reference[1]), abs=1e-4
    )


def test_stitched_seams_must_come_from_verified_correspondence():
    source = capped.make(panels=12)
    invalid = copy.deepcopy(source)
    invalid["caps"]["upper"]["stitch_ring_2d_mm"][2][0] += 8
    with pytest.raises(ValueError, match="Cap-to-gore"):
        kit.build(invalid)


@pytest.mark.parametrize(
    "change",
    [
        ("schema", "private-asset"),
        ("status", "APPROVED_FOR_MANUFACTURING"),
    ],
)
def test_reject_incompatible_source(change):
    source = capped.make()
    source[change[0]] = change[1]
    with pytest.raises(ValueError):
        kit.build(source)


def test_reject_locally_unequal_seams_even_with_matched_row_heights():
    source = capped.make()
    source["gore"]["right_stitch_2d_mm"][10][0] += 0.8
    with pytest.raises(ValueError, match="every stitch-row segment"):
        kit.build(source)


def test_reject_invalid_allowance_nonfinite_and_oversized():
    source = capped.make()
    source["parameters"]["allowance_mm"] = 0
    with pytest.raises(ValueError, match="allowance"):
        kit.build(source)
    source = capped.make()
    source["gore"]["cut_outline_2d_mm"][0][0] = float("nan")
    with pytest.raises(ValueError, match="non-finite"):
        kit.build(source)
    source = capped.make(radius_mm=200, half_height_mm=400, panels=8)
    with pytest.raises(ValueError, match="refusing to scale"):
        kit.build(source)


def test_cli_creates_non_overwriting_prototype_kit(tmp_path):
    spec = tmp_path / "approved-synthetic-source.json"
    target = tmp_path / "paper-sheets"
    spec.write_text(json.dumps(capped.make(panels=12)))
    command = [
        sys.executable,
        str(ROOT / "scripts/build_prototype_kit.py"),
        "--input",
        str(spec),
        "--output-dir",
        str(target),
        "--paper",
        "A4",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    manifest = json.loads((target / "manifest.json").read_text())
    assert (target / "sewing-guide.md").is_file()
    assert len(list(target.glob("sheet-*.svg"))) == len(manifest["sheets"])
    assert re.fullmatch("[0-9a-f]{64}", manifest["source_sha256"])
    snapshot = (target / "manifest.json").read_bytes()
    second = subprocess.run(command, capture_output=True)
    assert second.returncode != 0
    assert (target / "manifest.json").read_bytes() == snapshot
