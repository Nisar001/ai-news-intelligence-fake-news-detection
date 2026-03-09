from __future__ import annotations

import json
import time
from typing import Any

import requests
import streamlit as st


def build_headers(api_key: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    if api_key.strip():
        headers["x-api-key"] = api_key.strip()
    return headers


def safe_json(response: requests.Response) -> dict[str, Any]:
    try:
        return response.json()
    except Exception:
        return {"raw_response": response.text}


def call_api(method: str, url: str, headers: dict[str, str], payload: dict | None = None) -> tuple[int, dict[str, Any]]:
    response = requests.request(method=method, url=url, headers=headers, json=payload, timeout=60)
    return response.status_code, safe_json(response)


st.set_page_config(page_title="AI News Intelligence UI", layout="wide")
st.title("AI News Intelligence Platform")
st.caption("End-to-end test UI for analyze, summarize, status, and article retrieval.")

if "last_job_id" not in st.session_state:
    st.session_state.last_job_id = ""
if "last_article_id" not in st.session_state:
    st.session_state.last_article_id = ""

with st.sidebar:
    st.header("Connection")
    base_url = st.text_input("Base URL", value="http://localhost:8000")
    api_prefix = st.text_input("API Prefix", value="/api/v1")
    api_key = st.text_input("API Key (x-api-key)", value="local-dev-key", type="password")
    st.divider()
    st.subheader("Saved IDs")
    st.text_input("Last Job ID", value=st.session_state.last_job_id, disabled=True)
    st.text_input("Last Article ID", value=st.session_state.last_article_id, disabled=True)

headers = build_headers(api_key)
base_api = f"{base_url.rstrip('/')}{api_prefix}"

tab_health, tab_analyze, tab_status, tab_article, tab_summarize = st.tabs(
    ["Health", "Analyze", "Status", "Article", "Summarize"]
)

with tab_health:
    st.subheader("Health Check")
    if st.button("Check Health", use_container_width=True):
        try:
            status, body = call_api("GET", f"{base_api}/health", headers)
            st.write({"status_code": status, "response": body})
        except Exception as exc:
            st.error(f"Health check failed: {exc}")

with tab_analyze:
    st.subheader("Analyze Article")
    mode = st.radio("Input Mode", options=["Raw Text", "URL"], horizontal=True)
    include_detailed_summary = st.checkbox("Include detailed summary", value=False)

    payload: dict[str, Any] = {"include_detailed_summary": include_detailed_summary}
    if mode == "Raw Text":
        text = st.text_area("Article Text", height=250)
        payload["text"] = text
    else:
        url = st.text_input("Article URL", value="https://www.bbc.com/news/world-us-canada-66231858")
        payload["url"] = url

    if st.button("Submit Analysis Job", type="primary", use_container_width=True):
        try:
            status, body = call_api("POST", f"{base_api}/analyze", headers, payload)
            st.write({"status_code": status, "response": body})
            if isinstance(body, dict):
                st.session_state.last_job_id = body.get("job_id", st.session_state.last_job_id)
                st.session_state.last_article_id = body.get("article_id", st.session_state.last_article_id)
                if body.get("job_id"):
                    st.success(f"Job created: {body['job_id']}")
        except Exception as exc:
            st.error(f"Analyze failed: {exc}")

with tab_status:
    st.subheader("Job Status")
    job_id = st.text_input("Job ID", value=st.session_state.last_job_id)
    poll_seconds = st.number_input("Auto Poll Seconds", min_value=1, max_value=120, value=3)
    poll_attempts = st.number_input("Auto Poll Attempts", min_value=1, max_value=100, value=10)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Get Status", use_container_width=True):
            if not job_id.strip():
                st.warning("Enter a Job ID first.")
            else:
                try:
                    status, body = call_api("GET", f"{base_api}/status/{job_id.strip()}", headers)
                    st.write({"status_code": status, "response": body})
                except Exception as exc:
                    st.error(f"Status check failed: {exc}")

    with col2:
        if st.button("Auto Poll", use_container_width=True):
            if not job_id.strip():
                st.warning("Enter a Job ID first.")
            else:
                placeholder = st.empty()
                try:
                    for attempt in range(int(poll_attempts)):
                        status, body = call_api("GET", f"{base_api}/status/{job_id.strip()}", headers)
                        placeholder.write(
                            {
                                "attempt": attempt + 1,
                                "status_code": status,
                                "response": body,
                            }
                        )
                        job_status = str(body.get("status", "")).upper()
                        if job_status in {"COMPLETED", "FAILED"}:
                            break
                        time.sleep(int(poll_seconds))
                except Exception as exc:
                    st.error(f"Auto poll failed: {exc}")

with tab_article:
    st.subheader("Article Details")
    article_id = st.text_input("Article ID", value=st.session_state.last_article_id)
    if st.button("Get Article", use_container_width=True):
        if not article_id.strip():
            st.warning("Enter an Article ID first.")
        else:
            try:
                status, body = call_api("GET", f"{base_api}/article/{article_id.strip()}", headers)
                st.write({"status_code": status, "response": body})
            except Exception as exc:
                st.error(f"Article lookup failed: {exc}")

with tab_summarize:
    st.subheader("Summarize Existing Article")
    summarize_article_id = st.text_input("Article ID for summarization", value=st.session_state.last_article_id)
    summarize_detailed = st.checkbox("Detailed summary", value=True)

    if st.button("Create Summarize Job", use_container_width=True):
        if not summarize_article_id.strip():
            st.warning("Enter an Article ID first.")
        else:
            payload = {
                "article_id": summarize_article_id.strip(),
                "include_detailed_summary": summarize_detailed,
            }
            try:
                status, body = call_api("POST", f"{base_api}/summarize", headers, payload)
                st.write({"status_code": status, "response": body})
                if isinstance(body, dict) and body.get("job_id"):
                    st.session_state.last_job_id = body["job_id"]
                    st.success(f"Summarize job created: {body['job_id']}")
            except Exception as exc:
                st.error(f"Summarize request failed: {exc}")

st.divider()
with st.expander("cURL Example"):
    curl_payload = {
        "text": "Your article text here...",
        "include_detailed_summary": False,
    }
    st.code(
        "curl -X POST "
        f"\"{base_api}/analyze\" "
        "-H \"Content-Type: application/json\" "
        f"-H \"x-api-key: {api_key}\" "
        f"-d '{json.dumps(curl_payload)}'",
        language="bash",
    )
