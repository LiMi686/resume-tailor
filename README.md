# Resume Tailor

A local Streamlit app that tailors Li Mi's one-page resume to a pasted job description, exports `.docx`, and optionally exports PDF.

## What it does
- Uses your fixed LaTeX template plus your experience and project libraries
- Generates a tailored one-page resume from a JD with the OpenAI API
- Exports `.tex`, `.json`, `.docx`, and optionally `.pdf`
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

## How to use

1. Open the `Career-Ops` tab.
2. Set `Career-Ops path` to your local `career-ops` folder.
3. Click `Run Career-Ops Scan`.
4. Click `Load High-Score Career-Ops Jobs`.
5. Click `Use This JD in Resume Tailor` on a role you want.
6. Switch to `Resume Tailor`.
7. Click `Generate Resume`.
8. Download the `.docx` or `.pdf`.

## Chrome extension

The included Chrome extension can still send selected JD text into the app through:

```text
http://localhost:8501/?jd=...
```

Load it from `chrome://extensions` with `Developer mode` turned on.
