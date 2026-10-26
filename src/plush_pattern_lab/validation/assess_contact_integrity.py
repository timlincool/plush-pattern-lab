"""Independent nonadjacent-intersection promotion veto for synthetic cloth candidates.

An existing geometry research pass does not establish collision freedom.
This veto deliberately distinguishes finite collision evidence from real
manufacturing approval. It never modifies model or simulation results.
"""

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _count(record, key):
    number = record.get(key)
    if isinstance(number, bool) or not isinstance(number, int) or number < 0:
        raise ValueError("Invalid finite intersection count: " + key)
    return number


def assess(simulation, contact, report_sha256=None):
    if simulation.get("status") != "ACTUAL_CAPPED_CLOTH_SEWING_RESEARCH_ONLY":
        raise ValueError("Unknown simulation schema")
    if contact.get("status") != "FINITE_ZERO_THICKNESS_TRIANGLE_INTERSECTION_SCREEN":
        raise ValueError("Unknown independent triangle audit schema")
    if contact.get("research_trial_self_collision_enabled") is not simulation.get(
        "self_collision_enabled"
    ):
        raise ValueError("Simulation and triangle audit collision variants disagree")
    n = _count(contact, "nonadjacent_seam_related_pair_count")
    other = _count(contact, "nonadjacent_other_pair_count")
    total = _count(contact, "nonadjacent_total_intersections")
    _count(contact, "shared_vertex_pairs_excluded")
    if total != n + other:
        raise ValueError("Intersection categories do not add up")
    if _count(contact, "vertex_count") != simulation.get("vertices"):
        raise ValueError("Snapshot vertex identity changed")
    if _count(contact, "triangle_count") != simulation.get("total_face_count") * 2:
        raise ValueError("Snapshot triangle count changed")
    if _count(contact, "sewing_identity_links") != simulation.get(
        "total_sewing_springs"
    ):
        raise ValueError("Seam graph changed")
    if (
        report_sha256 is not None
        and contact.get("source_report_sha256") != report_sha256
    ):
        raise ValueError("Triangle audit did not come from this simulation report")
    # Any nonadjacent triangle intersection is grounds to withhold a
    # 'collision-free' or 'physically sewn' claim, even if seam-related.
    if total:
        status = "RESEARCH_CONTACT_SCREEN_REJECTED"
        passed = False
    else:
        status = "FINITE_TRIANGLE_CONTACT_SCREEN_CLEAR_NOT_CERTIFIED"
        passed = True
    return {
        "status": status,
        "finite_zero_thickness_screen_pass": passed,
        "seam_related_intersections": n,
        "other_nonadjacent_intersections": other,
        "all_nonadjacent_intersections": total,
        "physical_cloth_or_stuffing_approved": False,
        "reason": (
            "Positive nonadjacent triangle intersection witnesses on saved cloth"
            if total
            else "No finite nonadjacent intersection witness found within the declared test"
        ),
        "limitations": [
            "Seam-related intersections are reported, not assumed harmless",
            "Zero finite intersections would not prove coplanar, continuous-time, or thickness safety",
            "No 2D seam strength, material measurements, polyester fill or real plush",
            "The preexisting geometric research gate is separate from this contact veto",
        ],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--simulation-report", type=Path, required=True)
    p.add_argument("--triangle-report", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument(
        "--require-pass",
        action="store_true",
        help="Fail only on an explicit attempt to promote a rejected candidate",
    )
    a = p.parse_args()
    if (
        not a.simulation_report.is_file()
        or not a.triangle_report.is_file()
        or a.output.exists()
    ):
        raise RuntimeError("Missing reports or output already exists")
    report = assess(
        json.loads(a.simulation_report.read_text(encoding="utf8")),
        json.loads(a.triangle_report.read_text(encoding="utf8")),
        report_sha256=sha256(a.simulation_report),
    )
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(
        "CONTACT_VETO",
        json.dumps(
            {
                "status": report["status"],
                "seam": report["seam_related_intersections"],
                "other": report["other_nonadjacent_intersections"],
            }
        ),
        flush=True,
    )
    if a.require_pass and not report["finite_zero_thickness_screen_pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
