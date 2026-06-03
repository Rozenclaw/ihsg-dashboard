"""Optional AI enrichment for the decision helper (Anthropic Claude API).

Given the deterministic structured analysis from src/decision.py, ask Claude to
write a polished, flowing bilingual (EN/ID) research narrative — grounded ONLY
on the numbers we computed, never inventing data.

Degrades gracefully: returns None (caller falls back to decision.to_markdown)
when the `anthropic` package isn't installed, no API key is configured, or the
API call fails for any reason. Nothing here imports Streamlit — the page passes
the key/model in.
"""
from __future__ import annotations

import os

from . import decision

# The skill default; override via config.yaml `ai.model` if you want a cheaper
# model (e.g. "claude-sonnet-4-6") or to pin a specific version.
DEFAULT_MODEL = "claude-opus-4-8"

# Stable across calls → cacheable prefix. The volatile facts + language go in
# the user turn so this stays byte-identical request to request.
_SYSTEM = """You are a sell-side equity research writer for an Indonesian \
retail investor focused on the Indonesia Stock Exchange (IHSG / IDX). You turn \
a pre-computed, deterministic screening table into a clear, human-sounding \
decision note for BUY accumulation ("stacking").

Hard rules:
- Ground EVERYTHING strictly in the DATA block provided. Never invent or alter \
numbers (scores, yields, entry/target/stop, lots, capital, gain/loss, R:R). If \
a figure isn't in the DATA, don't state it.
- This is decision-support, not financial advice. Keep a measured, non-hype \
tone; flag risks honestly (yield-traps, passed ex-dates, sector concentration).
- "Smart bilingual": when writing in Indonesian, keep finance/technical terms \
that Indonesian investors normally use in English in English (RSI, yield, \
dividend, uptrend, support, entry, target, stop-loss, lot, BUY/HOLD/SELL, \
composite score) — translate only the surrounding prose.

Structure the note as Markdown:
1. A 2-3 sentence executive take.
2. Priority ranking with a one-line rationale per pick.
3. Per-stock: strengths, risks, and a verdict (weave the entry/target/stop/R:R \
in naturally).
4. A risk/reward overview and the total capital/gain/loss exposure.
5. Safer vs more-aggressive strategy.
6. A final verdict and a one-line not-financial-advice disclaimer.

Be concise and skimmable. Do not echo the raw table verbatim — synthesize."""


def available(api_key: str | None = None) -> tuple[bool, str]:
    """Return (is_available, reason). Cheap check for the UI to decide whether
    to offer the AI button."""
    try:
        import anthropic  # noqa: F401
    except Exception:
        return False, "anthropic package not installed (pip install anthropic)"
    if not (api_key or os.environ.get("ANTHROPIC_API_KEY")):
        return False, "no ANTHROPIC_API_KEY set (env or .streamlit/secrets.toml)"
    return True, "ready"


def narrate(analysis: dict, *, lang: str = "EN", model: str | None = None,
            api_key: str | None = None, effort: str = "low") -> str | None:
    """Write an AI research narrative for `analysis`. Returns Markdown, or None
    on any failure (missing package/key, API error) so the caller can fall back
    to the deterministic write-up."""
    if not analysis.get("picks"):
        return None
    ok, _ = available(api_key)
    if not ok:
        return None

    try:
        import anthropic
    except Exception:
        return None

    # Ground the model on our deterministic facts (the markdown report doubles
    # as a complete, structured fact sheet) plus the language directive.
    facts = decision.to_markdown(analysis)
    lang_name = "Bahasa Indonesia" if lang == "ID" else "English"
    user_content = (
        f"Write the decision note in {lang_name}.\n\n"
        f"DATA (the only source of truth — do not add numbers not present here):\n\n"
        f"{facts}"
    )

    try:
        client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        resp = client.with_options(timeout=120.0, max_retries=1).messages.create(
            model=model or DEFAULT_MODEL,
            max_tokens=4000,
            thinking={"type": "adaptive"},          # let Claude self-pace
            output_config={"effort": effort},        # low: this is writing, not deep reasoning
            system=[{
                "type": "text",
                "text": _SYSTEM,
                "cache_control": {"type": "ephemeral"},  # stable prefix
            }],
            messages=[{"role": "user", "content": user_content}],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        return text.strip() or None
    except Exception:
        # Old SDK that rejects thinking/output_config, auth failure, network,
        # rate limit — any of these → fall back to deterministic text.
        return None
