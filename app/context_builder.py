from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Optional


WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9+#./-]*")

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
    "using",
    "use",
    "used",
    "will",
    "your",
    "you",
    "our",
    "we",
    "role",
    "job",
    "candidate",
    "preferred",
    "required",
    "responsibilities",
    "responsibility",
    "experience",
    "skills",
    "ability",
    "work",
    "team",
    "data",
}


@dataclass(frozen=True)
class ExperienceEntry:
    title: str
    period: str
    location: str
    bullets: tuple[str, ...]
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class ProjectEntry:
    title: str
    bullets: tuple[str, ...]
    keywords: tuple[str, ...]


def _tokenize(text: str) -> set[str]:
    return {
        token.lower()
        for token in WORD_RE.findall(text)
        if len(token) > 1 and token.lower() not in STOPWORDS
    }


def _compact_whitespace(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    compacted: list[str] = []
    previous_blank = False
    for line in lines:
        if not line.strip():
            if not previous_blank:
                compacted.append("")
            previous_blank = True
            continue
        compacted.append(re.sub(r"\s+", " ", line).strip())
        previous_blank = False
    return "\n".join(compacted).strip()


def compact_text(text: str) -> str:
    return _compact_whitespace(text)


def compact_rules(text: str) -> str:
    rules: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        rules.append(line)
    return "\n".join(f"- {rule}" for rule in rules)


def parse_experience_library(text: str) -> list[ExperienceEntry]:
    entries: list[ExperienceEntry] = []
    blocks = re.split(r"^##\s+", text, flags=re.MULTILINE)
    for block in blocks[1:]:
        lines = [line.rstrip() for line in block.strip().splitlines() if line.strip()]
        if not lines:
            continue
        title = lines[0].strip()
        period = ""
        location = ""
        bullets: list[str] = []
        keywords: list[str] = []
        in_bullets = False
        for line in lines[1:]:
            if line.startswith("Period:"):
                period = line.split(":", 1)[1].strip()
                in_bullets = False
            elif line.startswith("Location:"):
                location = line.split(":", 1)[1].strip()
                in_bullets = False
            elif line.startswith("Bullets source:"):
                in_bullets = True
            elif line.startswith("Keywords:"):
                keywords = [item.strip() for item in line.split(":", 1)[1].split(",") if item.strip()]
                in_bullets = False
            elif in_bullets and line.startswith("- "):
                bullets.append(line[2:].strip())
        entries.append(
            ExperienceEntry(
                title=title,
                period=period,
                location=location,
                bullets=tuple(bullets),
                keywords=tuple(keywords),
            )
        )
    return entries


def parse_project_library(text: str) -> list[ProjectEntry]:
    entries: list[ProjectEntry] = []
    blocks = re.split(r"^##\s+", text, flags=re.MULTILINE)
    for block in blocks[1:]:
        lines = [line.rstrip() for line in block.strip().splitlines() if line.strip()]
        if not lines:
            continue
        title = lines[0].strip()
        bullets: list[str] = []
        keywords: list[str] = []
        for line in lines[1:]:
            if line.startswith("- "):
                bullets.append(line[2:].strip())
            elif line.startswith("Keywords:"):
                keywords = [item.strip() for item in line.split(":", 1)[1].split(",") if item.strip()]
        entries.append(ProjectEntry(title=title, bullets=tuple(bullets), keywords=tuple(keywords)))
    return entries


def _score_text(jd: str, title: str, bullets: tuple[str, ...], keywords: tuple[str, ...]) -> int:
    jd_tokens = _tokenize(jd)
    title_tokens = _tokenize(title)
    bullet_tokens = _tokenize(" ".join(bullets))
    keyword_tokens = _tokenize(" ".join(keywords))

    score = 0
    score += 4 * len(jd_tokens & title_tokens)
    score += 3 * len(jd_tokens & keyword_tokens)
    score += 2 * len(jd_tokens & bullet_tokens)

    jd_lower = jd.lower()
    for keyword in keywords:
        key = keyword.lower().strip()
        if len(key) >= 4 and key in jd_lower:
            score += 3

    if "hackarizona" in title.lower():
        score += 100

    return score


def _rank_experiences(jd: str, entries: list[ExperienceEntry], limit: Optional[int]) -> list[ExperienceEntry]:
    if limit is None or limit >= len(entries):
        return entries

    required = next((entry for entry in entries if "Arizona List" in entry.title), None)
    ranked = sorted(
        entries,
        key=lambda entry: (
            "Arizona List" in entry.title,
            _score_text(jd, entry.title, entry.bullets, entry.keywords),
            entry.title,
        ),
        reverse=True,
    )

    selected: list[ExperienceEntry] = []
    if required is not None:
        selected.append(required)

    for entry in ranked:
        if entry in selected:
            continue
        if len(selected) >= limit:
            break
        selected.append(entry)

    return selected


_PRIORITY_PROJECT_MARKERS = {"hackarizona", "most innovative use of ai for the public good"}


def _project_priority_bonus(entry: ProjectEntry) -> int:
    title_lower = entry.title.lower()
    if "hackarizona" in title_lower:
        return 50
    return 20 if any(marker in title_lower for marker in _PRIORITY_PROJECT_MARKERS) else 0


def _rank_projects(jd: str, entries: list[ProjectEntry], limit: Optional[int]) -> list[ProjectEntry]:
    if limit is None or limit >= len(entries):
        return entries

    required = next((entry for entry in entries if "HackArizona" in entry.title), None)
    ranked = sorted(
        entries,
        key=lambda entry: (
            _score_text(jd, entry.title, entry.bullets, entry.keywords) + _project_priority_bonus(entry),
            entry.title,
        ),
        reverse=True,
    )

    selected: list[ProjectEntry] = []
    if required is not None:
        selected.append(required)

    for entry in ranked:
        if entry in selected:
            continue
        if len(selected) >= limit:
            break
        selected.append(entry)

    return selected


def _render_experience_context(entries: list[ExperienceEntry]) -> str:
    blocks: list[str] = []
    for entry in entries:
        lines = [
            f"## {entry.title}",
            f"Period: {entry.period}",
            f"Location: {entry.location}",
        ]
        if entry.keywords:
            lines.append(f"Keywords: {', '.join(entry.keywords)}")
        lines.append("Supported details (select the most JD-relevant):")
        for bullet in entry.bullets:
            lines.append(f"- {bullet}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _render_project_context(entries: list[ProjectEntry]) -> str:
    blocks: list[str] = []
    for entry in entries:
        lines = [f"## {entry.title}"]
        if entry.keywords:
            lines.append(f"Keywords: {', '.join(entry.keywords)}")
        lines.append("Supported details:")
        for bullet in entry.bullets[:4]:
            lines.append(f"- {bullet}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def build_prompt_context(
    *,
    jd: str,
    rules_text: str,
    experience_library_text: str,
    project_library_text: str,
    experience_limit: Optional[int] = None,
    project_limit: Optional[int] = None,
) -> tuple[dict[str, str], dict[str, int]]:
    compacted_jd = compact_text(jd)
    compacted_rules = compact_rules(rules_text)
    experiences = parse_experience_library(experience_library_text)
    projects = parse_project_library(project_library_text)
    selected_experiences = _rank_experiences(compacted_jd, experiences, experience_limit)
    selected_projects = _rank_projects(compacted_jd, projects, project_limit)

    rendered_experiences = _render_experience_context(selected_experiences)
    rendered_projects = _render_project_context(selected_projects)

    stats = {
        "experience_candidates": len(selected_experiences),
        "project_candidates": len(selected_projects),
        "experience_library_chars": len(experience_library_text),
        "project_library_chars": len(project_library_text),
        "experience_context_chars": len(rendered_experiences),
        "project_context_chars": len(rendered_projects),
        "rules_chars": len(compacted_rules),
        "jd_chars": len(compacted_jd),
    }

    return (
        {
            "jd": compacted_jd,
            "rules": compacted_rules,
            "experience_library": rendered_experiences,
            "project_library": rendered_projects,
        },
        stats,
    )
