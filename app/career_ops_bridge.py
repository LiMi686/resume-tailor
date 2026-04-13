from __future__ import annotations

import csv
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import requests
from bs4 import BeautifulSoup


PIPELINE_LINE_RE = re.compile(r"^- \[[ x]\] (https?://\S+)\s+\|\s+([^|]+?)\s+\|\s+(.+?)\s*$")
SCORE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*/\s*5")
URL_RE = re.compile(r"https?://[^\s)]+")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")

SKIP_STATUSES = {"discarded", "skip", "rejected"}
BASE_DIR = Path(__file__).resolve().parents[1]
LOCAL_NODE_BIN_DIR = BASE_DIR / ".local" / "node" / "bin"
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    )
}


@dataclass(frozen=True)
class CareerOpsOffer:
    url: str
    company: str
    title: str
    location: str = ""
    source: str = ""


@dataclass(frozen=True)
class CareerOpsApplication:
    number: int
    date: str
    company: str
    role: str
    score_raw: str
    score_value: float | None
    status: str
    pdf_link: str
    report_link: str
    notes: str = ""


@dataclass(frozen=True)
class CareerOpsOpportunity:
    company: str
    title: str
    score_value: float | None
    score_raw: str
    status: str
    url: str = ""
    report_path: str = ""
    pdf_path: str = ""
    jd_text: str = ""
    notes: str = ""


def default_career_ops_dir(base_dir: Path) -> Path:
    candidates = (
        base_dir / "career-ops",
        base_dir.parent / "career-ops",
    )
    for candidate in candidates:
        if (candidate / "package.json").exists() and (candidate / "scan.mjs").exists():
            return candidate
    return candidates[-1]


def career_ops_available(path: Path) -> bool:
    return (path / "package.json").exists() and (path / "scan.mjs").exists()


def career_ops_install_hint(path: Path) -> str:
    return (
        f"Clone `career-ops` into `{path}` (or point this field at your existing checkout), "
        "then run `npm install` there."
    )


def _resolve_npm_executable() -> Path | None:
    configured_npm = os.getenv("CAREER_OPS_NPM", "").strip()
    if configured_npm:
        candidate = Path(configured_npm).expanduser()
        if candidate.exists():
            return candidate

    local_npm = LOCAL_NODE_BIN_DIR / "npm"
    if local_npm.exists():
        return local_npm

    system_npm = shutil.which("npm")
    if system_npm:
        return Path(system_npm)
    return None


def _build_node_env() -> dict[str, str]:
    env = dict(os.environ)
    path_parts: list[str] = []
    if LOCAL_NODE_BIN_DIR.exists():
        path_parts.append(str(LOCAL_NODE_BIN_DIR))
    if env.get("PATH"):
        path_parts.append(env["PATH"])
    env["PATH"] = os.pathsep.join(path_parts)
    return env


def fetch_job_description(url: str) -> tuple[str, str]:
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    for selector in ("script", "style", "noscript", "svg", "img", "header", "footer", "nav", "form"):
        for node in soup.select(selector):
            node.decompose()

    title = ""
    title_node = soup.select_one("h1")
    if title_node:
        title = title_node.get_text(" ", strip=True)
    if not title and soup.title:
        title = re.sub(r"\s*[|\-–—].*$", "", soup.title.get_text(" ", strip=True)).strip()
    title = re.sub(r"\s+", " ", title).strip() or url

    content_blocks: list[str] = []
    seen_blocks: set[str] = set()
    preferred_nodes = soup.select("main, article, section")
    for node in preferred_nodes:
        text = re.sub(r"\s+", " ", node.get_text("\n", strip=True)).strip()
        if len(text) < 120:
            continue
        lowered = text.lower()
        if lowered.startswith(("cookie", "privacy", "sign up", "log in")):
            continue
        if text in seen_blocks:
            continue
        seen_blocks.add(text)
        content_blocks.append(text)
        if len(content_blocks) >= 8:
            break

    if not content_blocks:
        page_text = re.sub(r"\s+", " ", soup.get_text("\n", strip=True)).strip()
        if page_text:
            content_blocks.append(page_text)

    description = "\n\n".join([title, *content_blocks]).strip()
    return title, description[:20000]


def run_career_ops_scan(
    career_ops_dir: Path,
    *,
    company: str = "",
    dry_run: bool = False,
) -> tuple[bool, str]:
    npm_executable = _resolve_npm_executable()
    if npm_executable is None:
        raise RuntimeError(
            "No `npm` executable was found. Install Node.js, or set `CAREER_OPS_NPM`, "
            "or keep using the local runtime in `.local/node/bin`."
        )

    command = [str(npm_executable), "run", "scan", "--"]
    if dry_run:
        command.append("--dry-run")
    if company.strip():
        command.extend(["--company", company.strip()])

    proc = subprocess.run(
        command,
        cwd=career_ops_dir,
        env=_build_node_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    output = "\n".join(part for part in (proc.stdout.strip(), proc.stderr.strip()) if part).strip()
    return proc.returncode == 0, output


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _offer_key(company: str, title: str) -> str:
    return f"{_normalize_key(company)}::{_normalize_key(title)}"


def _extract_markdown_target(value: str) -> str:
    match = MARKDOWN_LINK_RE.search(value or "")
    if match:
        return match.group(2).strip()
    return str(value or "").strip()


def _extract_score(value: str) -> float | None:
    match = SCORE_RE.search(value or "")
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _clean_status(value: str) -> str:
    cleaned = re.sub(r"\*\*", "", value or "").strip().lower()
    cleaned = re.sub(r"\s+\d{4}-\d{2}-\d{2}.*$", "", cleaned).strip()
    return cleaned


def _resolve_repo_path(career_ops_dir: Path, raw_value: str) -> str:
    target = _extract_markdown_target(raw_value)
    if not target or target.startswith(("http://", "https://")):
        return target
    path = (career_ops_dir / target).resolve()
    return str(path) if path.exists() else target


def _maybe_load_saved_jd(career_ops_dir: Path, report_path: str) -> tuple[str, str]:
    if not report_path:
        return "", ""
    path = Path(report_path)
    if not path.exists():
        return "", ""

    report_text = path.read_text(encoding="utf-8", errors="ignore")
    jd_text = ""

    for _, target in MARKDOWN_LINK_RE.findall(report_text):
        if target.startswith("jds/") and target.endswith(".md"):
            jd_path = (career_ops_dir / target).resolve()
            if jd_path.exists():
                jd_text = jd_path.read_text(encoding="utf-8", errors="ignore").strip()
                break

    url_match = URL_RE.search(report_text)
    report_url = url_match.group(0) if url_match else ""
    return report_url, jd_text


def load_pipeline_offers(career_ops_dir: Path) -> list[CareerOpsOffer]:
    pipeline_path = career_ops_dir / "data" / "pipeline.md"
    if not pipeline_path.exists():
        return []

    offers: list[CareerOpsOffer] = []
    for line in pipeline_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = PIPELINE_LINE_RE.match(line.strip())
        if not match:
            continue
        offers.append(
            CareerOpsOffer(
                url=match.group(1).strip(),
                company=match.group(2).strip(),
                title=match.group(3).strip(),
                source="pipeline",
            )
        )
    return offers


def load_scan_history_offers(career_ops_dir: Path) -> list[CareerOpsOffer]:
    history_path = career_ops_dir / "data" / "scan-history.tsv"
    if not history_path.exists():
        return []

    offers: list[CareerOpsOffer] = []
    with history_path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            url = str(row.get("url", "")).strip()
            title = str(row.get("title", "")).strip()
            company = str(row.get("company", "")).strip()
            if not url or not title or not company:
                continue
            offers.append(
                CareerOpsOffer(
                    url=url,
                    company=company,
                    title=title,
                    source=str(row.get("portal", "")).strip(),
                )
            )
    return offers


def load_career_ops_applications(career_ops_dir: Path) -> list[CareerOpsApplication]:
    candidates = (
        career_ops_dir / "data" / "applications.md",
        career_ops_dir / "applications.md",
    )
    path = next((item for item in candidates if item.exists()), None)
    if path is None:
        return []

    applications: list[CareerOpsApplication] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 8:
            continue
        try:
            number = int(cells[0])
        except ValueError:
            continue

        score_raw = cells[4] if len(cells) > 4 else ""
        applications.append(
            CareerOpsApplication(
                number=number,
                date=cells[1] if len(cells) > 1 else "",
                company=cells[2] if len(cells) > 2 else "",
                role=cells[3] if len(cells) > 3 else "",
                score_raw=score_raw,
                score_value=_extract_score(score_raw),
                status=_clean_status(cells[5] if len(cells) > 5 else ""),
                pdf_link=cells[6] if len(cells) > 6 else "",
                report_link=cells[7] if len(cells) > 7 else "",
                notes=cells[8] if len(cells) > 8 else "",
            )
        )
    return applications


def load_high_score_opportunities(
    career_ops_dir: Path,
    *,
    minimum_score: float,
) -> tuple[list[CareerOpsOpportunity], list[str]]:
    warnings: list[str] = []
    applications = load_career_ops_applications(career_ops_dir)
    pipeline_offers = load_pipeline_offers(career_ops_dir)
    history_offers = load_scan_history_offers(career_ops_dir)

    offer_index: dict[str, CareerOpsOffer] = {}
    for offer in [*pipeline_offers, *history_offers]:
        offer_index.setdefault(_offer_key(offer.company, offer.title), offer)

    opportunities: list[CareerOpsOpportunity] = []

    for application in applications:
        if application.score_value is None or application.score_value < minimum_score:
            continue
        if application.status in SKIP_STATUSES:
            continue

        offer = offer_index.get(_offer_key(application.company, application.role))
        report_path = _resolve_repo_path(career_ops_dir, application.report_link)
        pdf_path = _resolve_repo_path(career_ops_dir, application.pdf_link)
        report_url, jd_text = _maybe_load_saved_jd(career_ops_dir, report_path)

        opportunity_url = offer.url if offer else report_url
        if not opportunity_url:
            warnings.append(
                f"Could not resolve a job URL for career-ops row #{application.number}: "
                f"{application.company} | {application.role}"
            )

        opportunities.append(
            CareerOpsOpportunity(
                company=application.company,
                title=application.role,
                score_value=application.score_value,
                score_raw=application.score_raw,
                status=application.status,
                url=opportunity_url,
                report_path=report_path,
                pdf_path=pdf_path,
                jd_text=jd_text,
                notes=application.notes,
            )
        )

    if not opportunities and not applications:
        warnings.append(
            "No `applications.md` tracker was found yet. Run career-ops scan and evaluate at least one role first."
        )
    elif not opportunities:
        warnings.append(f"No career-ops roles met the minimum score threshold of {minimum_score:.1f}/5.")

    opportunities.sort(key=lambda item: (item.score_value or 0, item.company.lower(), item.title.lower()), reverse=True)
    return opportunities, warnings
