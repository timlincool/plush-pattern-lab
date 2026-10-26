"""Agent Skills must be discoverable, scoped and link to existing project evidence."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".agents" / "skills"
REQUIRED = {
    "feature-map",
    "pattern-engineering",
    "blender-evidence",
    "pr-security-review",
}
LINK = re.compile(r"\]\(([^)]+)\)")
SLUG = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")


def header(contents: str) -> tuple[dict[str, str], str]:
    if not contents.startswith("---\n"):
        raise ValueError("Skill requires YAML frontmatter")
    frontmatter, marker, body = contents[4:].partition("\n---\n")
    if not marker or not body.strip():
        raise ValueError("Skill requires closed frontmatter and usable instructions")
    value = yaml.load(frontmatter, Loader=yaml.BaseLoader)
    if not isinstance(value, dict):
        raise ValueError("Skill metadata must be a YAML mapping")
    if set(value) != {"name", "description"}:
        raise ValueError("Only name and description metadata are allowed")
    if not isinstance(value["name"], str) or not SLUG.fullmatch(value["name"]):
        raise ValueError("Skill name must be a lowercase slug")
    if not isinstance(value["description"], str) or not value["description"].strip():
        raise ValueError("Skill requires a non-empty description")
    return value, body


def relative_targets(source: Path, markdown: str) -> list[Path]:
    paths = []
    for link in LINK.findall(markdown):
        if link.startswith(("https://", "http://", "#", "mailto:")):
            continue
        name = link.split("#", 1)[0]
        target = (source.parent / name).resolve()
        if not target.is_relative_to(ROOT.resolve()):
            raise ValueError(f"Skill link outside repository: {source} -> {link}")
        paths.append(target)
    return paths


def test_discovered_skill_names_are_unique_and_valid():
    files = sorted(SKILLS.glob("*/SKILL.md"))
    assert {path.parent.name for path in files} == REQUIRED
    descriptions = []
    for path in files:
        meta, body = header(path.read_text(encoding="utf-8"))
        assert meta["name"] == path.parent.name
        descriptions.append(meta["description"])
        assert "references/" in body
        assert len(body.strip()) >= 150
    assert len(set(descriptions)) == len(descriptions)


def test_skill_references_exist_and_are_linked():
    for skill in sorted(SKILLS.iterdir()):
        if not skill.is_dir():
            continue
        skill_file = skill / "SKILL.md"
        body = header(skill_file.read_text(encoding="utf-8"))[1]
        references = sorted((skill / "references").glob("*.md"))
        assert references
        for path in references:
            assert f"references/{path.name}" in body
            assert len(path.read_text(encoding="utf-8").strip()) >= 200
        for doc in (skill_file, *references):
            for target in relative_targets(doc, doc.read_text(encoding="utf-8")):
                assert target.is_file(), f"{doc.relative_to(ROOT)} -> {target}"


def test_agents_entrypoint_routes_all_skills():
    guide = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for name in REQUIRED:
        assert f".agents/skills/{name}/SKILL.md" in guide
    assert "python scripts/check_quality.py" in guide
    assert "timlincool" in guide
    assert "外部 PR" in guide


@pytest.mark.parametrize(
    "invalid",
    [
        "not frontmatter",
        "---\nname: feature-map\n---\nmissing description",
        "---\nname: feature map\ndescription: invalid\n---\nbody",
    ],
)
def test_invalid_skill_headers_are_rejected(invalid):
    with pytest.raises(ValueError):
        header(invalid)


def test_links_cannot_escape_repository(tmp_path):
    source = tmp_path / "SKILL.md"
    with pytest.raises(ValueError):
        relative_targets(source, "[unsafe](../../outside/secret.md)")
