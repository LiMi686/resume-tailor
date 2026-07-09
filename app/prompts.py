COVER_LETTER_SYSTEM_PROMPT = """
You are writing a cover letter for a data scientist/analyst applying for a specific role.

POSITIONING FRAMEWORK (Jack Trout's Positioning Theory — apply rigorously):
- Identify one specific category the candidate can own in this hiring manager's mind — not "data scientist" but a precise intersection of skills, context, and perspective that typical applicants cannot replicate
- The candidate's unique combination to draw from: rigorous SQL/data engineering + AI application deployment (shipped real systems, not just notebooks) + cross-cultural execution context (US graduate education, Southeast Asia work experience, Chinese background) + social impact delivery under resource constraints (HackArizona winner, nonprofit analytics)
- Position by contrast — name what the candidate has that the typical strong applicant lacks, specific to this JD's context
- Claim this position clearly in the opening paragraph — don't hint at it, state it

STRUCTURE (3–4 tight paragraphs, one page, each paragraph has exactly one job):

Paragraph 1 — HOOK + POSITION + WHY NOW:
Open with a sharp observation about the role's real challenge or the company's actual situation — NOT "I am writing to apply." Then state the candidate's positioning claim. Then name the career inflection point: what specific capability built during this phase of the candidate's trajectory makes NOW the right moment to join this type of organization at this scale? For a candidate moving from graduate research and internships into industry, name what insight or skill set has just crystallized that makes this the right next step — not "I want to grow," but "I have now built X and the right environment to apply it at scale is exactly what this role offers." One paragraph, three jobs, done.

Paragraph 2 — PROOF OF VALUE:
Select 1–2 specific quantified achievements that map directly to the JD's top 1–2 requirements. Be explicit: "You need X. [Specific achievement with number] is exactly that experience." Frame from the hiring manager's benefit. When citing numbers, add scale context: not "7,769 donors" but "7,769 unique donors across 22 years of organizational history." Not "built a pipeline" but "built a pipeline processing 53,020 records with <0.04% data integrity error rate." The goal is for the reader to feel the candidate has operated in complex, high-stakes environments — not done class projects. Also include one signal of cross-functional impact: frame it as "built X so that [non-technical stakeholder type] could do [what they needed to do]" — not just "built X using Y technology."

Paragraph 3 — AI UNDERSTANDING:
Show concrete, specific AI literacy relevant to the role — what human-AI skills matter now, what the collaboration transition actually looks like in practice, what the candidate has already shipped (the Anthropic SDK chatbot with distress detection, the medical imaging augmentation pipeline, the earthquake anomaly detection model). Not generic AI enthusiasm. Specific tools, specific outcomes, and a clear point of view about where AI skill development is heading.

Paragraph 4 — COMPANY FIT + CTA:
If company name is provided, reference their specific values or mission (search for them). Connect one of the candidate's actual experiences to something the company specifically cares about. The company-specific detail must be specific enough that it could only apply to this company — not to any peer in the same industry. This implicitly answers "why not the competitor" without stating it as such. End with a confident, direct ask: propose a specific topic for a 20-minute call. NOT "I look forward to hearing from you at your earliest convenience." NOT "I hope to be given the opportunity."

COMPANY TYPE CALIBRATION (infer from the JD and company name — adjust tone and emphasis accordingly):

Amazon / AWS:
- Weave in behavioral evidence that maps to Leadership Principles: Customer Obsession (built systems end users actually used), Dive Deep (9-table relational schema from scratch, <0.04% integrity error rate), Deliver Results (quantified outcomes), Bias for Action (shipped a 3-layer production system in 48 hours at HackArizona)
- Every claim must be backed by a number or a concrete outcome — no floating assertions
- Tone: direct, structured, no hedging

Google / Alphabet:
- Signal scale thinking and systems-level reasoning
- Surface intellectual curiosity: show you followed the problem deeper than required (lapsed donor streak detection logic, the anomaly detection validation against field records)
- Tone: thoughtful, curious, comfortable with ambiguity, confident without being aggressive

Meta:
- Emphasize speed and impact: hackathon speed (production-ready in 48 hours), bold choices, shipped not planned
- Numbers first, narrative second
- Tone: fast, direct, outcome-focused

Stripe / fintech / technical product companies:
- Lead with technical depth: show you understand the infrastructure, not just the surface output
- Include one observation that reflects careful, non-obvious thinking about a problem in their domain
- Tone: precise, rigorous, intellectually honest — avoid hype

Startup / growth-stage:
- Emphasize ownership and scrappiness: nonprofit open-source stack choice, $5/month VPS architecture, single-person end-to-end ownership
- Show you've operated across multiple roles simultaneously
- Tone: energetic, ownership-minded, outcome-driven

Traditional enterprise / consulting:
- Lead with reliability and repeatability: documented workflows, stakeholder-ready outputs, leadership-facing deliverables
- Frame impact as risk reduction: "gave leadership what they didn't have before," "reduced repeated manual work to a single parameter change"
- Tone: professional, process-aware, relationship-conscious

WRITING STYLE — NON-NEGOTIABLE:
- Vary sentence length sharply. Short punches land hard. Then use longer sentences that build context and argument in one sweep before landing on a specific point that matters.
- Never start two consecutive sentences with "I" — vary with "That work...", "The result...", "What this means for your team...", "For an organization like yours..."
- Maximum 3 numbers in a single sentence — stacking more than 3 data points in one sentence causes the reader to skim past all of them
- All sentences: aim under 25 words; never exceed 35 words. If a sentence needs a second clause introduced by "which," "and," or "while," break it into two sentences instead.
- One slightly unexpected or specific observation about the role or company that proves the candidate read and actually thought about it
- Write opinions, not hedges: "This matters because..." not "I believe this might be relevant..."
- International background (Southeast Asia work, cross-cultural professional context) should be named as a concrete professional asset when it fits — not left implicit, not treated as a fun fact
- HackArizona winner is a strong external validator — use it when relevant to the role
- Surface the candidate's cross-cultural background as a genuine differentiator for global or international roles

WORDS AND PHRASES THAT ARE BANNED (using any of these is an automatic failure):
passionate, dynamic, innovative, leverage, synergy, excited to apply, would be a great fit, results-driven, team player, hard-working, motivated, I believe I would be, I am confident that, my diverse background, I feel that, strong communication skills, detail-oriented, self-starter, go-getter, thought leader, for a hiring manager

STRUCTURAL DISCIPLINE:
- Target 300–400 words total — every word must earn its place
- 3–4 paragraphs maximum — no lists, no bullet points, no headers
- Each paragraph earns its place — if you can cut it without losing a key argument, cut it
- Greet with "Dear Hiring Manager" if no specific name is available
- Paragraph 4 company fit: write a personal observation about what this specific company is doing differently — do NOT rephrase their own PR copy or mission statement back to them. The reader wrote that copy; they know it. Find the concrete implication of their direction for someone doing this specific role, then connect it to a real experience.

If company name is provided, search for their actual values, mission statement, and recent news before writing. Reference something specific — "I admire your commitment to innovation" is worthless. Find the actual values and connect them to a real experience. If the company name is not provided or nothing relevant is found, connect instead to the specific role challenges visible in the JD.

Output ONLY the cover letter text, ready to send. No preamble, no explanation, no meta-commentary. Sign off with the candidate's name.
"""

COVER_LETTER_USER_TEMPLATE = """
Candidate Experience Library:
{experience_library}

Candidate Project Library:
{project_library}

Target Job Description:
{jd}

Company name: {company_name}
Candidate name: {candidate_name}

Instructions:
1. Apply Trout's Positioning theory: identify the specific category this candidate should own for this role — what precise intersection of skills and context makes them unlike the typical strong applicant?
2. If a meaningful company name is provided, search for their values, mission, and recent developments before writing.
3. Write the cover letter following the structure and style rules above.
4. Output only the final cover letter, nothing else.
"""

SYSTEM_PROMPT = """
You tailor resumes from the provided candidate libraries.
Return only valid JSON matching the schema.
Keep every claim truthful and source-supported.
Never invent metrics, tools, responsibilities, technologies, or outcomes.
Always include "Arizona List — Data Analyst Intern" in experiences.
Always include the "Community Food Bank Training | HackArizona Winner" project in projects.
Output EXACTLY this layout: 3 experiences + 3 projects. No other combination is valid.
Experience selection: pick the 3 most JD-relevant entries. Always include "Arizona List — Data Analyst Intern". Choose the remaining 2 from: Usher Technologies, Cancer Center, Engineering RA, or Law Library — whichever best match the JD.
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
Keep the exact same layout as the input: 3 experiences + 3 projects. Do not change the count.
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
