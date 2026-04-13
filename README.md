# Resume Tailor

A local Streamlit app that tailors Li Mi's one-page resume to a pasted job description, exports `.docx`, and optionally exports PDF.

## What it does
- Uses your fixed LaTeX template plus your experience and project libraries
- Generates a tailored one-page resume from a JD with the OpenAI API
- Exports `.tex`, `.json`, `.docx`, and optionally `.pdf`
- Includes a built-in **JobSpy** tab so you can search live jobs before tailoring
- Includes a built-in **Career-Ops Bridge** so you can:
  - run `career-ops` scans
  - load high-score roles from `career-ops`
  - push a selected JD into Resume Tailor for final export

## Project structure

```text
resume-tailor/
├─ app/
│  ├─ main.py
│  ├─ career_ops_bridge.py
│  ├─ prompts.py
│  ├─ schema.py
│  ├─ renderer.py
│  ├─ docx_renderer.py
│  └─ compiler.py
├─ chrome-extension/
│  ├─ manifest.json
│  └─ background.js
├─ data/
│  ├─ master_resume.tex
│  ├─ experience_library.md
│  ├─ project_library.md
│  └─ resume_rules.md
├─ outputs/
├─ .env.example
├─ requirements.txt
├─ run_windows.bat
└─ README.md
```

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

4. Fill in your `.env`:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-5.4
OPENAI_REASONING_EFFORT=high
OPENAI_ENABLE_COMPRESS_PASS=true
OPENAI_EXPERIENCE_CANDIDATES=0
OPENAI_PROJECT_CANDIDATES=0
CAREER_OPS_DIR=../career-ops
CAREER_OPS_NPM=
JOBSPY_PREFER_STARTUPS=true
JOBSPY_REQUIRE_SPONSORSHIP=true
```

## Run

From the project root:

```bash
streamlit run app/main.py
```

On Windows:

```bat
run_windows.bat
```

## PDF export

The app prefers exporting PDF from the generated Word `.docx` so the PDF matches the Word layout more closely.

PDF export order:
- Microsoft Word on Windows
- Microsoft Word on macOS
- Pages on macOS
- LaTeX as fallback

## Career-Ops Bridge

This repo is now centered on the `career-ops` workflow:
- `career-ops` scans portals and tracks roles
- this app loads high-score roles from `career-ops`
- you choose a role and send its JD into Resume Tailor
- Resume Tailor generates the final `.docx/.pdf`

Recommended local setup:

```bash
git clone https://github.com/santifer/career-ops.git ../career-ops
cd ../career-ops
npm install
```

If your machine does not have a global `npm`, this repo can also use the local runtime at:

```text
.local/node/bin/npm
```

You can point to a specific npm binary with:

```env
CAREER_OPS_NPM=/absolute/path/to/npm
```

## JobSpy Search

The app now includes a dedicated `JobSpy` tab backed by [`python-jobspy`](https://github.com/speedyapply/JobSpy).

Default search scopes are ordered to prioritize North America with Tucson ZIP `85716` first:

```text
Tucson, AZ 85716 | USA
United States | USA
Canada | Canada
Mexico | Mexico
```

Notes:
- The first scope is treated as highest priority.
- You can add more lines to widen the search.
- Use `Location | Country` for non-US scopes so Indeed/Glassdoor get the correct country value.
- The default sources are `indeed`, `linkedin`, and `zip_recruiter`.
- LinkedIn description fetching is enabled by default so selected roles are easier to send into Resume Tailor.
- Startup preference is a soft ranking bias, not a hard filter, so non-startup matches can still appear.
- Sponsorship handling is conservative: non-internship roles that explicitly say sponsorship is unavailable are filtered out, while internships remain exempt from that filter.

## How to use

1. Open the `Career-Ops` tab.
2. Set `Career-Ops path` to your local `career-ops` folder.
3. Click `Run Career-Ops Scan`.
4. Click `Load High-Score Career-Ops Jobs`.
5. Click `Use This JD in Resume Tailor` on a role you want.
6. Switch to `Resume Tailor`.
7. Click `Generate Resume`.
8. Download the `.docx` or `.pdf`.

## JobSpy Workflow

1. Open the `JobSpy` tab.
2. Enter a search term such as `data analyst OR business analyst`.
3. Keep the default search scopes if you want Tucson `85716` first and broader North America after that.
4. Click `Search JobSpy`.
5. Click `Use This JD in Resume Tailor` on a role you want.
6. Switch to `Resume Tailor`.
7. Click `Generate Resume`.

## Chrome extension

The included Chrome extension can still send selected JD text into the app through:

```text
http://localhost:8501/?jd=...
```

Load it from `chrome://extensions` with `Developer mode` turned on.
