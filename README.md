# Resume Tailor (Local)

A local Streamlit app that tailors Li Mi's one-page LaTeX resume to a pasted job description.

## What it does
- Reads your fixed LaTeX resume template
- Reads your experience and project libraries
- Uses the OpenAI API to select either **3 experiences + 3 projects** or **4 experiences + 2 projects**
- Generates concise, ATS-friendly content
- Fills the selected content into your LaTeX template
- Exports a local Word `.docx` version from the same structured payload
- Optionally exports a PDF, preferring the Word layout when possible

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

On Windows, the simplest option is:

```bat
run_windows.bat
```

## PDF export

The app now prefers exporting PDF from the generated Word `.docx` so the PDF matches the Word layout more closely.

PDF export order:
- **Microsoft Word on Windows** via COM automation
- **Microsoft Word on macOS** via automation
- **Pages on macOS** via automation
- **TeX Live / MiKTeX** as a fallback LaTeX renderer

Then enable **Generate PDF after generating** in the app.

## Chrome extension

A minimal Chrome extension is included in [chrome-extension](./chrome-extension).

What it does:
- Click the extension icon to open the local app.
- Highlight a JD on a webpage, right-click, and send the selected text to the local app.

How to load it:
1. Start the local app first.
2. Open `chrome://extensions`
3. Turn on `Developer mode`
4. Click `Load unpacked`
5. Select the `chrome-extension/` folder

The extension opens:

```text
http://localhost:8501/?jd=...
```

The app reads that query parameter and prefills the JD box automatically.

## How to use
1. Paste a job description.
2. Click **Generate Resume**.
3. Download the generated `.tex`, `.json`, or `.docx`.
4. Optionally generate and download the PDF.

## Notes
- The app can compact prompt formatting without removing source evidence.
- The app can optionally run a second compression model pass if it looks too long for one page.
- You can tighten the one-page constraint or candidate counts in `app/main.py` or via `.env`.
- To update your content library, edit files in `data/`.
- The Chrome extension passes selected JD text through the app URL, so it works best for normal-length job descriptions. For very long JDs, open the app and paste manually.
