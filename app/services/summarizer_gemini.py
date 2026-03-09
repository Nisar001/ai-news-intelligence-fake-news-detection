from __future__ import annotations

import json
from functools import lru_cache

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings, load_yaml_config
from app.core.exceptions import DomainError


@lru_cache(maxsize=1)
def configure_gemini() -> None:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise DomainError("GEMINI_KEY_MISSING", "Gemini API key is not configured", 500)
    genai.configure(api_key=settings.gemini_api_key)


@retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3), reraise=True)
def _generate_once(model_name: str, prompt: str, timeout: int):
    model = genai.GenerativeModel(model_name)
    return model.generate_content(prompt, request_options={"timeout": timeout})


def generate_summary(
    article: str,
    label: str,
    confidence: float,
    entities: list[dict],
    sentiment: dict,
) -> dict:
    configure_gemini()
    settings = get_settings()
    prompt_cfg = load_yaml_config(settings.prompts_config_path)

    template = prompt_cfg.get("summary_user_template", "{article}")
    prompt = template.format(
        article=article,
        label=label,
        confidence=round(confidence, 4),
        entities=entities,
        sentiment=sentiment,
    )

    models_to_try = [settings.gemini_primary_model, settings.gemini_fallback_model]
    last_error = None

    for model_name in models_to_try:
        try:
            resp = _generate_once(model_name=model_name, prompt=prompt, timeout=settings.gemini_timeout_seconds)
            txt = (resp.text or "{}").strip()
            parsed = json.loads(txt)
            return {
                "executive_summary": parsed.get("executive_summary", ""),
                "detailed_summary": parsed.get("detailed_summary", ""),
                "risk_analysis": parsed.get("risk_analysis", ""),
                "reasoning": parsed.get("reasoning", ""),
                "suspicious_claims": parsed.get("suspicious_claims", []),
                "model": model_name,
            }
        except Exception as exc:
            last_error = exc
            continue

    raise DomainError("SUMMARY_FAILED", f"Gemini summarization failed: {last_error}", 502)
