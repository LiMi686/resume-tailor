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
    bullet: str

class ResumePayload(BaseModel):
    summary: str
    skills: Skills
    experiences: List[Experience] = Field(min_length=3, max_length=4)
    projects: List[Project] = Field(min_length=2, max_length=3)

    @model_validator(mode="after")
    def require_arizona_list_experience(self):
        valid_pairs = {(3, 3), (4, 2)}
        pair = (len(self.experiences), len(self.projects))
        if pair not in valid_pairs:
            raise ValueError("Resume must contain either 3 experiences and 3 projects, or 4 experiences and 2 projects.")
        if not any("Arizona List" in exp.organization for exp in self.experiences):
            raise ValueError("Arizona List — Data Analyst Intern must be included in experiences.")
        return self
