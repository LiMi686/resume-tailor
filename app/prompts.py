SYSTEM_PROMPT = """
You tailor resumes from the provided candidate libraries.
Return only valid JSON matching the schema.
Keep every claim truthful and source-supported.
Never invent metrics, tools, responsibilities, technologies, or outcomes.
Always include "Arizona List — Data Analyst Intern" in experiences.
Select either 3 experiences + 3 projects, or 4 experiences + 2 projects.
Keep the resume to one page and make it full without overflow.
Use concise ATS-friendly language.
Summary must be one sentence.
Prefer 3 bullets per experience; allow 4 only when the extra detail is useful and supported.
Keep each project to 1 bullet and keep skill lines compact.
Match the resume language to the JD language.
"""

USER_TEMPLATE = """
Resume rules:
{rules}

Candidate experience library:
{experience_library}

Candidate project library:
{project_library}

Target job description:
{jd}
"""

COMPRESS_TEMPLATE = """
Compress this JSON by about {percent}%.
Do not change the selected experiences or projects.
Keep a valid pair: 3 experiences + 3 projects, or 4 experiences + 2 projects.
Keep "Arizona List — Data Analyst Intern" in experiences.
Shorten wording only.
Preserve truthfulness, relevance, ATS keywords, and one-page fit.
Prefer 3 bullets per experience; keep 4 only when clearly worth the space.
Return only valid JSON.

JSON:
{json_payload}
"""
