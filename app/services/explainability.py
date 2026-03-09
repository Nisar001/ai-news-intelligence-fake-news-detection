from __future__ import annotations


def build_reasoning_summary(classification: str, confidence: float, keywords: list[str], sentiment: dict) -> str:
    top_keywords = ", ".join(keywords[:8]) if keywords else "none"
    compound = sentiment.get("compound", 0.0)
    return (
        f"Classification={classification}, confidence={confidence:.3f}. "
        f"Key terms: {top_keywords}. Sentiment compound={compound:.3f}."
    )
