from __future__ import annotations
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.prompts import SYSTEM_PROMPT, USER_TEMPLATE, COMPRESS_TEMPLATE
from app.career_ops_bridge import (
    career_ops_available,
    career_ops_install_hint,
    default_career_ops_dir,
    fetch_job_description,
    load_high_score_opportunities,
    run_career_ops_scan,
)
from app.jobspy_bridge import (
    DEFAULT_JOBSPY_SCOPE_TEXT,
    DEFAULT_JOBSPY_SITES,
    SUPPORTED_JOBSPY_SITES,
    jobspy_available,
    jobspy_install_hint,
    search_jobspy_jobs,
)
from app.context_builder import build_prompt_context
from app.renderer import render_resume
from app.schema import ResumePayload
from app.compiler import compile_pdf, pdf_export_available
from app.docx_renderer import render_docx

DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"
APPLIED_JOBS_PATH = DATA_DIR / "applied_jobs.json"


def read_file(name: str) -> str:
    return (DATA_DIR / name).read_text(encoding="utf-8")


def load_applied_jobs() -> dict[str, dict[str, Any]]:
    if not APPLIED_JOBS_PATH.exists():
        return {}
    try:
        payload = json.loads(APPLIED_JOBS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(key): value for key, value in payload.items() if isinstance(value, dict)}


def save_applied_jobs(applied_jobs: dict[str, dict[str, Any]]) -> None:
    APPLIED_JOBS_PATH.parent.mkdir(parents=True, exist_ok=True)
    APPLIED_JOBS_PATH.write_text(
        json.dumps(applied_jobs, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def build_match_key(match: dict[str, Any]) -> str:
    candidate_parts = [
        str(match.get("source_name", "")).strip().lower(),
        str(match.get("url", "")).strip().lower(),
        str(match.get("jobspy_direct_url", "")).strip().lower(),
        str(match.get("jobspy_board_url", "")).strip().lower(),
        str(match.get("career_ops_report_path", "")).strip().lower(),
        str(match.get("title", "")).strip().lower(),
        str(match.get("company", "") or match.get("career_ops_company", "")).strip().lower(),
        str(match.get("location", "")).strip().lower(),
    ]
    normalized = "||".join(part for part in candidate_parts if part)
    if not normalized:
        normalized = json.dumps(match, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def stamp_matches(matches: list[dict[str, Any]]) -> None:
    for match in matches:
        match["match_key"] = build_match_key(match)


def split_matches_by_applied_status(
    matches: list[dict[str, Any]],
    applied_jobs: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    active_matches: list[dict[str, Any]] = []
    applied_matches: list[dict[str, Any]] = []
    for match in matches:
        match_key = str(match.get("match_key") or build_match_key(match))
        match["match_key"] = match_key
        saved_record = applied_jobs.get(match_key)
        if saved_record:
            merged_match = dict(match)
            merged_match["applied_at"] = saved_record.get("applied_at", "")
            saved_snapshot = saved_record.get("match_snapshot")
            if isinstance(saved_snapshot, dict):
                for key, value in saved_snapshot.items():
                    merged_match.setdefault(key, value)
            applied_matches.append(merged_match)
        else:
            active_matches.append(match)
    return active_matches, applied_matches


def persist_applied_match(match: dict[str, Any]) -> None:
    applied_jobs = load_applied_jobs()
    match_key = str(match.get("match_key") or build_match_key(match))
    match["match_key"] = match_key
    applied_jobs[match_key] = {
        "applied_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "match_snapshot": match,
    }
    save_applied_jobs(applied_jobs)


def remove_applied_match(match_key: str) -> None:
    applied_jobs = load_applied_jobs()
    if match_key in applied_jobs:
        del applied_jobs[match_key]
        save_applied_jobs(applied_jobs)


def load_config() -> None:
    load_dotenv(BASE_DIR / ".env")


def get_client() -> OpenAI:
    load_config()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY in .env")
    return OpenAI(api_key=api_key)


def get_model() -> str:
    load_config()
    model = os.getenv("OPENAI_MODEL", "gpt-5.4").strip()
    if model.endswith("-thinking"):
        return model[: -len("-thinking")]
    return model


def get_reasoning_config() -> dict[str, str] | None:
    load_config()

    valid_efforts = {"none", "minimal", "low", "medium", "high", "xhigh"}
    effort = os.getenv("OPENAI_REASONING_EFFORT", "").strip().lower()
    if effort in valid_efforts:
        model = get_model().lower()
        if effort == "minimal" and model == "gpt-5.4-mini":
            return {"effort": "low"}
        return {"effort": effort}

    # Backward-compatible fallback for old configs like `gpt-5.4-thinking`.
    legacy_model = os.getenv("OPENAI_MODEL", "").strip().lower()
    if legacy_model.endswith("-thinking"):
        return {"effort": "high"}

    return None


def get_candidate_limit(env_name: str) -> int | None:
    load_config()
    raw = os.getenv(env_name, "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
        return value if value > 0 else None
    except ValueError:
        return None


def compress_pass_enabled() -> bool:
    load_config()
    raw = os.getenv("OPENAI_ENABLE_COMPRESS_PASS", "").strip().lower()
    if not raw:
        return True
    return raw in {"1", "true", "yes", "on"}


def extract_usage(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    if not usage:
        return {}

    input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
    total_tokens = int(getattr(usage, "total_tokens", input_tokens + output_tokens) or (input_tokens + output_tokens))

    input_details = getattr(usage, "input_tokens_details", None)
    output_details = getattr(usage, "output_tokens_details", None)

    cached_input_tokens = int(getattr(input_details, "cached_tokens", 0) or 0) if input_details else 0
    reasoning_tokens = int(getattr(output_details, "reasoning_tokens", 0) or 0) if output_details else 0

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cached_input_tokens": cached_input_tokens,
        "reasoning_tokens": reasoning_tokens,
    }


def merge_usage(*items: dict[str, int]) -> dict[str, int]:
    merged = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "cached_input_tokens": 0,
        "reasoning_tokens": 0,
    }
    for item in items:
        for key in merged:
            merged[key] += int(item.get(key, 0))
    return merged


def call_model(jd: str) -> tuple[ResumePayload, dict[str, int], dict[str, int]]:
    client = get_client()
    prompt_context, prompt_stats = build_prompt_context(
        jd=jd,
        rules_text=read_file("resume_rules.md"),
        experience_library_text=read_file("experience_library.md"),
        project_library_text=read_file("project_library.md"),
        experience_limit=get_candidate_limit("OPENAI_EXPERIENCE_CANDIDATES"),
        project_limit=get_candidate_limit("OPENAI_PROJECT_CANDIDATES"),
    )
    user_prompt = USER_TEMPLATE.format(**prompt_context)

    request_kwargs = {
        "model": get_model(),
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "text_format": ResumePayload,
    }
    reasoning = get_reasoning_config()
    if reasoning:
        request_kwargs["reasoning"] = reasoning

    response = client.responses.parse(
        **request_kwargs,
    )
    return response.output_parsed, extract_usage(response), prompt_stats


def compress_payload(payload: ResumePayload, percent: int = 12, jd: str = "") -> tuple[ResumePayload, dict[str, int]]:
    client = get_client()
    request_kwargs = {
        "model": get_model(),
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": COMPRESS_TEMPLATE.format(
                    percent=percent,
                    jd=jd,
                    json_payload=payload.model_dump_json(),
                ),
            },
        ],
        "text_format": ResumePayload,
    }
    reasoning = get_reasoning_config()
    if reasoning:
        request_kwargs["reasoning"] = reasoning

    response = client.responses.parse(**request_kwargs)
    return response.output_parsed, extract_usage(response)


def estimated_length_score(payload: ResumePayload) -> int:
    total = len(payload.summary)
    total += len(payload.skills.languages_analytics)
    total += len(payload.skills.data_stack_ml)
    total += len(payload.skills.databases_concepts)
    for exp in payload.experiences:
        total += len(exp.organization) + len(exp.role) + len(exp.location)
        total += sum(len(b) for b in exp.bullets)
    for proj in payload.projects:
        total += len(proj.title) + sum(len(b) for b in proj.bullets)
    return total


def maybe_compress(payload: ResumePayload, jd: str = "") -> tuple[ResumePayload, dict[str, int]]:
    if not compress_pass_enabled():
        return payload, {}
    score = estimated_length_score(payload)
    if score <= 1600:
        return payload, {}
    # First pass: compress proportionally to how far over the limit we are.
    percent = 25 if score > 2100 else 18
    payload, usage1 = compress_payload(payload, percent=percent, jd=jd)
    # Second pass if still over threshold after first compress.
    if estimated_length_score(payload) > 1700:
        payload, usage2 = compress_payload(payload, percent=12, jd=jd)
        return payload, merge_usage(usage1, usage2)
    return payload, usage1


def sync_jd_from_query_params() -> None:
    pending_jd = st.session_state.pop("_pending_jd_input", None)
    if pending_jd is not None:
        st.session_state["jd_input"] = pending_jd

    query_jd = st.query_params.get("jd", "")
    previous_query_jd = st.session_state.get("_last_query_jd", "")

    if "jd_input" not in st.session_state:
        st.session_state["jd_input"] = query_jd
    elif query_jd and query_jd != previous_query_jd:
        st.session_state["jd_input"] = query_jd

    st.session_state["_last_query_jd"] = query_jd


def queue_match_for_resume(jd_text: str, success_message: str) -> None:
    st.session_state["_pending_jd_input"] = jd_text
    st.session_state["_resume_load_message"] = success_message
    st.rerun()


def assign_match_ranks(matches: list[dict[str, Any]]) -> None:
    for index, match in enumerate(matches, start=1):
        match["rank"] = index


def sync_applied_checkbox_state(matches: list[dict[str, Any]], button_prefix: str) -> bool:
    changed = False
    applied_jobs = load_applied_jobs()
    for match in matches:
        match_key = str(match.get("match_key") or build_match_key(match))
        widget_key = f"applied_toggle_{button_prefix}_{match_key}"
        is_checked = bool(st.session_state.get(widget_key, match_key in applied_jobs))
        if is_checked and match_key not in applied_jobs:
            persist_applied_match(match)
            changed = True
        elif not is_checked and match_key in applied_jobs:
            remove_applied_match(match_key)
            changed = True
    return changed


def load_match_into_resume(match: dict[str, Any]) -> None:
    if match.get("jd_text"):
        queue_match_for_resume(
            str(match["jd_text"]),
            "Loaded this job description into the Resume Tailor tab.",
        )
        return

    candidate_urls: list[str] = []
    for key in ("url", "jobspy_direct_url", "jobspy_board_url"):
        value = str(match.get(key, "")).strip()
        if value and value not in candidate_urls:
            candidate_urls.append(value)

    if candidate_urls:
        last_error = ""
        for index, candidate_url in enumerate(candidate_urls):
            try:
                spinner_text = "Fetching this job description before handing it to Resume Tailor..."
                if index > 0:
                    spinner_text = "Retrying with an alternate job link..."
                with st.spinner(spinner_text):
                    fetched_title, fetched_jd = fetch_job_description(candidate_url)
                if fetched_jd:
                    match["jd_text"] = fetched_jd
                    match["url"] = candidate_url
                    if not match.get("title") and fetched_title:
                        match["title"] = fetched_title
                    queue_match_for_resume(
                        fetched_jd,
                        "Fetched and loaded this job description into the Resume Tailor tab.",
                    )
                    return
            except Exception as exc:
                last_error = str(exc)

        if last_error:
            st.error(f"Could not fetch the job description: {last_error}")
        else:
            st.error("I could not recover JD text for this role yet.")
        return

    st.error("This entry does not have a job URL or saved JD text yet.")


def render_match_list(
    *,
    matches: list[dict[str, Any]],
    warnings: list[str],
    title: str,
    download_label: str,
    download_file_name: str,
    button_prefix: str,
) -> None:
    stamp_matches(matches)
    if sync_applied_checkbox_state(matches, button_prefix):
        st.rerun()

    if warnings:
        with st.expander("Warnings"):
            for warning in warnings:
                st.write(f"- {warning}")

    if not matches:
        return

    applied_jobs = load_applied_jobs()
    active_matches, applied_matches = split_matches_by_applied_status(matches, applied_jobs)
    assign_match_ranks(active_matches)
    assign_match_ranks(applied_matches)

    st.subheader(title)
    st.download_button(
        download_label,
        json.dumps(matches, indent=2, ensure_ascii=False),
        file_name=download_file_name,
        mime="application/json",
    )
    if active_matches:
        st.caption(f"Pending applications: {len(active_matches)} | Applied: {len(applied_matches)}")
    else:
        st.caption(f"All loaded roles are already marked applied. Applied: {len(applied_matches)}")

    for index, match in enumerate(active_matches):
        st.markdown(f"### {match['rank']}. {match['title']}")

        caption_bits: list[str] = []
        if match.get("source_name"):
            caption_bits.append(str(match["source_name"]))
        if match.get("career_ops_score"):
            caption_bits.append(f"Career-Ops score: {match['career_ops_score']}")
        if match.get("jobspy_site"):
            caption_bits.append(f"JobSpy: {match['jobspy_site']}")
        if match.get("url"):
            caption_bits.append(str(match["url"]))
        st.caption(" | ".join(caption_bits) or "No job URL available")

        details_bits: list[str] = []
        if match.get("company"):
            details_bits.append(f"Company: {match['company']}")
        elif match.get("career_ops_company"):
            details_bits.append(f"Company: {match['career_ops_company']}")
        if match.get("location"):
            details_bits.append(f"Location: {match['location']}")
        if match.get("jobspy_search_scope"):
            details_bits.append(f"Scope: {match['jobspy_search_scope']}")
        if match.get("jobspy_date_posted"):
            details_bits.append(f"Posted: {match['jobspy_date_posted']}")
        if match.get("jobspy_job_type"):
            details_bits.append(f"Type: {match['jobspy_job_type']}")
        if match.get("jobspy_is_remote"):
            details_bits.append("Remote")
        if match.get("jobspy_salary"):
            details_bits.append(f"Salary: {match['jobspy_salary']}")
        if match.get("jobspy_company_industry"):
            details_bits.append(f"Industry: {match['jobspy_company_industry']}")
        if match.get("jobspy_startup_score"):
            details_bits.append(f"Startup bias: {match['jobspy_startup_score']}")
        if match.get("jobspy_visa_support_label"):
            details_bits.append(f"Visa: {match['jobspy_visa_support_label']}")
        if match.get("jobspy_sponsorship_filter_exempt"):
            details_bits.append("Internship exempt")
        if match.get("career_ops_status"):
            details_bits.append(f"Status: {match['career_ops_status']}")
        if details_bits:
            st.write("Details: " + " | ".join(details_bits))
        if match.get("jobspy_startup_signals"):
            st.write(f"Startup signals: {match['jobspy_startup_signals']}")
        if match.get("jobspy_visa_support_signals"):
            st.write(f"Visa signals: {match['jobspy_visa_support_signals']}")

        if match.get("career_ops_report_path"):
            st.write(f"Career-Ops report: {match['career_ops_report_path']}")
        if match.get("career_ops_notes"):
            st.write(f"Notes: {match['career_ops_notes']}")

        st.checkbox(
            "Mark as applied",
            key=f"applied_toggle_{button_prefix}_{match['match_key']}",
            value=False,
            help="Checked roles are saved locally, hidden from the main results next time, and moved into the applied section below.",
        )

        if st.button("Use This JD in Resume Tailor", key=f"use_job_{button_prefix}_{index}"):
            load_match_into_resume(match)

        with st.expander("Preview crawled JD"):
            st.text(str(match.get("jd_text", ""))[:5000] or "No JD text available yet.")

    if applied_matches:
        st.markdown("### Applied Roles")
        st.caption("Unchecked roles will move back into the active list.")
        for index, match in enumerate(applied_matches):
            st.markdown(f"### {match['rank']}. {match['title']}")

            caption_bits: list[str] = []
            if match.get("source_name"):
                caption_bits.append(str(match["source_name"]))
            if match.get("career_ops_score"):
                caption_bits.append(f"Career-Ops score: {match['career_ops_score']}")
            if match.get("jobspy_site"):
                caption_bits.append(f"JobSpy: {match['jobspy_site']}")
            if match.get("url"):
                caption_bits.append(str(match["url"]))
            st.caption(" | ".join(caption_bits) or "No job URL available")

            details_bits: list[str] = []
            if match.get("company"):
                details_bits.append(f"Company: {match['company']}")
            elif match.get("career_ops_company"):
                details_bits.append(f"Company: {match['career_ops_company']}")
            if match.get("location"):
                details_bits.append(f"Location: {match['location']}")
            if match.get("applied_at"):
                details_bits.append(f"Applied at: {match['applied_at']}")
            if match.get("career_ops_status"):
                details_bits.append(f"Status: {match['career_ops_status']}")
            if details_bits:
                st.write("Details: " + " | ".join(details_bits))
            if match.get("career_ops_notes"):
                st.write(f"Notes: {match['career_ops_notes']}")

            st.checkbox(
                "Mark as applied",
                key=f"applied_toggle_{button_prefix}_{match['match_key']}",
                value=True,
            )

            if st.button("Use This JD in Resume Tailor", key=f"use_applied_job_{button_prefix}_{index}"):
                load_match_into_resume(match)

            with st.expander("Preview crawled JD", expanded=False):
                st.text(str(match.get("jd_text", ""))[:5000] or "No JD text available yet.")


def render_resume_tab() -> None:
    st.caption("Paste a JD, generate a one-page resume based on your fixed template.")
    resume_load_message = st.session_state.pop("_resume_load_message", "")
    if resume_load_message:
        st.success(resume_load_message)

    jd = st.text_area("Job Description", height=320, placeholder="Paste the full JD here...", key="jd_input")
    file_stem = st.text_input("Output file name", value="tailored_resume")

    col1, col2 = st.columns(2)
    with col1:
        generate = st.button("Generate Resume", type="primary")
    with col2:
        generate_pdf = st.checkbox("Generate PDF after generating", value=False)

    if generate:
        if not jd.strip():
            st.error("Please paste a JD first.")
            return
        try:
            with st.spinner("Selecting content and generating resume fields..."):
                payload, generation_usage, prompt_stats = call_model(jd)
                payload, compression_usage = maybe_compress(payload, jd=jd)
                total_usage = merge_usage(generation_usage, compression_usage)

            tex = render_resume(DATA_DIR / "master_resume.tex", payload)
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            tex_path = OUTPUT_DIR / f"{file_stem}.tex"
            tex_path.write_text(tex, encoding="utf-8")
            json_path = OUTPUT_DIR / f"{file_stem}.json"
            json_path.write_text(payload.model_dump_json(indent=2), encoding="utf-8")
            docx_path = OUTPUT_DIR / f"{file_stem}.docx"

            docx_error = None
            try:
                render_docx(docx_path, payload)
            except Exception as docx_exc:
                docx_error = str(docx_exc)

            st.success("Generated resume files successfully.")
            st.subheader("Generation Stats")
            original_context_chars = prompt_stats["experience_library_chars"] + prompt_stats["project_library_chars"]
            reduced_context_chars = prompt_stats["experience_context_chars"] + prompt_stats["project_context_chars"]
            reduction_pct = 0
            if original_context_chars:
                reduction_pct = round((1 - (reduced_context_chars / original_context_chars)) * 100)
            if reduction_pct > 0:
                st.caption(
                    "Prompt context trimmed from "
                    f"{original_context_chars} to {reduced_context_chars} chars "
                    f"({reduction_pct}% smaller) before the model call."
                )
            else:
                st.caption("Prompt context kept functionally complete; only formatting-level compaction was applied.")
            usage_col1, usage_col2, usage_col3 = st.columns(3)
            usage_col1.metric("Input Tokens", f"{total_usage['input_tokens']:,}")
            usage_col2.metric("Output Tokens", f"{total_usage['output_tokens']:,}")
            usage_col3.metric("Cached Input Tokens", f"{total_usage['cached_input_tokens']:,}")
            if total_usage["reasoning_tokens"]:
                st.caption(f"Reasoning tokens: {total_usage['reasoning_tokens']:,}")
            if compression_usage:
                st.caption("A second compression model pass was used for this run.")
            else:
                st.caption("A second compression model pass was not needed for this run.")
            st.subheader("Selected experiences")
            st.json([e.model_dump() for e in payload.experiences])
            st.subheader("Selected projects")
            st.json([p.model_dump() for p in payload.projects])
            st.download_button("Download .tex", tex, file_name=tex_path.name, mime="text/x-tex")
            st.download_button("Download JSON", json_path.read_text(encoding="utf-8"), file_name=json_path.name, mime="application/json")
            if docx_path.exists():
                st.download_button(
                    "Download .docx",
                    docx_path.read_bytes(),
                    file_name=docx_path.name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            elif docx_error:
                st.warning(f"Word export failed: {docx_error}")

            if generate_pdf:
                ok, log, pdf_path, pdf_method = compile_pdf(
                    tex_path,
                    docx_path if docx_path.exists() else None,
                )
                if ok:
                    method_label = {
                        "word": "Word",
                        "pages": "Pages",
                        "latex": "LaTeX",
                    }.get(pdf_method or "", "PDF")
                    st.success(f"PDF generated successfully via {method_label}.")
                    st.download_button(
                        "Download PDF",
                        pdf_path.read_bytes(),
                        file_name=pdf_path.name,
                        mime="application/pdf",
                    )
                else:
                    st.warning("PDF generation was not completed.")
                    st.code(log[:4000] or "No compiler output.")
                    if not pdf_export_available():
                        st.info("Install Microsoft Word, Pages, or TeX Live/MiKTeX, then rerun with PDF generation enabled.")

            with st.expander("Preview generated LaTeX"):
                st.code(tex, language="latex")

        except Exception as exc:
            st.error(f"Generation failed: {exc}")


def render_jobspy_tab() -> None:
    st.caption("Search with JobSpy, prioritize Tucson ZIP 85716, widen to North America, then send a role into Resume Tailor.")
    if not jobspy_available():
        st.warning(jobspy_install_hint())

    load_config()
    default_scope_text = os.getenv("JOBSPY_SCOPE_TEXT", "").strip() or DEFAULT_JOBSPY_SCOPE_TEXT
    configured_sites = [site.strip().lower() for site in os.getenv("JOBSPY_SITES", "").split(",") if site.strip()]
    default_sites = configured_sites or list(DEFAULT_JOBSPY_SITES)
    prefer_startups_default = os.getenv("JOBSPY_PREFER_STARTUPS", "true").strip().lower() in {"1", "true", "yes", "on"}
    require_sponsorship_default = os.getenv("JOBSPY_REQUIRE_SPONSORSHIP", "true").strip().lower() in {"1", "true", "yes", "on"}

    with st.form("jobspy_search_form"):
        search_term = st.text_input(
            "Search term",
            value=st.session_state.get("jobspy_search_term", ""),
            placeholder="e.g. data analyst OR business analyst OR product analyst",
        )
        scope_text = st.text_area(
            "Search scopes",
            value=st.session_state.get("jobspy_scope_text", default_scope_text),
            height=120,
            help=(
                "One scope per line. Use `Location | Country`. Defaults prioritize Tucson, AZ 85716 first, "
                "then USA, Canada, and Mexico."
            ),
        )

        controls_col1, controls_col2, controls_col3 = st.columns(3)
        with controls_col1:
            site_names = st.multiselect(
                "Sources",
                options=list(SUPPORTED_JOBSPY_SITES),
                default=default_sites,
            )
            results_wanted = int(
                st.number_input(
                    "Results per site",
                    min_value=5,
                    max_value=50,
                    value=15,
                    step=5,
                )
            )
        with controls_col2:
            hours_old_label = st.selectbox(
                "Recency",
                options=["Any time", "24 hours", "72 hours", "7 days", "30 days"],
                index=2,
            )
            job_type_label = st.selectbox(
                "Job type",
                options=["Any", "fulltime", "internship", "contract", "parttime"],
                index=0,
            )
        with controls_col3:
            remote_only = st.checkbox("Remote only", value=False)
            easy_apply_only = st.checkbox("Easy apply only", value=False)
            prefer_startups = st.checkbox("Prefer startups", value=prefer_startups_default)
            require_sponsorship = st.checkbox("Need sponsorship for non-internships", value=require_sponsorship_default)
            linkedin_fetch_description = st.checkbox("Fetch LinkedIn descriptions", value=True)

        search_jobspy_button = st.form_submit_button("Search JobSpy", type="primary")

    if search_jobspy_button:
        st.session_state["jobspy_search_term"] = search_term
        st.session_state["jobspy_scope_text"] = scope_text

        if not search_term.strip():
            st.error("Please add a search term first.")
        elif not site_names:
            st.error("Choose at least one JobSpy source.")
        else:
            hours_old = {
                "Any time": None,
                "24 hours": 24,
                "72 hours": 72,
                "7 days": 168,
                "30 days": 720,
            }[hours_old_label]
            job_type = None if job_type_label == "Any" else job_type_label

            try:
                with st.spinner("Searching JobSpy across your prioritized North America scopes..."):
                    opportunities, bridge_warnings = search_jobspy_jobs(
                        search_term=search_term.strip(),
                        scope_text=scope_text,
                        site_names=site_names,
                        results_wanted=results_wanted,
                        hours_old=hours_old,
                        job_type=job_type,
                        remote_only=remote_only,
                        easy_apply_only=easy_apply_only,
                        linkedin_fetch_description=linkedin_fetch_description,
                        prefer_startups=prefer_startups,
                        require_sponsorship=require_sponsorship,
                    )

                merged_matches: list[dict[str, Any]] = []
                for item in opportunities:
                    merged_matches.append(
                        {
                            "rank": 0,
                            "title": item.title or "Untitled role",
                            "url": item.url or item.direct_url,
                            "jd_text": item.jd_text,
                            "source_name": "JobSpy",
                            "company": item.company,
                            "location": item.location,
                            "jobspy_site": item.site,
                            "jobspy_search_scope": item.search_scope,
                            "jobspy_date_posted": item.date_posted,
                            "jobspy_is_remote": item.is_remote,
                            "jobspy_job_type": item.job_type,
                            "jobspy_salary": item.salary_text,
                            "jobspy_board_url": item.board_url,
                            "jobspy_direct_url": item.direct_url,
                            "jobspy_company_industry": item.company_industry,
                            "jobspy_startup_score": item.startup_score,
                            "jobspy_startup_signals": item.startup_signals,
                            "jobspy_visa_support_label": item.visa_support_label,
                            "jobspy_visa_support_signals": item.visa_support_signals,
                            "jobspy_sponsorship_filter_exempt": item.sponsorship_filter_exempt,
                        }
                    )

                assign_match_ranks(merged_matches)
                st.session_state["jobspy_matches"] = merged_matches
                st.session_state["jobspy_warnings"] = bridge_warnings

                if merged_matches:
                    st.success(
                        f"Loaded {len(merged_matches)} JobSpy roles with Tucson ZIP 85716 prioritized first."
                    )
                else:
                    st.warning("JobSpy did not return any roles for this search yet.")
            except Exception as exc:
                st.error(f"JobSpy search failed: {exc}")

    render_match_list(
        matches=st.session_state.get("jobspy_matches", []),
        warnings=st.session_state.get("jobspy_warnings", []),
        title="JobSpy Matches",
        download_label="Download JobSpy Roles JSON",
        download_file_name="jobspy_roles.json",
        button_prefix="jobspy",
    )


def render_career_ops_tab() -> None:
    st.caption("Use Career-Ops to scan portals, keep scored roles, then send one role into Resume Tailor.")
    load_config()
    configured_career_ops_dir = os.getenv("CAREER_OPS_DIR", "").strip()
    default_career_ops = configured_career_ops_dir or str(default_career_ops_dir(BASE_DIR))

    st.markdown("### Career-Ops Bridge")
    st.caption(
        "Use `career-ops` as the portal scanner and high-score tracker, then hand selected jobs back into Resume Tailor."
    )
    bridge_col1, bridge_col2, bridge_col3 = st.columns([2.4, 1, 1])
    with bridge_col1:
        career_ops_dir_text = st.text_input("Career-Ops path", value=default_career_ops, key="career_ops_dir")
    with bridge_col2:
        minimum_career_ops_score = st.number_input(
            "Min score",
            min_value=0.0,
            max_value=5.0,
            value=4.0,
            step=0.1,
            key="career_ops_min_score",
        )
    with bridge_col3:
        dry_run_scan = st.checkbox("Dry-run scan", value=False, key="career_ops_dry_run")

    scan_company = st.text_input(
        "Optional company filter",
        value="",
        placeholder="e.g. OpenAI",
        key="career_ops_company_filter",
    )
    scan_button_col, import_button_col = st.columns(2)
    run_career_ops_scan_button = scan_button_col.button("Run Career-Ops Scan")
    import_career_ops_button = import_button_col.button("Load High-Score Career-Ops Jobs")

    career_ops_dir = Path(career_ops_dir_text).expanduser()
    if run_career_ops_scan_button:
        if not career_ops_available(career_ops_dir):
            st.error(career_ops_install_hint(career_ops_dir))
        else:
            try:
                with st.spinner("Running career-ops portal scan..."):
                    ok, output = run_career_ops_scan(
                        career_ops_dir,
                        company=scan_company,
                        dry_run=dry_run_scan,
                    )
                if ok:
                    st.success("Career-ops scan completed.")
                else:
                    st.warning("Career-ops scan finished with an error.")
                if output:
                    st.code(output[:8000])
            except Exception as exc:
                st.error(f"Career-ops scan failed: {exc}")

    if import_career_ops_button:
        if not career_ops_available(career_ops_dir):
            st.error(career_ops_install_hint(career_ops_dir))
        else:
            try:
                with st.spinner("Loading high-score career-ops opportunities and preparing Resume Tailor handoff..."):
                    opportunities, bridge_warnings = load_high_score_opportunities(
                        career_ops_dir,
                        minimum_score=float(minimum_career_ops_score),
                    )

                    merged_matches: list[dict[str, Any]] = []
                    for item in opportunities:
                        match = {
                            "rank": 0,
                            "title": item.title,
                            "url": item.url,
                            "jd_text": item.jd_text,
                            "source_name": "Career-Ops",
                            "company": item.company,
                        }

                        match["career_ops_score"] = item.score_raw or (f"{item.score_value:.2f}/5" if item.score_value else "")
                        match["career_ops_score_value"] = item.score_value or 0.0
                        match["career_ops_status"] = item.status
                        match["career_ops_company"] = item.company
                        match["career_ops_report_path"] = item.report_path
                        match["career_ops_pdf_path"] = item.pdf_path
                        match["career_ops_notes"] = item.notes
                        merged_matches.append(match)

                    merged_matches.sort(
                        key=lambda item: (
                            float(item.get("career_ops_score_value", 0) or 0),
                            str(item.get("title", "")).lower(),
                        ),
                        reverse=True,
                    )
                    assign_match_ranks(merged_matches)

                st.session_state["career_ops_matches"] = merged_matches
                st.session_state["career_ops_warnings"] = bridge_warnings
                st.success(
                    f"Imported {len(merged_matches)} high-score career-ops roles "
                    f"(threshold {minimum_career_ops_score:.1f}/5)."
                )
            except Exception as exc:
                st.error(f"Career-ops import failed: {exc}")

    render_match_list(
        matches=st.session_state.get("career_ops_matches", []),
        warnings=st.session_state.get("career_ops_warnings", []),
        title="High-Score Roles",
        download_label="Download Career-Ops Roles JSON",
        download_file_name="career_ops_roles.json",
        button_prefix="career_ops",
    )


def main() -> None:
    st.set_page_config(page_title="Resume Tailor", layout="wide")
    st.title("Resume Tailor")
    sync_jd_from_query_params()

    resume_tab, jobspy_tab, career_ops_tab = st.tabs(["Resume Tailor", "JobSpy", "Career-Ops"])
    with resume_tab:
        render_resume_tab()
    with jobspy_tab:
        render_jobspy_tab()
    with career_ops_tab:
        render_career_ops_tab()


if __name__ == "__main__":
    main()
