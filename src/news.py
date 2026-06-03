"""Per-stock news + lightweight rule-based sentiment (Tier 3).

Headlines come free from the active data source (yfinance `.news`). Sentiment is
a transparent keyword score — no paid NLP API. It's a rough signal, clearly
labeled as such. Gracefully returns empty when no news is available.

NOT financial advice.
"""
from __future__ import annotations

from .config import get_config
from .datasources import get_source

POSITIVE = {
    "surge", "soar", "jump", "rise", "gain", "beat", "beats", "record", "high",
    "profit", "growth", "grow", "up", "upgrade", "outperform", "buy", "strong",
    "rally", "expand", "dividend", "boost", "win", "wins", "approve", "approved",
    "naik", "untung", "laba", "tumbuh", "rekor", "kuat", "positif",
}
NEGATIVE = {
    "fall", "drop", "plunge", "slump", "loss", "losses", "miss", "misses", "cut",
    "down", "downgrade", "underperform", "sell", "weak", "decline", "fraud",
    "probe", "lawsuit", "default", "debt", "warn", "warning", "halt", "suspend",
    "turun", "rugi", "anjlok", "lemah", "negatif", "gagal", "tunda",
}


def _score_title(title: str) -> int:
    words = {w.strip(".,!?:;()'\"").lower() for w in title.split()}
    return len(words & POSITIVE) - len(words & NEGATIVE)


def sentiment_label(score: int, lang: str = "EN") -> str:
    if score > 0:
        return "🟢 positif" if lang == "ID" else "🟢 positive"
    if score < 0:
        return "🔴 negatif" if lang == "ID" else "🔴 negative"
    return "⚪ netral" if lang == "ID" else "⚪ neutral"


def get_news(symbol: str, limit: int = 6) -> dict:
    """Return {items:[{title,publisher,link,sentiment,score}], overall, overall_score}."""
    cfg = get_config()
    src = get_source(cfg["data"]["source"])
    try:
        raw = src.news(symbol, limit=limit)
    except Exception:
        raw = []
    items, total = [], 0
    for it in raw:
        # synthetic source may pre-tag _sent; otherwise score the title
        if it.get("_sent") == "pos":
            sc = 1
        elif it.get("_sent") == "neg":
            sc = -1
        elif it.get("_sent") == "neu":
            sc = 0
        else:
            sc = _score_title(it.get("title", ""))
        total += sc
        items.append({**it, "score": sc})
    overall = "neutral"
    if total > 0:
        overall = "positive"
    elif total < 0:
        overall = "negative"
    return {"items": items, "overall": overall, "overall_score": total}
