from __future__ import annotations

import csv
import html
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
import yaml
from bs4 import BeautifulSoup

from app.job_finder import crawl_pages, find_top_jobs, load_job_search_config


DEFAULT_JOB_LINK_KEYWORDS = (
    "job",
    "jobs",
    "career",
    "careers",
    "position",
    "positions",
    "opening",
    "openings",
    "opportunity",
    "opportunities",
    "role",
    "roles",
    "apply",
    "requisition",
    "req",
)

DEFAULT_NON_JOB_LINK_KEYWORDS = (
    "privacy",
    "cookie",
    "benefits",
    "faq",
    "login",
    "sign in",
    "investor",
    "news",
    "blog",
    "press",
    "linkedin",
    "facebook",
    "instagram",
    "terms",
)

NEWGRAD_JOBS_BASE_URL = "https://www.newgrad-jobs.com"
NEWGRAD_DATA_SOURCE_URLS = (
    "https://www.newgrad-jobs.com/list-data-analyst",
)
NEWGRAD_DISCOVERY_TERMS = (
    "data",
    "analytics",
    "analyst",
    "scientist",
    "machine learning",
    "ml",
    "ai",
    "business intelligence",
    "bi",
    "research",
    "quant",
    "model",
    "sql",
    "python",
)
NEWGRAD_CLOSED_TERMS = (
    "this job has closed",
    "job has closed",
    "not found",
    "position has been filled",
)
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    )
}


@dataclass(frozen=True)
class CompanyCareerSource:
    name: str
    careers_url: str
    allowed_domains: tuple[str, ...] = ()


@dataclass(frozen=True)
class DiscoveryConfig:
    companies: tuple[CompanyCareerSource, ...]
    max_links_per_company: int = 40
    job_link_keywords: tuple[str, ...] = DEFAULT_JOB_LINK_KEYWORDS
    non_job_link_keywords: tuple[str, ...] = DEFAULT_NON_JOB_LINK_KEYWORDS


@dataclass
class DiscoveredJobLink:
    company: str
    source_url: str
    url: str
    label: str
    discovery_score: int


@dataclass
class JobDigestResult:
    generated_at: str
    discovered_links: list[DiscoveredJobLink] = field(default_factory=list)
    top_matches: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _newgrad_company_source(source_url: str) -> CompanyCareerSource:
    return CompanyCareerSource(
        name="NewGrad Jobs",
        careers_url=source_url,
        allowed_domains=("www.newgrad-jobs.com", "newgrad-jobs.com"),
    )


def load_company_careers_config(path: Path) -> DiscoveryConfig:
    if not path.exists():
        return DiscoveryConfig(companies=())

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    companies_raw = data.get("companies", [])
    companies: list[CompanyCareerSource] = []

    for item in companies_raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        careers_url = str(item.get("careers_url", "")).strip()
        if not name or not careers_url:
            continue
        allowed = item.get("allowed_domains", [])
        allowed_domains = tuple(str(value).strip() for value in allowed if str(value).strip()) if isinstance(allowed, list) else ()
        companies.append(
            CompanyCareerSource(
                name=name,
                careers_url=careers_url,
                allowed_domains=allowed_domains,
            )
        )

    def _tuple_setting(key: str, fallback: tuple[str, ...]) -> tuple[str, ...]:
        raw = data.get(key, fallback)
        if not isinstance(raw, list):
            return fallback
        items = [str(value).strip() for value in raw if str(value).strip()]
        return tuple(items) if items else fallback

    return DiscoveryConfig(
        companies=tuple(companies),
        max_links_per_company=max(1, int(data.get("max_links_per_company", 40) or 40)),
        job_link_keywords=_tuple_setting("job_link_keywords", DEFAULT_JOB_LINK_KEYWORDS),
        non_job_link_keywords=_tuple_setting("non_job_link_keywords", DEFAULT_NON_JOB_LINK_KEYWORDS),
    )


def _normalize_label(link: dict[str, Any]) -> str:
    parts = [
        str(link.get("text", "")).strip(),
        str(link.get("title", "")).strip(),
    ]
    label = " ".join(part for part in parts if part)
    return re.sub(r"\s+", " ", label).strip()


def _domain_allowed(url: str, source: CompanyCareerSource) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    source_parsed = urlparse(source.careers_url)
    source_host = source_parsed.netloc.lower()

    if parsed.scheme == "file" and source_parsed.scheme == "file":
        return True

    if not host:
        return False
    if host == source_host or host.endswith("." + source_host):
        return True
    return any(host == allowed.lower() or host.endswith("." + allowed.lower()) for allowed in source.allowed_domains)


def _score_discovered_link(
    *,
    url: str,
    label: str,
    company: CompanyCareerSource,
    discovery: DiscoveryConfig,
    search_config: Any,
) -> int:
    combined = f"{url} {label}".lower()
    score = 0

    for keyword in discovery.job_link_keywords:
        if keyword.lower() in combined:
            score += 8

    for keyword in discovery.non_job_link_keywords:
        if keyword.lower() in combined:
            score -= 20

    for title in search_config.target_titles:
        if title.lower() in combined:
            score += 14

    if "intern" in combined:
        score += 6

    if "greenhouse" in combined or "lever" in combined or "workday" in combined:
        score += 5

    if not _domain_allowed(url, company):
        score -= 50

    return score


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _looks_like_newgrad_job_path(path: str) -> bool:
    return bool(re.match(r"^/list-data-analyst/[^/]+$", path.rstrip("/")))


def _label_from_newgrad_slug(url: str) -> str:
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    slug = re.sub(r"_[0-9]+(?:-[a-z0-9]+)?$", "", slug, flags=re.IGNORECASE)
    slug = slug.replace("_", " ").replace("-", " ")
    return _normalize_text(slug).title()


def _is_closed_newgrad_listing(label: str) -> bool:
    lowered = label.lower()
    return any(term in lowered for term in NEWGRAD_CLOSED_TERMS)


def _score_newgrad_job_link(label: str, url: str, search_config: Any) -> int:
    lowered = f"{label} {url}".lower()
    score = 20

    if not any(term in lowered for term in NEWGRAD_DISCOVERY_TERMS):
        return 0

    for term in NEWGRAD_DISCOVERY_TERMS:
        if term in lowered:
            score += 8

    for title in search_config.target_titles:
        if title.lower() in lowered:
            score += 14

    for term in search_config.excluded_title_keywords:
        if term.lower() in lowered:
            score -= 25

    if "intern" in lowered:
        score += 8

    return score


def _dedupe_discovered_links(items: list[DiscoveredJobLink]) -> list[DiscoveredJobLink]:
    deduped: list[DiscoveredJobLink] = []
    seen_urls: set[str] = set()
    for item in sorted(
        items,
        key=lambda value: (value.discovery_score, value.company.lower(), value.label.lower(), value.url),
        reverse=True,
    ):
        if item.url in seen_urls:
            continue
        seen_urls.add(item.url)
        deduped.append(item)
    return deduped


def discover_newgrad_jobs_links(
    *,
    search_config_path: Path,
) -> tuple[list[DiscoveredJobLink], list[str]]:
    search_config = load_job_search_config(search_config_path)
    session = requests.Session()
    warnings: list[str] = []
    discovered: list[DiscoveredJobLink] = []
    seen_urls: set[str] = set()
    max_links = max(search_config.top_k * 5, 40)

    for source_url in NEWGRAD_DATA_SOURCE_URLS:
        try:
            response = session.get(source_url, headers=REQUEST_HEADERS, timeout=30)
            response.raise_for_status()
        except Exception as exc:
            warnings.append(f"Could not fetch NewGrad Jobs source page: {source_url} ({exc})")
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        company_source = _newgrad_company_source(source_url)
        candidates: list[DiscoveredJobLink] = []

        for anchor in soup.select("a[href]"):
            href = str(anchor.get("href", "")).strip()
            if not href:
                continue
            absolute_url = urljoin(source_url, href)
            parsed = urlparse(absolute_url)
            if parsed.netloc.lower() not in {"www.newgrad-jobs.com", "newgrad-jobs.com"}:
                continue
            if not _looks_like_newgrad_job_path(parsed.path):
                continue
            if absolute_url in seen_urls:
                continue

            label = _normalize_text(anchor.get_text(" ", strip=True)) or _label_from_newgrad_slug(absolute_url)
            if _is_closed_newgrad_listing(label):
                continue

            discovery_score = _score_newgrad_job_link(label, absolute_url, search_config)
            if discovery_score <= 0:
                continue

            candidates.append(
                DiscoveredJobLink(
                    company=company_source.name,
                    source_url=source_url,
                    url=absolute_url,
                    label=label,
                    discovery_score=discovery_score,
                )
            )

        candidates.sort(key=lambda item: (item.discovery_score, item.label.lower(), item.url), reverse=True)
        for item in candidates[:max_links]:
            if item.url in seen_urls:
                continue
            seen_urls.add(item.url)
            discovered.append(item)

    if not discovered:
        warnings.append("No data-related job links were discovered from newgrad-jobs.com.")

    return _dedupe_discovered_links(discovered), warnings


def discover_job_links_from_careers_pages(
    *,
    config_path: Path,
    search_config_path: Path,
) -> tuple[list[DiscoveredJobLink], list[str]]:
    discovery = load_company_careers_config(config_path)
    search_config = load_job_search_config(search_config_path)

    if not discovery.companies:
        return [], ["No companies configured in data/company_careers.yml."]

    pages = crawl_pages([company.careers_url for company in discovery.companies])
    warnings: list[str] = []
    discovered: list[DiscoveredJobLink] = []
    seen_urls: set[str] = set()

    page_by_url = {page.url: page for page in pages}

    for company in discovery.companies:
        page = page_by_url.get(company.careers_url)
        if page is None or not page.success:
            warnings.append(f"Could not crawl careers page for {company.name}: {company.careers_url}")
            continue

        candidates: list[DiscoveredJobLink] = []
        for bucket_name in ("internal", "external"):
            for link in page.links.get(bucket_name, []):
                href = str(link.get("href", "")).strip()
                if not href:
                    continue
                absolute_url = urljoin(company.careers_url, href)
                if absolute_url in seen_urls:
                    continue
                label = _normalize_label(link)
                discovery_score = _score_discovered_link(
                    url=absolute_url,
                    label=label,
                    company=company,
                    discovery=discovery,
                    search_config=search_config,
                )
                if discovery_score <= 0:
                    continue
                candidates.append(
                    DiscoveredJobLink(
                        company=company.name,
                        source_url=company.careers_url,
                        url=absolute_url,
                        label=label or absolute_url,
                        discovery_score=discovery_score,
                    )
                )

        candidates.sort(key=lambda item: (item.discovery_score, item.label.lower(), item.url), reverse=True)
        for item in candidates[: discovery.max_links_per_company]:
            if item.url in seen_urls:
                continue
            seen_urls.add(item.url)
            discovered.append(item)

    discovered.sort(key=lambda item: (item.discovery_score, item.company.lower(), item.label.lower()), reverse=True)
    return discovered, warnings


def _timestamp_slug(now: datetime) -> str:
    return now.strftime("%Y%m%d_%H%M%S")


def _prepare_rows(top_matches: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in top_matches:
        rows.append(
            {
                "rank": str(item.get("rank", "")),
                "title": str(item.get("title", "")),
                "url": str(item.get("url", "")),
                "score": str(item.get("score", "")),
                "role_type": str(item.get("role_type", "")),
                "visa_status": str(item.get("visa_status", "")),
                "visa_evidence": " | ".join(map(str, item.get("visa_evidence", []))),
                "matched_terms": " | ".join(map(str, item.get("matched_terms", []))),
                "highlights": " | ".join(map(str, item.get("highlights", []))),
            }
        )
    return rows


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return str(value)


def write_job_digest_outputs(result: JobDigestResult, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    latest_json = output_dir / "top_13_jobs.json"
    latest_csv = output_dir / "top_13_jobs.csv"
    timestamp = _timestamp_slug(datetime.fromisoformat(result.generated_at))
    timestamped_json = output_dir / f"top_13_jobs_{timestamp}.json"
    timestamped_csv = output_dir / f"top_13_jobs_{timestamp}.csv"

    payload = {
        "generated_at": result.generated_at,
        "discovered_links": [asdict(item) for item in result.discovered_links],
        "top_matches": result.top_matches,
        "warnings": result.warnings,
    }
    safe_payload = _json_safe(payload)
    latest_json.write_text(json.dumps(safe_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    timestamped_json.write_text(json.dumps(safe_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    rows = _prepare_rows(result.top_matches)
    fieldnames = ["rank", "title", "url", "score", "role_type", "visa_status", "visa_evidence", "matched_terms", "highlights"]
    for path in (latest_csv, timestamped_csv):
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return latest_json, latest_csv


def run_job_digest(
    *,
    careers_config_path: Path,
    search_config_path: Path,
    experience_library_path: Path,
    project_library_path: Path,
    output_dir: Path,
    include_company_careers: bool = True,
    include_newgrad_jobs: bool = True,
) -> JobDigestResult:
    discovered_links: list[DiscoveredJobLink] = []
    warnings: list[str] = []

    if include_company_careers:
        careers_config = load_company_careers_config(careers_config_path)
        if careers_config.companies:
            company_links, company_warnings = discover_job_links_from_careers_pages(
                config_path=careers_config_path,
                search_config_path=search_config_path,
            )
            discovered_links.extend(company_links)
            warnings.extend(company_warnings)

    if include_newgrad_jobs:
        newgrad_links, newgrad_warnings = discover_newgrad_jobs_links(search_config_path=search_config_path)
        discovered_links.extend(newgrad_links)
        warnings.extend(newgrad_warnings)

    discovered_links = _dedupe_discovered_links(discovered_links)
    urls = [item.url for item in discovered_links]
    top_matches: list[dict[str, Any]] = []

    if urls:
        matches, rank_warnings = find_top_jobs(
            urls=urls,
            experience_library_text=experience_library_path.read_text(encoding="utf-8"),
            project_library_text=project_library_path.read_text(encoding="utf-8"),
            config_path=search_config_path,
        )
        top_matches = [asdict(match) for match in matches]
        warnings.extend(rank_warnings)
    else:
        warnings.append("No candidate job links were discovered from the configured careers pages.")

    result = JobDigestResult(
        generated_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        discovered_links=discovered_links,
        top_matches=top_matches,
        warnings=warnings,
    )
    write_job_digest_outputs(result, output_dir)
    return result
