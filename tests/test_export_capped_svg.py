"""Research SVG should be a true-scale readable pattern, not a production release."""

import xml.etree.ElementTree as ET
from pathlib import Path

from plush_pattern_lab.patterns import capped_gore_pattern as caps
from plush_pattern_lab.patterns import export_capped_svg as svg
import pytest

ROOT = Path(__file__).resolve().parents[1]




@pytest.mark.parametrize("panels", [8, 12, 16])
def test_svg_contains_all_sewing_and_cut_layers(panels):
    spec = caps.make(panels=panels)
    root = ET.fromstring(svg.draw(spec))
    ns = {"s": "http://www.w3.org/2000/svg"}
    assert root.get("width").endswith("mm")
    assert root.get("height").endswith("mm")
    polygons = root.findall("s:polygon", ns)
    assert len(polygons) == 6
    assert len([p for p in polygons if p.get("class") == "cut"]) == 3
    assert len([p for p in polygons if p.get("class") == "stitch"]) == 3
    assert len(root.findall("s:circle", ns)) == 6 + 2 * panels
    text = " ".join((n.text or "") for n in root.findall("s:text", ns))
    assert "NOT APPROVED" in text
    assert f"GORES x{panels}" in text
    assert "UPPER CAP" in text and "LOWER CAP" in text


def test_refuse_incompatible_schema():
    s = caps.make()
    s["schema"] = "private-company-pattern"
    with pytest.raises(ValueError):
        svg.draw(s)


def test_cli_no_overwrite(tmp_path):
    import json
    import subprocess
    import sys

    spec = tmp_path / "source.json"
    out = tmp_path / "design.svg"
    spec.write_text(json.dumps(caps.make()))
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "export_capped_svg.py"),
        "--input",
        str(spec),
        "--output",
        str(out),
    ]
    assert subprocess.run(cmd, capture_output=True).returncode == 0
    assert out.stat().st_size > 3000
    assert subprocess.run(cmd, capture_output=True).returncode != 0
