from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.prompts import SYSTEM_PROMPT, USER_TEMPLATE, COMPRESS_TEMPLATE
from app.context_builder import build_prompt_context
from app.renderer import render_resume
from app.schema import ResumePayload
from app.compiler import compile_pdf, pdf_export_available
from app.docx_renderer import render_docx
from app.job_finder import (
    find_top_jobs,
    load_job_search_config,
    parse_job_urls,
    serialize_job_matches,
)
from app.job_digest import run_job_digest

DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"


def read_file(name: str) -> str:
    return (DATA_DIR / name).read_text(encoding="utf-8")


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


def compress_payload(payload: ResumePayload, percent: int = 12) -> tuple[ResumePayload, dict[str, int]]:
    client = get_client()
    request_kwargs = {
        "model": get_model(),
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": COMPRESS_TEMPLATE.format(
                    percent=percent,
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
        total += len(proj.title) + len(proj.bullet)
    return total


def maybe_compress(payload: ResumePayload) -> tuple[ResumePayload, dict[str, int]]:
    # Conservative heuristic for this template.
    if compress_pass_enabled() and estimated_length_score(payload) > 2500:
        return compress_payload(payload, percent=15)
    return payload, {}


def sync_jd_from_query_params() -> None:
    query_jd = st.query_params.get("jd", "")
    previous_query_jd = st.session_state.get("_last_query_jd", "")

    if "jd_input" not in st.session_state:
        st.session_state["jd_input"] = query_jd
    elif query_jd and query_jd != previous_query_jd:
        st.session_state["jd_input"] = query_jd

    st.session_state["_last_query_jd"] = query_jd


def render_resume_tab() -> None:
    st.caption("Paste a JD, generate a one-page resume based on your fixed template.")
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
                payload, compression_usage = maybe_compress(payload)
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


def render_job_finder_tab() -> None:
    st.caption("Paste public job URLs, crawl them with Crawl4AI, rank locally, then send one JD into Resume Tailor.")
    config = load_job_search_config(DATA_DIR / "job_search_config.yml")

    urls_text = st.text_area(
        "Job URLs",
        height=220,
        placeholder="Paste one public job URL per line...",
        key="job_urls_input",
    )
    st.caption(
        f"Current local filter: Top {config.top_k}, minimum score {config.minimum_score}. "
        "Edit `data/job_search_config.yml` to tune titles, seniority exclusions, and locations."
    )
    st.caption(
        "LIMI visa filter is enabled: full-time roles are ranked for future sponsorship fit; "
        "OPT/STEM-OPT language is treated as a positive signal; internships are not blocked for lacking sponsorship."
    )

    st.markdown("### Daily Careers Digest")
    st.caption(
        "Configured careers pages from `data/company_careers.yml` are combined with a built-in "
        "`newgrad-jobs.com` data feed. The digest writes latest files to "
        "`outputs/job_digest/top_13_jobs.json` and `.csv`."
    )
    run_digest_now = st.button("Run Careers Digest Now")
    if run_digest_now:
        try:
            with st.spinner("Discovering job links from careers pages and building the Top 13 digest..."):
                digest = run_job_digest(
                    careers_config_path=DATA_DIR / "company_careers.yml",
                    search_config_path=DATA_DIR / "job_search_config.yml",
                    experience_library_path=DATA_DIR / "experience_library.md",
                    project_library_path=DATA_DIR / "project_library.md",
                    output_dir=OUTPUT_DIR / "job_digest",
                )
            st.session_state["job_matches"] = digest.top_matches
            st.session_state["job_match_warnings"] = digest.warnings
            st.success(
                f"Daily digest updated. Discovered {len(digest.discovered_links)} candidate links and kept "
                f"{len(digest.top_matches)} ranked jobs."
            )
        except Exception as exc:
            st.error(f"Daily digest failed: {exc}")

    st.divider()
    st.markdown("### newgrad-jobs.com Data Feed")
    st.caption("Auto-discovers Data-related postings from newgrad-jobs.com and ranks them with your LIMI filters.")
    fetch_newgrad_jobs = st.button("Fetch Data Jobs From newgrad-jobs.com")
    if fetch_newgrad_jobs:
        try:
            with st.spinner("Discovering Data-related jobs from newgrad-jobs.com and ranking local matches..."):
                digest = run_job_digest(
                    careers_config_path=DATA_DIR / "company_careers.yml",
                    search_config_path=DATA_DIR / "job_search_config.yml",
                    experience_library_path=DATA_DIR / "experience_library.md",
                    project_library_path=DATA_DIR / "project_library.md",
                    output_dir=OUTPUT_DIR / "job_digest",
                    include_company_careers=False,
                    include_newgrad_jobs=True,
                )
            st.session_state["job_matches"] = digest.top_matches
            st.session_state["job_match_warnings"] = digest.warnings
            st.success(
                f"newgrad-jobs.com scan complete. Discovered {len(digest.discovered_links)} candidate links and kept "
                f"{len(digest.top_matches)} ranked jobs."
            )
        except Exception as exc:
            st.error(f"newgrad-jobs.com scan failed: {exc}")

    st.divider()
    st.markdown("### Manual Job URLs")

    fetch_jobs = st.button("Fetch and Rank Jobs", type="primary")

    if fetch_jobs:
        urls = parse_job_urls(urls_text)
        if not urls:
            st.error("Please paste at least one public job URL.")
        else:
            try:
                with st.spinner("Crawling job pages and ranking local matches..."):
                    matches, warnings = find_top_jobs(
                        urls=urls,
                        experience_library_text=read_file("experience_library.md"),
                        project_library_text=read_file("project_library.md"),
                        config_path=DATA_DIR / "job_search_config.yml",
                    )
                st.session_state["job_matches"] = [match.__dict__ for match in matches]
                st.session_state["job_match_warnings"] = warnings
            except Exception as exc:
                st.error(f"Job finder failed: {exc}")

    matches = st.session_state.get("job_matches", [])
    warnings = st.session_state.get("job_match_warnings", [])

    if warnings:
        with st.expander("Crawl warnings"):
            for warning in warnings:
                st.write(f"- {warning}")

    if matches:
        st.subheader("Top Matches")
        st.download_button(
            "Download Top Jobs JSON",
            serialize_job_matches(matches),
            file_name="top_jobs.json",
            mime="application/json",
        )
        for index, match in enumerate(matches):
            st.markdown(f"### {match['rank']}. {match['title']}")
            st.caption(f"Score: {match['score']} | {match['url']}")
            if match.get("role_type") or match.get("visa_status"):
                role_label = match.get("role_type", "unknown")
                st.write(f"Role type: {role_label}")
                st.write(f"Visa fit: {match.get('visa_status', 'Not evaluated')}")
            if match.get("visa_evidence"):
                st.write("Visa signals: " + ", ".join(match["visa_evidence"]))
            if match.get("matched_terms"):
                st.write("Matched terms: " + ", ".join(match["matched_terms"]))
            for highlight in match.get("highlights", []):
                st.write(f"- {highlight}")
            button_key = f"use_job_{index}"
            if st.button("Use This JD in Resume Tailor", key=button_key):
                st.session_state["jd_input"] = match["jd_text"]
                st.success("Loaded this job description into the Resume Tailor tab.")
            with st.expander("Preview crawled JD"):
                st.text(match["jd_text"][:5000])


def main() -> None:
    st.set_page_config(page_title="Resume Tailor", layout="wide")
    st.title("Resume Tailor")
    sync_jd_from_query_params()

    resume_tab, job_finder_tab = st.tabs(["Resume Tailor", "Job Finder"])
    with resume_tab:
        render_resume_tab()
    with job_finder_tab:
        render_job_finder_tab()


if __name__ == "__main__":
    main()
