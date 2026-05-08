SYSTEM_PROMPT = """
You tailor resumes from the provided candidate libraries.
Return only valid JSON matching the schema.
Keep every claim truthful and source-supported.
Never invent metrics, tools, responsibilities, technologies, or outcomes.
Always include "Arizona List — Data Analyst Intern" in experiences.
Always include "Usher Technologies Inc — Data Scientist Intern" in experiences.
Always include the "Community Food Bank Training | HackArizona Winner" project in projects.
Output EXACTLY one of these two layouts: (A) 3 experiences + 3 projects, or (B) 4 experiences + 2 projects. No other combination is valid. Choose (A) when fewer than 4 experiences are clearly relevant to the JD; choose (B) when all 4 experiences are relevant.
Experience selection priority: (1) Arizona List, (2) Usher Technologies, (3) Cancer Center or Engineering RA based on JD fit, (4) Law Library only if it adds soft-skill value that the JD explicitly calls for.
Keep the resume to one page and make it full without overflow.
Use concise ATS-friendly language.
Summary must be one sentence, max 180 characters.
Each experience entry includes a pool of supported bullets. Select the 3–4 most JD-relevant bullets from the pool; do not use all of them.
Prefer 3 bullets per experience; allow 4 only when the extra detail is clearly worth the space.
Each experience bullet must be at most 110 characters. Cut filler words aggressively to stay under this limit.
Exception: "Arizona List — Data Analyst Intern" bullets may be up to 170 characters and may use all 4 bullets if JD-relevant.
For the "Community Food Bank Training | HackArizona Winner" project, always write 2–3 detailed bullets up to 180 characters each; select the most impressive technical and impact details.
For all other projects, write exactly 1 concise bullet up to 120 characters.
Keep skill lines compact: list only the most relevant items, comma-separated.
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
Target job description (use this to judge relevance):
{jd}

Compress this JSON by about {percent}% to ensure it fits on one page.
Do not change the selected experiences or projects.
Keep the exact same layout as the input: either 3 experiences + 3 projects, or 4 experiences + 2 projects. Do not change the count.
Keep "Arizona List — Data Analyst Intern" in experiences.
Keep "Community Food Bank Training | HackArizona Winner" in projects.

Prioritize cuts from least JD-relevant content first:
1. Drop the 4th bullet from non-Arizona-List experience entries if they have 4 bullets.
2. Shorten bullets in experiences that are less relevant to the JD.
3. Shorten bullets in non-HackArizona projects.
4. Shorten HackArizona project bullets last.

Each experience bullet must be at most 110 characters after compression.
Exception: do not shorten "Arizona List — Data Analyst Intern" bullets below 150 characters; keep all 4 bullets for that role.
HackArizona Winner project bullets may be up to 160 characters; preserve as many as possible.
All other project bullets must be at most 100 characters after compression.
Summary must be at most 160 characters.
Preserve truthfulness, ATS keywords, and one-page fit.
Return only valid JSON.

JSON:
{json_payload}
"""
