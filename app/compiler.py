from __future__ import annotations
from pathlib import Path
import platform
import shutil
import subprocess


BASE_DIR = Path(__file__).resolve().parents[1]
LOCAL_PDFLATEX = BASE_DIR / ".texlive" / "2026" / "bin" / "universal-darwin" / "pdflatex"
WORD_APP = Path("/Applications/Microsoft Word.app")
PAGES_APP = Path("/Applications/Pages.app")


def find_pdflatex() -> str | None:
    if LOCAL_PDFLATEX.exists():
        return str(LOCAL_PDFLATEX)
    return shutil.which("pdflatex")


def pdflatex_available() -> bool:
    return find_pdflatex() is not None


def word_pdf_available() -> bool:
    return WORD_APP.exists() and shutil.which("osascript") is not None


def windows_word_pdf_available() -> bool:
    return platform.system() == "Windows"


def pages_pdf_available() -> bool:
    return PAGES_APP.exists() and shutil.which("osascript") is not None


def pdf_export_available() -> bool:
    return windows_word_pdf_available() or word_pdf_available() or pages_pdf_available() or pdflatex_available()


def compile_tex(tex_path: Path) -> tuple[bool, str]:
    pdflatex = find_pdflatex()
    if not pdflatex:
        return False, "pdflatex not found. Install TeX Live / MiKTeX to enable PDF compilation."

    cmd = [
        pdflatex,
        "-interaction=nonstopmode",
        "-halt-on-error",
        tex_path.name,
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=tex_path.parent,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            return False, proc.stdout + "\n" + proc.stderr
        return True, proc.stdout
    except Exception as exc:
        return False, str(exc)


def _run_osascript(script: str) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            return False, proc.stdout + "\n" + proc.stderr
        return True, proc.stdout
    except Exception as exc:
        return False, str(exc)


def _run_jxa(script: str, *args: str) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            ["osascript", "-l", "JavaScript", "-e", script, *args],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            return False, proc.stdout + "\n" + proc.stderr
        return True, proc.stdout
    except Exception as exc:
        return False, str(exc)


def export_docx_to_pdf_with_word(docx_path: Path) -> tuple[bool, str]:
    if not word_pdf_available():
        return False, "Microsoft Word with AppleScript automation is not available."

    pdf_path = docx_path.with_suffix(".pdf")
    if pdf_path.exists():
        pdf_path.unlink()
    input_posix = docx_path.resolve().as_posix()
    output_posix = pdf_path.resolve().as_posix()
    script = """
function run(argv) {
  var inputPath = argv[0];
  var outputPath = argv[1];
  var word = Application("Microsoft Word");
  var systemEvents = Application("System Events");

  if (!word.running()) {
    word.activate();
    delay(1);
    systemEvents.processes["Microsoft Word"].visible = false;
  } else {
    word.launch();
    systemEvents.processes["Microsoft Word"].visible = false;
  }

  word.open(Path(inputPath));
  delay(1);

  var doc = word.activeDocument;
  doc.saveAs({ fileName: outputPath, fileFormat: "format PDF" });
  doc.close({ saving: "no" });
  word.quit();
}
"""
    ok, log = _run_jxa(script, input_posix, output_posix)
    if ok and pdf_path.exists():
        return True, log
    return False, log or "Word did not produce a PDF file."


def export_docx_to_pdf_with_windows_word(docx_path: Path) -> tuple[bool, str]:
    if not windows_word_pdf_available():
        return False, "Windows Word PDF export is only available on Windows."

    try:
        import win32com.client  # type: ignore[import-not-found]
    except ImportError:
        return False, "pywin32 is required on Windows for Word->PDF export. Install dependencies from requirements.txt."

    pdf_path = docx_path.with_suffix(".pdf")
    if pdf_path.exists():
        pdf_path.unlink()

    word = None
    document = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        document = word.Documents.Open(str(docx_path.resolve()))
        document.SaveAs(str(pdf_path.resolve()), FileFormat=17)
        document.Close(False)
        word.Quit()
        if pdf_path.exists():
            return True, "Exported PDF with Microsoft Word on Windows."
        return False, "Microsoft Word did not produce a PDF file."
    except Exception as exc:
        try:
            if document is not None:
                document.Close(False)
        except Exception:
            pass
        try:
            if word is not None:
                word.Quit()
        except Exception:
            pass
        return False, str(exc)


def export_docx_to_pdf_with_pages(docx_path: Path) -> tuple[bool, str]:
    if not pages_pdf_available():
        return False, "Pages with AppleScript automation is not available."

    pdf_path = docx_path.with_suffix(".pdf")
    if pdf_path.exists():
        pdf_path.unlink()
    input_posix = docx_path.resolve().as_posix()
    output_posix = pdf_path.resolve().as_posix()
    script = f"""
set inputFile to POSIX file "{input_posix}"
set outputFile to POSIX file "{output_posix}"
tell application "Pages"
    activate
    set openedDoc to open inputFile
    repeat 50 times
        if openedDoc is not missing value then exit repeat
        delay 0.2
    end repeat
    export openedDoc to outputFile as PDF
    close openedDoc saving no
end tell
"""
    ok, log = _run_osascript(script)
    if ok and pdf_path.exists():
        return True, log
    return False, log or "Pages did not produce a PDF file."


def compile_pdf(tex_path: Path, docx_path: Path | None = None) -> tuple[bool, str, Path | None, str | None]:
    if docx_path and docx_path.exists():
        ok, windows_log = export_docx_to_pdf_with_windows_word(docx_path)
        if ok:
            return True, windows_log, docx_path.with_suffix(".pdf"), "word"

        ok, log = export_docx_to_pdf_with_word(docx_path)
        if ok:
            return True, log, docx_path.with_suffix(".pdf"), "word"

        ok, pages_log = export_docx_to_pdf_with_pages(docx_path)
        if ok:
            return True, pages_log, docx_path.with_suffix(".pdf"), "pages"

        latex_ok, latex_log = compile_tex(tex_path)
        if latex_ok:
            return True, latex_log, tex_path.with_suffix(".pdf"), "latex"

        combined_log = "\n\n".join(
            part
            for part in [
                f"Windows Word export failed:\n{windows_log}",
                f"macOS Word export failed:\n{log}",
                f"Pages export failed:\n{pages_log}",
                f"LaTeX export failed:\n{latex_log}",
            ]
            if part.strip()
        )
        return False, combined_log, None, None

    latex_ok, latex_log = compile_tex(tex_path)
    if latex_ok:
        return True, latex_log, tex_path.with_suffix(".pdf"), "latex"
    return False, latex_log, None, None
