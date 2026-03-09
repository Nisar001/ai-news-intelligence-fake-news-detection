from __future__ import annotations

from functools import lru_cache

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_model_bundle():
    settings = get_settings()
    try:
        tokenizer = AutoTokenizer.from_pretrained(settings.hf_model_name, revision=settings.hf_model_revision)
        model = AutoModelForSequenceClassification.from_pretrained(settings.hf_model_name, revision=settings.hf_model_revision)
        if settings.hf_use_gpu and torch.cuda.is_available():
            model.to("cuda")
        model.eval()
        return tokenizer, model
    except Exception:
        return None


def _fallback_classification(text: str) -> dict:
    settings = get_settings()
    normalized = text.lower()
    fake_terms = [
        "hoax",
        "conspiracy",
        "fabricated",
        "unverified",
        "rumor",
        "clickbait",
        "shocking truth",
    ]
    real_terms = [
        "official",
        "according to",
        "report",
        "statement",
        "data",
        "confirmed",
    ]

    fake_hits = sum(1 for t in fake_terms if t in normalized)
    real_hits = sum(1 for t in real_terms if t in normalized)
    total = max(fake_hits + real_hits, 1)
    fake_score = fake_hits / total
    real_score = real_hits / total
    confidence = max(fake_score, real_score)

    if confidence < settings.model_low_confidence_threshold:
        classification = "UNCERTAIN"
    else:
        classification = "FAKE" if fake_score >= real_score else "REAL"

    return {
        "classification": classification,
        "confidence": float(confidence),
        "scores": {"FAKE": float(fake_score), "REAL": float(real_score)},
        "attention_weights": {},
        "model_name": f"{settings.hf_model_name}-fallback",
    }


def classify_article(text: str) -> dict:
    settings = get_settings()
    bundle = get_model_bundle()
    if bundle is None:
        return _fallback_classification(text)
    tokenizer, model = bundle

    encoded = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=settings.model_max_tokens,
    )
    if settings.hf_use_gpu and torch.cuda.is_available():
        encoded = {k: v.to("cuda") for k, v in encoded.items()}

    with torch.no_grad():
        output = model(**encoded)
        probs = torch.softmax(output.logits, dim=-1).squeeze(0).cpu().tolist()

    id2label = model.config.id2label
    scores = {id2label[i]: float(p) for i, p in enumerate(probs)}

    fake_score = 0.0
    real_score = 0.0
    for label, score in scores.items():
        upper = label.upper()
        if settings.model_label_fake in upper:
            fake_score = max(fake_score, score)
        if settings.model_label_real in upper:
            real_score = max(real_score, score)

    confidence = max(fake_score, real_score)
    margin = abs(fake_score - real_score)

    if confidence < settings.model_low_confidence_threshold or margin < settings.model_uncertain_margin:
        classification = "UNCERTAIN"
    else:
        classification = "FAKE" if fake_score >= real_score else "REAL"

    attention_weights = {}
    if hasattr(output, "attentions") and output.attentions:
        attention_weights = {"layers": len(output.attentions)}

    return {
        "classification": classification,
        "confidence": confidence,
        "scores": scores,
        "attention_weights": attention_weights,
        "model_name": settings.hf_model_name,
    }
