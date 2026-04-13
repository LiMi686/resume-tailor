# Resume Tailor Chrome Extension

This extension is intentionally thin. It does not run the resume generator itself.

What it does:
- Click the extension icon to open the local Resume Tailor app.
- Highlight a job description on any page, right-click, and choose `Send selected JD to Resume Tailor`.

Requirements:
- The local app must already be running at `http://localhost:8501/`.

Install locally in Chrome:
1. Open `chrome://extensions`
2. Turn on `Developer mode`
3. Click `Load unpacked`
4. Select this `chrome-extension/` folder

Note:
- The selected JD is passed through the page URL as a query parameter, so this works best for normal-length job descriptions.
- For very long JDs, open the app from the extension and paste the text manually.
