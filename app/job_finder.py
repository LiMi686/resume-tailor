from __future__ import annotations

import asyncio
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
import yaml
from bs4 import BeautifulSoup

from app.context_builder import _tokenize, compact_text, parse_experience_library, parse_project_library


DEFAULT_TARGET_TITLES = (
    "Data Analyst",
    "Business Intelligence Analyst",
    "Analytics Intern",
    "Data Science Intern",
    "Research Assistant",
    "Research Analyst",
    "Machine Learning Intern",
)

DEFAULT_EXCLUDED_TITLE_KEYWORDS = (
    "Senior",
    "Staff",
    "Principal",
    "Director",
    "Manager",
    "Architect",
    "Vice President",
    "VP",
)

DEFAULT_PREFERRED_LOCATIONS = (
    "Remote",
    "Arizona",
    "Phoenix",
    "Tucson",
    "United States",
)

DEFAULT_INTERNSHIP_KEYWORDS = (
    "intern",
    "internship",
    "co-op",
    "co op",
)

DEFAULT_OPT_TERMS = (
    "opt",
    "stem opt",
    "stem-opt",
    "f-1 opt",
    "f1 opt",
)

DEFAULT_SPONSORSHIP_POSITIVE_TERMS = (
    "visa sponsorship available",
    "sponsorship available",
    "provide visa sponsorship",
    "support visa sponsorship",
    "we sponsor visas",
    "h-1b",
    "h1b",
)

DEFAULT_SPONSORSHIP_BLOCK_TERMS = (
    "without sponsorship",
    "no sponsorship",
    "no future sponsorship",
    "will not sponsor",
    "will not provide sponsorship",
    "unable to sponsor",
    "cannot sponsor",
    "does not provide sponsorship",
    "does not offer sponsorship",
    "not eligible for visa sponsorship",
    "must be authorized to work in the united states without sponsorship",
    "must have unrestricted work authorization",
)

DEFAULT_CLOSED_JOB_TERMS = (
    "this job has closed",
    "job has closed",
    "no longer accepting applications",
    "position has been filled",
    "role has been filled",
    "posting has expired",
)


@dataclass(frozen=True)
class JobSearchConfig:
    top_k: int = 13
    minimum_score: int = 10
    target_titles: tuple[str, ...] = DEFAULT_TARGET_TITLES
    excluded_title_keywords: tuple[str, ...] = DEFAULT_EXCLUDED_TITLE_KEYWORDS
    preferred_locations: tuple[str, ...] = DEFAULT_PREFERRED_LOCATIONS
    internship_keywords: tuple[str, ...] = DEFAULT_INTERNSHIP_KEYWORDS
    opt_terms: tuple[str, ...] = DEFAULT_OPT_TERMS
    sponsorship_positive_terms: tuple[str, ...] = DEFAULT_SPONSORSHIP_POSITIVE_TERMS
    sponsorship_block_terms: tuple[str, ...] = DEFAULT_SPONSORSHIP_BLOCK_TERMS
    closed_job_terms: tuple[str, ...] = DEFAULT_CLOSED_JOB_TERMS
    full_time_requires_future_sponsorship: bool = True
    internships_ignore_future_sponsorship_requirement: bool = True
    internship_bonus: int = 10
    opt_match_bonus: int = 18
    unknown_sponsorship_penalty: int = 8
    blocked_sponsorship_penalty: int = 100


@dataclass
class JobMatch:
    rank: int
    title: str
    url: str
    score: int
    role_type: str = ""
    visa_status: str = ""
    eligible: bool = True
    visa_evidence: list[str] = field(default_factory=list)
    matched_terms: list[str] = field(default_factory=list)
    highlights: list[str] = field(default_factory=list)
    jd_text: str = ""


@dataclass
class CrawledPage:
    url: str
    title: str
    markdown: str
    success: bool
    error: str = ""
    links: dict[str, list[dict[str, Any]]] = field(default_factory=dict)


REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    )
}


def crawl4ai_available() -> bool:
    try:
        import crawl4ai  # noqa: F401
    except Exception:
        return False
    return True


def crawl4ai_install_hint() -> str:
    return "Install Crawl4AI with `pip install -r requirements.txt`, then run `crawl4ai-setup` once."


def parse_job_urls(text: str) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = line.strip("-,")
        if not line.startswith(("http://", "https://")):
            continue
        if line in seen:
            continue
        seen.add(line)
        urls.append(line)
    return urls


def load_job_search_config(path: Path) -> JobSearchConfig:
    if not path.exists():
        return JobSearchConfig()

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    def _tuple_of_strings(key: str, fallback: tuple[str, ...]) -> tuple[str, ...]:
        raw = data.get(key, fallback)
        if not isinstance(raw, list):
            return fallback
        items = [str(item).strip() for item in raw if str(item).strip()]
        return tuple(items) if items else fallback

    top_k = int(data.get("top_k", 13) or 13)
    minimum_score = int(data.get("minimum_score", 10) or 10)

    return JobSearchConfig(
        top_k=max(1, top_k),
        minimum_score=minimum_score,
        target_titles=_tuple_of_strings("target_titles", DEFAULT_TARGET_TITLES),
        excluded_title_keywords=_tuple_of_strings("excluded_title_keywords", DEFAULT_EXCLUDED_TITLE_KEYWORDS),
        preferred_locations=_tuple_of_strings("preferred_locations", DEFAULT_PREFERRED_LOCATIONS),
        internship_keywords=_tuple_of_strings("internship_keywords", DEFAULT_INTERNSHIP_KEYWORDS),
        opt_terms=_tuple_of_strings("opt_terms", DEFAULT_OPT_TERMS),
        sponsorship_positive_terms=_tuple_of_strings("sponsorship_positive_terms", DEFAULT_SPONSORSHIP_POSITIVE_TERMS),
        sponsorship_block_terms=_tuple_of_strings("sponsorship_block_terms", DEFAULT_SPONSORSHIP_BLOCK_TERMS),
        closed_job_terms=_tuple_of_strings("closed_job_terms", DEFAULT_CLOSED_JOB_TERMS),
        full_time_requires_future_sponsorship=bool(data.get("full_time_requires_future_sponsorship", True)),
        internships_ignore_future_sponsorship_requirement=bool(
            data.get("internships_ignore_future_sponsorship_requirement", True)
        ),
        internship_bonus=int(data.get("internship_bonus", 10) or 10),
        opt_match_bonus=int(data.get("opt_match_bonus", 18) or 18),
        unknown_sponsorship_penalty=int(data.get("unknown_sponsorship_penalty", 8) or 8),
        blocked_sponsorship_penalty=int(data.get("blocked_sponsorship_penalty", 100) or 100),
    )


def _build_candidate_profile(experience_library_text: str, project_library_text: str) -> dict[str, set[str]]:
    experiences = parse_experience_library(experience_library_text)
    projects = parse_project_library(project_library_text)

    title_tokens: set[str] = set()
    keyword_tokens: set[str] = set()

    for entry in experiences:
        title_tokens.update(_tokenize(entry.title))
        title_tokens.update(_tokenize(entry.location))
        keyword_tokens.update(_tokenize(" ".join(entry.keywords)))
        keyword_tokens.update(_tokenize(" ".join(entry.bullets)))

    for entry in projects:
        title_tokens.update(_tokenize(entry.title))
        keyword_tokens.update(_tokenize(" ".join(entry.keywords)))
        keyword_tokens.update(_tokenize(" ".join(entry.bullets)))

    return {
        "title_tokens": title_tokens,
        "keyword_tokens": keyword_tokens,
    }


def _extract_markdown(result: Any) -> str:
    markdown = getattr(result, "markdown", "")
    if isinstance(markdown, str):
        return markdown

    for attr in ("fit_markdown", "raw_markdown", "markdown"):
        value = getattr(markdown, attr, "")
        if value:
            return str(value)
    return str(markdown or "")


def _extract_title(markdown: str, fallback_url: str) -> str:
    for line in markdown.splitlines():
        text = re.sub(r"^#+\s*", "", line).strip()
        if len(text) >= 6:
            return text[:160]

    match = re.search(r"https?://[^/]+/(.+)", fallback_url)
    if match:
        return match.group(1).replace("-", " ").replace("_", " ").strip()[:160] or fallback_url
    return fallback_url


def _highlight_lines(markdown: str, title: str, limit: int = 3) -> list[str]:
    lines: list[str] = []
    normalized_title = title.lower().strip()

    for raw_line in markdown.splitlines():
        cleaned = re.sub(r"^[#>*\-\d\.\)\(]+\s*", "", raw_line).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        if not cleaned or len(cleaned) < 35:
            continue
        if cleaned.lower() == normalized_title:
            continue
        lowered = cleaned.lower()
        if lowered.startswith(("apply", "share this job", "back to", "cookie", "privacy")):
            continue
        lines.append(cleaned)
        if len(lines) >= limit:
            break
    return lines


def _is_newgrad_jobs_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return host in {"www.newgrad-jobs.com", "newgrad-jobs.com"}


def _normalize_dom_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _crawl_newgrad_job_page(url: str) -> CrawledPage:
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
        response.raise_for_status()
    except Exception as exc:
        return CrawledPage(url=url, title=url, markdown="", success=False, error=str(exc))

    soup = BeautifulSoup(response.text, "html.parser")
    title_node = soup.select_one("h1")
    title = title_node.get_text(" ", strip=True) if title_node else ""
    if not title:
        title_tag = soup.title.get_text(" ", strip=True) if soup.title else ""
        title = re.sub(r"\s*\|.*$", "", title_tag).strip() or url

    section = soup.select_one("section")
    content_parts: list[str] = [title]
    if section:
        section_text = _normalize_dom_text(section.get_text("\n", strip=True))
        if section_text:
            content_parts.append(section_text)

    markdown = "\n\n".join(part for part in content_parts if part).strip()
    return CrawledPage(
        url=url,
        title=title,
        markdown=markdown,
        success=bool(markdown),
        links={},
    )


def _find_phrase_hits(text: str, phrases: tuple[str, ...]) -> list[str]:
    hits: list[str] = []
    for phrase in phrases:
        pattern = r"(?<!\w)" + re.escape(phrase.lower()) + r"(?!\w)"
        if re.search(pattern, text):
            hits.append(phrase)
    return hits


def _evaluate_visa_fit(markdown: str, title: str, config: JobSearchConfig) -> tuple[str, bool, str, list[str], int]:
    combined_text = f"{title}\n{compact_text(markdown)}".lower()
    role_type = "internship" if _find_phrase_hits(combined_text, config.internship_keywords) else "full-time-or-other"

    opt_hits = _find_phrase_hits(combined_text, config.opt_terms)
    positive_hits = _find_phrase_hits(combined_text, config.sponsorship_positive_terms)
    block_hits = _find_phrase_hits(combined_text, config.sponsorship_block_terms)
    evidence = sorted(set(opt_hits + positive_hits + block_hits))

    if role_type == "internship" and config.internships_ignore_future_sponsorship_requirement:
        status = "Internship: future sponsorship is not required for filtering."
        bonus = config.internship_bonus + (config.opt_match_bonus if opt_hits else 0)
        return role_type, True, status, evidence, bonus

    if block_hits:
        status = "Likely incompatible: posting says no future sponsorship or requires unrestricted work authorization."
        return role_type, False, status, evidence, -config.blocked_sponsorship_penalty

    if opt_hits or positive_hits:
        status = "Visa path looks compatible: OPT/STEM-OPT or sponsorship language found."
        return role_type, True, status, evidence, config.opt_match_bonus

    if config.full_time_requires_future_sponsorship:
        status = "Sponsorship not stated: keep for manual review, but rank lower."
        return role_type, True, status, evidence, -config.unknown_sponsorship_penalty

    return role_type, True, "No sponsorship filter applied.", evidence, 0


def _score_job(
    markdown: str,
    title: str,
    config: JobSearchConfig,
    profile: dict[str, set[str]],
) -> tuple[int, list[str], str, bool, str, list[str]]:
    compacted = compact_text(markdown)
    title_tokens = _tokenize(title)
    body_tokens = _tokenize(compacted)

    score = 0
    score += 6 * len(title_tokens & profile["title_tokens"])
    score += 3 * len(title_tokens & profile["keyword_tokens"])
    score += len(body_tokens & profile["keyword_tokens"])

    lowered_title = title.lower()
    lowered_text = compacted.lower()

    title_phrase_hits = [phrase for phrase in config.target_titles if phrase.lower() in lowered_title]
    text_phrase_hits = [phrase for phrase in config.target_titles if phrase.lower() in lowered_text]
    location_hits = [place for place in config.preferred_locations if place.lower() in lowered_text]
    excluded_hits = [term for term in config.excluded_title_keywords if term.lower() in lowered_title]

    score += 12 * len(title_phrase_hits)
    score += 5 * len(text_phrase_hits)
    score += 3 * len(location_hits)
    score -= 20 * len(excluded_hits)

    role_type, eligible, visa_status, visa_evidence, visa_adjustment = _evaluate_visa_fit(compacted, title, config)
    score += visa_adjustment

    matched_terms = sorted((body_tokens & profile["keyword_tokens"]) | set(map(str.lower, title_phrase_hits)))
    return score, matched_terms[:10], role_type, eligible, visa_status, visa_evidence


async def _crawl_urls(urls: list[str]) -> list[CrawledPage]:
    from crawl4ai import AsyncWebCrawler

    async with AsyncWebCrawler() as crawler:
        tasks = [crawler.arun(url=url) for url in urls]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    pages: list[CrawledPage] = []
    for url, item in zip(urls, raw_results):
        if isinstance(item, Exception):
            pages.append(CrawledPage(url=url, title=url, markdown="", success=False, error=str(item)))
            continue

        markdown = _extract_markdown(item)
        title = getattr(item, "title", "") or _extract_title(markdown, url)
        success = bool(getattr(item, "success", True)) and bool(markdown.strip())
        error_message = str(getattr(item, "error_message", "") or "")
        links = getattr(item, "links", None) or {}
        pages.append(
            CrawledPage(
                url=url,
                title=title,
                markdown=markdown,
                success=success,
                error=error_message,
                links=links,
            )
        )
    return pages


def _run_async(coro: Any) -> Any:
    try:
        return asyncio.run(coro)
    except RuntimeError as exc:
        if "asyncio.run() cannot be called from a running event loop" not in str(exc):
            raise
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


def crawl_pages(urls: list[str]) -> list[CrawledPage]:
    if not crawl4ai_available() and any(not _is_newgrad_jobs_url(url) for url in urls):
        raise RuntimeError(crawl4ai_install_hint())
    newgrad_pages: dict[str, CrawledPage] = {}
    standard_urls: list[str] = []

    for url in urls:
        if _is_newgrad_jobs_url(url):
            newgrad_pages[url] = _crawl_newgrad_job_page(url)
        else:
            standard_urls.append(url)

    standard_pages = _run_async(_crawl_urls(standard_urls)) if standard_urls else []
    standard_page_map = {page.url: page for page in standard_pages}

    combined_pages: list[CrawledPage] = []
    for url in urls:
        if url in newgrad_pages:
            combined_pages.append(newgrad_pages[url])
        elif url in standard_page_map:
            combined_pages.append(standard_page_map[url])
        else:
            combined_pages.append(CrawledPage(url=url, title=url, markdown="", success=False, error="No crawl result returned."))

    return combined_pages


def find_top_jobs(
    *,
    urls: list[str],
    experience_library_text: str,
    project_library_text: str,
    config_path: Path,
) -> tuple[list[JobMatch], list[str]]:
    if not crawl4ai_available() and any(not _is_newgrad_jobs_url(url) for url in urls):
        raise RuntimeError(crawl4ai_install_hint())

    config = load_job_search_config(config_path)
    profile = _build_candidate_profile(experience_library_text, project_library_text)
    crawled_pages = crawl_pages(urls)

    warnings: list[str] = []
    scored: list[JobMatch] = []

    for page in crawled_pages:
        if not page.success:
            warnings.append(f"{page.url} could not be parsed cleanly. {page.error}".strip())
            continue

        closed_hits = _find_phrase_hits(f"{page.title}\n{compact_text(page.markdown)}".lower(), config.closed_job_terms)
        if closed_hits:
            warnings.append(f"Excluded closed or expired posting: {page.title} | {page.url}")
            continue

        score, matched_terms, role_type, eligible, visa_status, visa_evidence = _score_job(
            page.markdown,
            page.title,
            config,
            profile,
        )
        if not eligible:
            warnings.append(f"Excluded for LIMI visa rules: {page.title} | {page.url}")
            continue

        scored.append(
            JobMatch(
                rank=0,
                title=page.title,
                url=page.url,
                score=score,
                role_type=role_type,
                visa_status=visa_status,
                eligible=eligible,
                visa_evidence=visa_evidence,
                matched_terms=matched_terms,
                highlights=_highlight_lines(page.markdown, page.title),
                jd_text=page.markdown,
            )
        )

    scored.sort(key=lambda item: (item.score, item.title.lower()), reverse=True)
    filtered = [item for item in scored if item.score >= config.minimum_score] or scored
    top_matches = filtered[: config.top_k]

    for index, match in enumerate(top_matches, start=1):
        match.rank = index

    return top_matches, warnings


def serialize_job_matches(matches: list[Any]) -> str:
    payload: list[dict[str, Any]] = []
    for match in matches:
        if isinstance(match, dict):
            payload.append(match)
        elif hasattr(match, "__dataclass_fields__"):
            payload.append(asdict(match))
        else:
            payload.append(dict(getattr(match, "__dict__", {})))
    return json.dumps(payload, indent=2, ensure_ascii=False)
