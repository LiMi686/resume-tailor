# Resume Tailor (Local)

A local Streamlit app that tailors Li Mi's one-page LaTeX resume to a pasted job description.

## What it does
- Reads your fixed LaTeX resume template
- Reads your experience and project libraries
- Uses the OpenAI API to select either **3 experiences + 3 projects** or **4 experiences + 2 projects**
- Generates concise, ATS-friendly content
- Fills the selected content into your LaTeX template
- Exports a local Word `.docx` version from the same structured payload
- Optionally compiles a PDF if `pdflatex` is installed

## Project structure

```text
resume-tailor/
├─ app/
│  ├─ main.py
│  ├─ prompts.py
│  ├─ schema.py
│  ├─ renderer.py
│  ├─ docx_renderer.py
│  └─ compiler.py
├─ data/
│  ├─ master_resume.tex
│  ├─ experience_library.md
│  ├─ project_library.md
│  └─ resume_rules.md
├─ outputs/
├─ .env.example
├─ requirements.txt
└─ README.md
```

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and set your API key:

```bash
cp .env.example .env
```

Then edit `.env`:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-5.4
OPENAI_REASONING_EFFORT=high
OPENAI_ENABLE_COMPRESS_PASS=true
OPENAI_EXPERIENCE_CANDIDATES=0
OPENAI_PROJECT_CANDIDATES=0
```

Optional cost-saving knobs:
- Set `OPENAI_MODEL` to a cheaper model only if you accept possible quality tradeoffs.
- Set `OPENAI_REASONING_EFFORT=low` to reduce reasoning-token usage.
- Set `OPENAI_EXPERIENCE_CANDIDATES` or `OPENAI_PROJECT_CANDIDATES` to a positive number only if you explicitly want local pre-filtering; `0` keeps the full library and preserves baseline selection behavior.
- Leave `OPENAI_ENABLE_COMPRESS_PASS=true` if you want the original one-page safeguard behavior.

## Run

From the project root:

```bash
streamlit run app/main.py
```

## PDF compilation

The app now prefers exporting PDF from the generated Word `.docx` so the PDF matches the Word layout more closely.

PDF export order:
- **Microsoft Word on macOS** via automation
- **Pages on macOS** via automation
- **TeX Live / MiKTeX** as a fallback LaTeX renderer

Then enable **Compile PDF after generating** in the app.

## How to use
1. Paste a job description.
2. Click **Generate Resume**.
3. Download the generated `.tex`, `.json`, or `.docx`.
4. Optionally compile and download the PDF.

## Notes
- The app can compact prompt formatting without removing source evidence.
- The app can optionally run a second compression model pass if it looks too long for one page.
- You can tighten the one-page constraint or candidate counts in `app/main.py` or via `.env`.
- To update your content library, edit files in `data/`.
