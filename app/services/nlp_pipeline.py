from __future__ import annotations

from functools import lru_cache

import nltk
import spacy
from nltk.sentiment import SentimentIntensityAnalyzer

from app.core.config import get_settings, load_yaml_config


@lru_cache(maxsize=1)
def get_nlp_model():
    try:
        return spacy.load("en_core_web_sm")
    except Exception:
        # Fallback for local environments where the model isn't installed yet.
        return spacy.blank("en")


@lru_cache(maxsize=1)
def get_sentiment_model():
    try:
        nltk.data.find("sentiment/vader_lexicon.zip")
    except LookupError:
        try:
            nltk.download("vader_lexicon", quiet=True, raise_on_error=False)
        except Exception:
            return None

    try:
        return SentimentIntensityAnalyzer()
    except Exception:
        return None


def process_text(text: str) -> dict:
    settings = get_settings()
    cfg = load_yaml_config(settings.app_config_path).get("pipeline", {})

    nlp = get_nlp_model()
    doc = nlp(text)

    tokens = [t.text for t in doc] if cfg.get("tokenize", True) else []
    lemmas = [t.lemma_ for t in doc if not t.is_space] if cfg.get("lemmatize", True) else []
    filtered_tokens = [t.lemma_.lower() for t in doc if not t.is_stop and t.is_alpha] if cfg.get("remove_stopwords", True) else lemmas

    entities = []
    if cfg.get("ner", True):
        entities = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]

    sentiment = {}
    if cfg.get("sentiment", True):
        sentiment_model = get_sentiment_model()
        if sentiment_model is not None:
            sentiment = sentiment_model.polarity_scores(text)

    keyword_freq = {}
    for tok in filtered_tokens:
        keyword_freq[tok] = keyword_freq.get(tok, 0) + 1

    important_keywords = [k for k, _ in sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:15]]

    return {
        "cleaned_text": " ".join([t.text for t in doc if not t.is_space]),
        "tokens": tokens,
        "lemmas": lemmas,
        "filtered_tokens": filtered_tokens,
        "entities": entities,
        "sentiment": sentiment,
        "important_keywords": important_keywords,
        "feature_vector": {
            "token_count": len(tokens),
            "entity_count": len(entities),
            "keyword_count": len(important_keywords),
            "sentiment_compound": sentiment.get("compound", 0.0),
        },
    }
