from __future__ import annotations
from pathlib import Path
from app.schema import ResumePayload


def latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    out = []
    for ch in text:
        out.append(replacements.get(ch, ch))
    return "".join(out)


def build_experience_block(payload: ResumePayload) -> str:
    chunks = []
    for exp in payload.experiences:
        chunks.append(
            "\n  \\resumeSubheading\n"
            f"    {{{latex_escape(exp.organization)}}}{{{latex_escape(exp.dates)}}}\n"
            f"    {{{latex_escape(exp.role)}}}{{{latex_escape(exp.location)}}}\n"
            "    \\resumeItemListStart"
        )
        for bullet in exp.bullets:
            chunks.append(f"      \\resumeItem{{{latex_escape(bullet)}}}")
        chunks.append("    \\resumeItemListEnd\n")
    return "\n".join(chunks)


def build_project_block(payload: ResumePayload) -> str:
    lines = []
    for proj in payload.projects:
        title = latex_escape(proj.title)
        bullet = latex_escape(proj.bullet)
        if proj.link:
            link = proj.link.replace('%', r'\%')
            title_part = rf"\href{{{link}}}{{\textcolor{{blue}}{{\myuline{{{title}}}}}}}"
        else:
            title_part = rf"\textbf{{{title}}}"
        lines.append(
            "\\resumeItem{%\n"
            f"{title_part}. \n"
            f"{bullet}" + "}"
        )
    return "\n\n".join(lines)


def render_resume(template_path: Path, payload: ResumePayload) -> str:
    template = template_path.read_text(encoding="utf-8")
    rendered = template
    rendered = rendered.replace("<<SUMMARY>>", latex_escape(payload.summary))
    rendered = rendered.replace("<<SKILLS_LANG>>", latex_escape(payload.skills.languages_analytics))
    rendered = rendered.replace("<<SKILLS_STACK>>", latex_escape(payload.skills.data_stack_ml))
    rendered = rendered.replace("<<SKILLS_DB>>", latex_escape(payload.skills.databases_concepts))
    rendered = rendered.replace("<<EXPERIENCE_BLOCK>>", build_experience_block(payload))
    rendered = rendered.replace("<<PROJECT_BLOCK>>", build_project_block(payload))
    return rendered
