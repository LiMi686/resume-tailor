from __future__ import annotations

from collections.abc import Iterable, Sequence
import importlib.util
import re
from dataclasses import dataclass
from typing import Any


DEFAULT_JOBSPY_SCOPE_TEXT = "\n".join(
    [
        "Tucson, AZ 85716 | USA",
        "United States | USA",
        "Canada | Canada",
        "Mexico | Mexico",
    ]
)

SUPPORTED_JOBSPY_SITES = (
    "indeed",
    "linkedin",
    "zip_recruiter",
    "glassdoor",
)

DEFAULT_JOBSPY_SITES = (
    "indeed",
    "linkedin",
    "zip_recruiter",
)

COUNTRY_ALIASES = {
    "us": "USA",
    "usa": "USA",
    "united states": "USA",
    "united states of america": "USA",
    "ca": "Canada",
    "canada": "Canada",
    "mx": "Mexico",
    "mexico": "Mexico",
}


@dataclass(frozen=True)
class JobSpySearchScope:
    label: str
    location: str
    country_indeed: str | None


@dataclass(frozen=True)
class JobSpyOpportunity:
    title: str
    company: str
    location: str
    site: str
    url: str
    board_url: str
    direct_url: str
    jd_text: str
    search_scope: str
    date_posted: str = ""
    is_remote: bool = False
    job_type: str = ""
    salary_text: str = ""
    company_industry: str = ""
    startup_score: int = 0
    startup_signals: str = ""
    visa_support_score: int = 0
    visa_support_label: str = ""
    visa_support_signals: str = ""
    sponsorship_filter_exempt: bool = False


def jobspy_available() -> bool:
    return importlib.util.find_spec("jobspy") is not None


def jobspy_install_hint() -> str:
    return "Install JobSpy with `pip install -r requirements.txt` or `pip install -U python-jobspy`."


def parse_jobspy_search_scopes(raw_text: str) -> list[JobSpySearchScope]:
    scopes: list[JobSpySearchScope] = []
    seen: set[tuple[str, str]] = set()

    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        location_text, separator, country_text = line.partition("|")
        location = location_text.strip()
        if not location:
            continue

        country = _normalize_country(country_text.strip()) if separator else _infer_country(location)
        key = (location.lower(), (country or "").lower())
        if key in seen:
            continue

        seen.add(key)
        label = f"{location} ({country})" if country else location
        scopes.append(
            JobSpySearchScope(
                label=label,
                location=location,
                country_indeed=country,
            )
        )

    return scopes


def search_jobspy_jobs(
    *,
    search_term: str,
    scope_text: str,
    site_names: Sequence[str],
    results_wanted: int,
    hours_old: int | None = None,
    job_type: str | None = None,
    remote_only: bool = False,
    easy_apply_only: bool = False,
    linkedin_fetch_description: bool = True,
    prefer_startups: bool = False,
    require_sponsorship: bool = False,
) -> tuple[list[JobSpyOpportunity], list[str]]:
    if not jobspy_available():
        raise RuntimeError(jobspy_install_hint())

    from jobspy import scrape_jobs

    scopes = parse_jobspy_search_scopes(scope_text)
    if not scopes:
        raise ValueError("Add at least one JobSpy search scope.")

    normalized_sites = [site.strip().lower() for site in site_names if site.strip()]
    if not normalized_sites:
        raise ValueError("Choose at least one JobSpy source.")

    site_order = {site: index for index, site in enumerate(normalized_sites)}
    merged: dict[str, tuple[int, int, JobSpyOpportunity]] = {}
    warnings: list[str] = []
    limitation_warnings: set[str] = set()
    sponsorship_filtered_count = 0

    for scope_index, scope in enumerate(scopes):
        for site in normalized_sites:
            if site not in SUPPORTED_JOBSPY_SITES:
                warnings.append(f"Skipped unsupported JobSpy site `{site}`.")
                continue

            if not _scope_supported_for_site(scope, site):
                warnings.append(f"Skipped `{site}` for `{scope.label}` because that site does not support this country.")
                continue

            scrape_kwargs, site_warnings = _build_site_scrape_kwargs(
                site=site,
                scope=scope,
                search_term=search_term,
                results_wanted=results_wanted,
                hours_old=hours_old,
                job_type=job_type,
                remote_only=remote_only,
                easy_apply_only=easy_apply_only,
                linkedin_fetch_description=linkedin_fetch_description,
            )
            for warning in site_warnings:
                if warning not in limitation_warnings:
                    limitation_warnings.add(warning)
                    warnings.append(warning)

            try:
                jobs = scrape_jobs(**scrape_kwargs)
            except Exception as exc:
                warnings.append(f"`{site}` search failed for `{scope.label}`: {exc}")
                continue

            for row in _frame_to_records(jobs):
                opportunity = _record_to_opportunity(row, scope_label=scope.label)
                if not opportunity.title:
                    continue
                if require_sponsorship and not opportunity.sponsorship_filter_exempt and opportunity.visa_support_score < 0:
                    sponsorship_filtered_count += 1
                    continue

                sort_key = (scope_index, site_order.get(site, 999))
                key = _opportunity_key(opportunity)
                existing = merged.get(key)
                if existing is None or sort_key < (existing[0], existing[1]):
                    merged[key] = (sort_key[0], sort_key[1], opportunity)

    if require_sponsorship and sponsorship_filtered_count:
        warnings.append(
            f"Filtered out {sponsorship_filtered_count} roles that explicitly said visa/employment sponsorship was not available."
        )

    opportunities = [
        item[2]
        for item in sorted(
            merged.values(),
            key=lambda item: (
                item[0],
                -_effective_visa_priority(item[2], require_sponsorship=require_sponsorship),
                -(item[2].startup_score if prefer_startups else 0),
                item[1],
                item[2].company.lower(),
                item[2].title.lower(),
            ),
        )
    ]
    return opportunities, warnings


def _normalize_country(value: str) -> str | None:
    normalized = COUNTRY_ALIASES.get(value.strip().lower())
    return normalized or None


def _infer_country(location: str) -> str | None:
    lowered = location.lower()
    if "canada" in lowered:
        return "Canada"
    if "mexico" in lowered:
        return "Mexico"
    return "USA"


def _scope_supported_for_site(scope: JobSpySearchScope, site: str) -> bool:
    if site == "zip_recruiter" and scope.country_indeed == "Mexico":
        return False
    return True


def _build_site_scrape_kwargs(
    *,
    site: str,
    scope: JobSpySearchScope,
    search_term: str,
    results_wanted: int,
    hours_old: int | None,
    job_type: str | None,
    remote_only: bool,
    easy_apply_only: bool,
    linkedin_fetch_description: bool,
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    kwargs: dict[str, Any] = {
        "site_name": [site],
        "search_term": search_term,
        "location": scope.location,
        "results_wanted": results_wanted,
        "description_format": "markdown",
        "verbose": 0,
    }

    if site in {"indeed", "glassdoor"} and scope.country_indeed:
        kwargs["country_indeed"] = scope.country_indeed

    # JobSpy imposes different filter combinations per site, so we downshift
    # conflicting filters here instead of failing the whole run.
    if site in {"indeed", "glassdoor"}:
        if hours_old is not None:
            kwargs["hours_old"] = hours_old
            if job_type or remote_only or easy_apply_only:
                warnings.append(
                    f"`{site}` used `hours_old` for recency and skipped `job_type`, `remote_only`, and `easy_apply_only` "
                    "because JobSpy does not allow those filters together on this site."
                )
        elif easy_apply_only:
            kwargs["easy_apply"] = True
            if job_type or remote_only:
                warnings.append(
                    f"`{site}` used `easy_apply_only` and skipped `job_type` and `remote_only` because JobSpy does not "
                    "allow those filters together on this site."
                )
        else:
            if job_type:
                kwargs["job_type"] = job_type
            if remote_only:
                kwargs["is_remote"] = True
    elif site == "linkedin":
        if hours_old is not None:
            kwargs["hours_old"] = hours_old
            if easy_apply_only:
                warnings.append(
                    "`linkedin` used `hours_old` and skipped `easy_apply_only` because JobSpy does not allow both "
                    "filters together on LinkedIn."
                )
        elif easy_apply_only:
            kwargs["easy_apply"] = True

        if job_type:
            kwargs["job_type"] = job_type
        if remote_only:
            kwargs["is_remote"] = True
        if linkedin_fetch_description:
            kwargs["linkedin_fetch_description"] = True
    else:
        if hours_old is not None:
            kwargs["hours_old"] = hours_old
        if job_type:
            kwargs["job_type"] = job_type
        if remote_only:
            kwargs["is_remote"] = True
        if easy_apply_only:
            kwargs["easy_apply"] = True

    return kwargs, warnings


def _frame_to_records(data: Any) -> list[dict[str, Any]]:
    if hasattr(data, "to_dict"):
        records = data.to_dict(orient="records")
        if isinstance(records, list):
            return [item for item in records if isinstance(item, dict)]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _record_to_opportunity(record: dict[str, Any], *, scope_label: str) -> JobSpyOpportunity:
    lowered = {str(key).lower(): value for key, value in record.items()}

    title = _string_value(_first_value(lowered, "title"))
    company = _string_value(_first_value(lowered, "company"))
    location = _format_location(
        _first_value(lowered, "location")
        or _build_location_from_columns(lowered)
    )
    site = _string_value(_first_value(lowered, "site"))
    direct_url = _string_value(_first_value(lowered, "job_url_direct"))
    board_url = _string_value(_first_value(lowered, "job_url"))
    job_url = _choose_preferred_job_url(site=site, board_url=board_url, direct_url=direct_url)
    jd_text = _string_value(_first_value(lowered, "description"))
    date_posted = _string_value(_first_value(lowered, "date_posted"))
    job_type = _format_collection(_first_value(lowered, "job_type", "listing_type"))
    salary_text = _format_salary(lowered)
    is_remote = bool(_first_value(lowered, "is_remote") or False)
    company_industry = _string_value(_first_value(lowered, "company_industry"))
    startup_score, startup_signals = _score_startup_affinity(lowered)
    sponsorship_filter_exempt = _is_internship_role(
        title=title,
        job_type=job_type,
        description=jd_text,
    )
    visa_support_score, visa_support_label, visa_support_signals = _score_visa_support(
        lowered,
        sponsorship_filter_exempt=sponsorship_filter_exempt,
    )

    return JobSpyOpportunity(
        title=title,
        company=company,
        location=location,
        site=site,
        url=job_url,
        board_url=board_url,
        direct_url=direct_url,
        jd_text=jd_text,
        search_scope=scope_label,
        date_posted=date_posted,
        is_remote=is_remote,
        job_type=job_type,
        salary_text=salary_text,
        company_industry=company_industry,
        startup_score=startup_score,
        startup_signals=startup_signals,
        visa_support_score=visa_support_score,
        visa_support_label=visa_support_label,
        visa_support_signals=visa_support_signals,
        sponsorship_filter_exempt=sponsorship_filter_exempt,
    )


def _first_value(record: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in record:
            return _clean_value(record[key])
    return None


def _build_location_from_columns(record: dict[str, Any]) -> str:
    parts = [
        _string_value(_first_value(record, "city")),
        _string_value(_first_value(record, "state")),
        _string_value(_first_value(record, "country")),
    ]
    return ", ".join(part for part in parts if part)


def _format_location(value: Any) -> str:
    cleaned = _clean_value(value)
    if cleaned is None:
        return ""
    if isinstance(cleaned, dict):
        parts = [
            _string_value(cleaned.get("city")),
            _string_value(cleaned.get("state")),
            _string_value(cleaned.get("country")),
        ]
        return ", ".join(part for part in parts if part)
    return _string_value(cleaned)


def _format_collection(value: Any) -> str:
    cleaned = _clean_value(value)
    if cleaned is None:
        return ""
    if isinstance(cleaned, str):
        return cleaned.strip()
    if isinstance(cleaned, Iterable) and not isinstance(cleaned, (bytes, dict)):
        return ", ".join(_string_value(item) for item in cleaned if _string_value(item))
    return _string_value(cleaned)


def _format_salary(record: dict[str, Any]) -> str:
    minimum = _clean_value(record.get("min_amount"))
    maximum = _clean_value(record.get("max_amount"))
    interval = _string_value(record.get("interval"))
    currency = _string_value(record.get("currency")) or "USD"

    if minimum is None and maximum is None:
        return ""

    parts: list[str] = []
    if minimum is not None and maximum is not None:
        parts.append(f"{_format_amount(minimum)}-{_format_amount(maximum)}")
    elif minimum is not None:
        parts.append(f"from {_format_amount(minimum)}")
    elif maximum is not None:
        parts.append(f"up to {_format_amount(maximum)}")

    if currency:
        parts.insert(0, currency)
    if interval:
        parts.append(f"per {interval}")
    return " ".join(part for part in parts if part).strip()


def _format_amount(value: Any) -> str:
    cleaned = _clean_value(value)
    if isinstance(cleaned, int):
        return f"{cleaned:,}"
    if isinstance(cleaned, float):
        if cleaned.is_integer():
            return f"{int(cleaned):,}"
        return f"{cleaned:,.2f}"
    return _string_value(cleaned)


def _is_internship_role(*, title: str, job_type: str, description: str) -> bool:
    combined = " ".join(part.lower() for part in (title, job_type, description[:400]) if part)
    internship_patterns = (
        " internship",
        " intern ",
        "internship ",
        " intern,",
        " intern-",
        " co-op",
        " co op",
        " coop ",
    )
    return any(pattern in f" {combined} " for pattern in internship_patterns)


def _score_visa_support(
    record: dict[str, Any],
    *,
    sponsorship_filter_exempt: bool,
) -> tuple[int, str, str]:
    if sponsorship_filter_exempt:
        return 0, "internship exempt", "internship/co-op role exempt from sponsorship filter"

    text_parts = [
        _string_value(_first_value(record, "title")),
        _string_value(_first_value(record, "description")),
        _string_value(_first_value(record, "company_description")),
    ]
    text = " ".join(part for part in text_parts if part).lower()

    negative_patterns = {
        "no sponsorship": (
            r"\bno (visa |employment )?sponsorship\b",
            r"\bwithout (visa |employment )?sponsorship\b",
            r"\b(will not|won't|cannot|can't|unable to|do not|does not) sponsor\b",
            r"\b(do not|does not|will not|cannot|can't) provide (visa |employment )?sponsorship\b",
            r"\bnot eligible for (visa |employment )?sponsorship\b",
            r"\bmust be authorized to work .* without (visa |employment )?sponsorship\b",
            r"\b(now or in the future|now or future) require sponsorship\b",
            r"\bfuture sponsorship\b",
            r"\bimmigration sponsorship is not available\b",
            r"\bposition is not eligible for sponsorship\b",
        ),
    }
    for label, patterns in negative_patterns.items():
        if any(re.search(pattern, text) for pattern in patterns):
            return -2, "not supported", label

    positive_patterns = {
        "visa sponsorship available": (
            r"\bvisa sponsorship available\b",
            r"\bemployment sponsorship available\b",
            r"\b(sponsor|sponsorship) (is )?available\b",
            r"\b(will|can) sponsor\b",
            r"\bprovide(s)? (visa |employment )?sponsorship\b",
            r"\boffer(s)? (visa |employment )?sponsorship\b",
            r"\bh-?1b sponsorship\b",
        ),
    }
    for label, patterns in positive_patterns.items():
        if any(re.search(pattern, text) for pattern in patterns):
            return 2, "likely supported", label

    return 0, "unknown", ""


def _effective_visa_priority(opportunity: JobSpyOpportunity, *, require_sponsorship: bool) -> int:
    if not require_sponsorship or opportunity.sponsorship_filter_exempt:
        return 0
    return opportunity.visa_support_score


def _choose_preferred_job_url(*, site: str, board_url: str, direct_url: str) -> str:
    normalized_site = site.strip().lower()
    if normalized_site == "indeed":
        return direct_url or board_url
    return board_url or direct_url


def _score_startup_affinity(record: dict[str, Any]) -> tuple[int, str]:
    score = 0
    signals: list[str] = []

    employee_text = _string_value(
        _first_value(record, "company_num_employees", "company_employees_label")
    ).lower()
    if employee_text:
        if any(token in employee_text for token in ("1-10", "1 to 10", "11-50", "11 to 50")):
            score += 4
            signals.append("very small team")
        elif any(token in employee_text for token in ("51-200", "51 to 200")):
            score += 3
            signals.append("small team")
        elif any(token in employee_text for token in ("201-500", "201 to 500")):
            score += 2
            signals.append("mid-size growth team")

    keyword_sources = [
        _string_value(_first_value(record, "company_description")).lower(),
        _string_value(_first_value(record, "description")).lower(),
        _string_value(_first_value(record, "company_industry")).lower(),
    ]
    merged_text = " ".join(part for part in keyword_sources if part)

    positive_signals = {
        "startup": ("startup", "start-up"),
        "early-stage": ("early stage", "early-stage"),
        "venture-backed": ("venture-backed", "vc-backed", "backed by"),
        "funding-stage": ("seed", "series a", "series b", "series c"),
        "high-growth": ("fast-growing", "high growth", "high-growth", "growth-stage"),
        "founding": ("founding", "0 to 1", "zero to one", "greenfield"),
        "small-team": ("small team", "lean team", "tiny team"),
        "stealth": ("stealth",),
    }
    for label, keywords in positive_signals.items():
        if any(keyword in merged_text for keyword in keywords):
            score += 2
            signals.append(label)

    negative_signals = {
        "enterprise": ("fortune 500", "global leader", "enterprise software", "public company", "publicly traded"),
    }
    for _, keywords in negative_signals.items():
        if any(keyword in merged_text for keyword in keywords):
            score -= 2

    return max(score, 0), ", ".join(signals[:4])


def _opportunity_key(opportunity: JobSpyOpportunity) -> str:
    if opportunity.direct_url:
        return f"url::{opportunity.direct_url}"
    if opportunity.url:
        return f"url::{opportunity.url}"
    return "::".join(
        [
            "sig",
            _normalize_token(opportunity.site),
            _normalize_token(opportunity.company),
            _normalize_token(opportunity.title),
            _normalize_token(opportunity.location),
        ]
    )


def _normalize_token(value: str) -> str:
    return "".join(char for char in value.lower() if char.isalnum())


def _clean_value(value: Any) -> Any:
    if value is None:
        return None
    try:
        if value != value:
            return None
    except Exception:
        return value
    return value


def _string_value(value: Any) -> str:
    cleaned = _clean_value(value)
    if cleaned is None:
        return ""
    return str(cleaned).strip()
