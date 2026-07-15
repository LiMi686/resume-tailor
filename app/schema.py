from pydantic import BaseModel, Field, model_validator
from typing import List

class Skills(BaseModel):
    languages_analytics: str
    data_stack_ml: str
    databases_concepts: str

class Experience(BaseModel):
    organization: str
    dates: str
    role: str
    location: str
    bullets: List[str] = Field(min_length=3, max_length=4)

class Project(BaseModel):
    title: str
    link: str = ""
    bullets: List[str] = Field(min_length=1, max_length=3)

class ResumePayload(BaseModel):
    summary: str
    skills: Skills
    experiences: List[Experience] = Field(min_length=3, max_length=4)
    projects: List[Project] = Field(min_length=2, max_length=3)

    @model_validator(mode="after")
    def require_core_entries(self):
        valid_pairs = {(3, 3), (4, 2)}
        pair = (len(self.experiences), len(self.projects))
        if pair not in valid_pairs:
            raise ValueError("Resume must contain either 3 experiences and 3 projects, or 4 experiences and 2 projects.")
        if not any("Arizona List" in exp.organization for exp in self.experiences):
            raise ValueError("Arizona List — Data Analyst Intern must be included in experiences.")
        if not any("Community Food Bank" in proj.title or "HackArizona" in proj.title for proj in self.projects):
            raise ValueError("Community Food Bank Training (HackArizona Winner) must be included in projects.")
        return self


SUMMARY_LIMIT = 180
ARIZONA_LIST_BULLET_LIMIT = 170
DEFAULT_EXPERIENCE_BULLET_LIMIT = 110
HACKARIZONA_PROJECT_BULLET_LIMIT = 180
DEFAULT_PROJECT_BULLET_LIMIT = 120


def _is_arizona_list(organization: str) -> bool:
    return "Arizona List" in organization


def _is_hackarizona_project(title: str) -> bool:
    return "HackArizona" in title or "Community Food Bank" in title


def _truncate_to_limit(text: str, limit: int) -> str:
    """Trim text to at most `limit` chars, cutting on the last word boundary."""
    if len(text) <= limit:
        return text
    clipped = text[:limit]
    last_space = clipped.rfind(" ")
    if last_space > limit * 0.6:
        clipped = clipped[:last_space]
    return clipped.rstrip(" ,;:-")


def enforce_length_limits(payload: ResumePayload) -> tuple[ResumePayload, list[str]]:
    """Model-generated bullets sometimes exceed the prompt's stated char limits
    (more often at lower reasoning effort). Nothing upstream enforces those limits,
    so clamp here as a last line of defense against one-page overflow."""
    warnings: list[str] = []

    summary = payload.summary
    if len(summary) > SUMMARY_LIMIT:
        warnings.append(f"Summary trimmed from {len(summary)} to {SUMMARY_LIMIT} chars.")
        summary = _truncate_to_limit(summary, SUMMARY_LIMIT)

    experiences = []
    for exp in payload.experiences:
        limit = ARIZONA_LIST_BULLET_LIMIT if _is_arizona_list(exp.organization) else DEFAULT_EXPERIENCE_BULLET_LIMIT
        new_bullets = []
        for bullet in exp.bullets:
            if len(bullet) > limit:
                warnings.append(
                    f"[{exp.organization}] bullet trimmed from {len(bullet)} to {limit} chars: \"{bullet[:60]}...\""
                )
                bullet = _truncate_to_limit(bullet, limit)
            new_bullets.append(bullet)
        experiences.append(exp.model_copy(update={"bullets": new_bullets}))

    projects = []
    for proj in payload.projects:
        limit = HACKARIZONA_PROJECT_BULLET_LIMIT if _is_hackarizona_project(proj.title) else DEFAULT_PROJECT_BULLET_LIMIT
        new_bullets = []
        for bullet in proj.bullets:
            if len(bullet) > limit:
                warnings.append(
                    f"[{proj.title}] bullet trimmed from {len(bullet)} to {limit} chars: \"{bullet[:60]}...\""
                )
                bullet = _truncate_to_limit(bullet, limit)
            new_bullets.append(bullet)
        projects.append(proj.model_copy(update={"bullets": new_bullets}))

    clamped = payload.model_copy(update={"summary": summary, "experiences": experiences, "projects": projects})
    return clamped, warnings
