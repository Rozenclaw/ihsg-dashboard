"""Optional AI narrative for the Decision Helper — provider-agnostic.

Given the deterministic analysis from src/decision.py, ask a chat LLM to write a
polished bilingual (EN/ID) research narrative grounded ONLY on the numbers we
computed. Works with any OpenAI-compatible API (Google Gemini, Groq, OpenRouter,
a local Ollama, …) — pick one in config.yaml `ai.provider` and set its free API
key via env var or .streamlit/secrets.toml.

Uses `requests` only (no provider SDK). Degrades gracefully: returns None (caller
falls back to decision.to_markdown) when no key is configured, the provider is
unreachable, or the call fails. Nothing here imports Streamlit.
"""
from __future__ import annotations

import os

import requests

from . import decision

# Free OpenAI-compatible providers. Override base_url/model in config.yaml `ai`
# to use any other endpoint. `key_envs` lists the env vars (and secrets keys) we
# look in, in order. requires_key=False for a local server (Ollama).
PRESETS: dict[str, dict] = {
    "gemini": {
        "label": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-2.0-flash",
        "key_envs": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "requires_key": True,
        "signup": "https://aistudio.google.com/apikey",
    },
    "groq": {
        "label": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "key_envs": ["GROQ_API_KEY"],
        "requires_key": True,
        "signup": "https://console.groq.com/keys",
    },
    "openrouter": {
        "label": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "key_envs": ["OPENROUTER_API_KEY"],
        "requires_key": True,
        "signup": "https://openrouter.ai/keys",
    },
    "ollama": {
        "label": "Ollama (local)",
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.2",
        "key_envs": [],
        "requires_key": False,
        "signup": "https://ollama.com/download",
    },
}

_SYSTEM = """You are a sell-side equity research writer for an Indonesian retail \
investor focused on the Indonesia Stock Exchange (IHSG / IDX). You turn a \
pre-computed, deterministic screening table into a clear, human-sounding \
decision note for BUY accumulation ("stacking").

Hard rules:
- Ground EVERYTHING strictly in the DATA block provided. Never invent or alter \
numbers (scores, yields, entry/target/stop, lots, capital, gain/loss, R:R). If a \
figure isn't in the DATA, don't state it.
- This is decision-support, not financial advice. Keep a measured, non-hype tone; \
flag risks honestly (yield-traps, passed ex-dates, sector concentration).
- "Smart bilingual": when writing in Indonesian, keep finance/technical terms \
Indonesian investors normally use in English in English (RSI, yield, dividend, \
uptrend, support, entry, target, stop-loss, lot, BUY/HOLD/SELL, composite score) \
— translate only the surrounding prose.

Write Markdown: (1) a 2-3 sentence executive take; (2) priority ranking with a \
one-line rationale each; (3) per-stock strengths, risks, and a verdict weaving in \
entry/target/stop/R:R; (4) a risk-reward overview with total capital/gain/loss; \
(5) safer vs more-aggressive strategy; (6) a final verdict and a one-line \
not-financial-advice disclaimer. Be concise and skimmable — synthesize, don't \
echo the table."""

# Day-trading shortlist persona: deliberately risk-first (NOT bullish sell-side).
# Downside, stops and position sizing come BEFORE any bull case.
_SYSTEM_DAYTRADE = """You are a risk-first trading coach for an Indonesian retail \
BEGINNER with a small daily budget on the IDX. You turn a pre-computed, \
deterministic daily SWING shortlist (not intraday scalping) into a calm, honest \
decision note.

Hard rules:
- Ground EVERYTHING strictly in the DATA block (scores, RSI, entry/stop/target, \
R:R, lots, capital, NET gain/loss after costs, risk-vs-capital). Never invent or \
alter a number. If it isn't in the DATA, don't say it.
- Lead with DOWNSIDE: for each candidate state the stop, the rupiah loss if the \
stop is hit, and one reason you might NOT take it — before any bull case.
- These are CANDIDATES for the user's own review, not buy instructions, and this \
is decision-support, not financial advice. No hype, no price predictions, no \
"guaranteed/safe/profitable".
- Respect the safety frame: trade only liquid names; risk <= 1% of capital; \
always set the stop first; require R:R >= 2; never chase RSI > 70 or ARA spikes; \
never average down past the stop. If there are no BUY signals, the correct \
message is that holding cash and waiting is a valid, often better choice.
- Note that costs (~0.15-0.25% per side + 0.1% sell tax) erode a small budget if \
the user overtrades.
- "Smart bilingual": when writing Indonesian, keep finance terms Indonesian \
investors use in English (RSI, yield, entry, target, stop-loss, lot, BUY/WATCH/\
AVOID, support, uptrend, swing, R:R, ARA) in English; translate only the prose.

Write Markdown: (1) a 2-3 sentence honest take incl. how many clean BUYs exist \
today; (2) for each BUY/WATCH candidate: stop & rupiah-at-risk first, then the \
setup (trend/RSI/volume) and the verdict; (3) the budget-allocation read-through \
(what fits, NET gain/loss, leftover cash, total risk vs capital); (4) a final \
"what a disciplined beginner would do" line and a one-line not-financial-advice \
disclaimer. Be concise and skimmable."""

# Exposed so pages can pick the right persona.
SYSTEM_STACKING = _SYSTEM
SYSTEM_DAYTRADE = _SYSTEM_DAYTRADE


def _resolved(cfg: dict) -> dict:
    """Merge a provider preset with explicit config.yaml `ai` overrides."""
    cfg = cfg or {}
    provider = str(cfg.get("provider", "gemini")).lower()
    preset = dict(PRESETS.get(provider, PRESETS["gemini"]))
    preset["provider"] = provider
    if cfg.get("base_url"):
        preset["base_url"] = str(cfg["base_url"]).rstrip("/")
    if cfg.get("model"):
        preset["model"] = str(cfg["model"])
    # explicit key_env override (for a custom provider)
    if cfg.get("key_env"):
        preset["key_envs"] = [str(cfg["key_env"])]
    preset["base_url"] = preset["base_url"].rstrip("/")
    preset["temperature"] = float(cfg.get("temperature", 0.4))
    preset["max_tokens"] = int(cfg.get("max_tokens", 6000))
    # Caps "thinking" token spend on reasoning models (e.g. Gemini 2.5) so the
    # output budget goes to the narrative, not internal thinking. Blank → omit
    # (some providers reject the field). "" | none | low | medium | high.
    preset["reasoning_effort"] = str(cfg.get("reasoning_effort", "") or "").strip()
    return preset


def key_env_names(cfg: dict) -> list[str]:
    """Env-var / secrets key names the page should look up for this provider."""
    return list(_resolved(cfg).get("key_envs", []))


def available(cfg: dict, api_key: str | None = None) -> tuple[bool, str]:
    """(is_available, reason). Local providers (Ollama) need no key."""
    r = _resolved(cfg)
    if not r.get("requires_key", True):
        return True, "ready (local)"
    key = api_key or _key_from_env(r)
    if not key:
        envs = " / ".join(r["key_envs"]) or "API key"
        return False, (f"no {r['label']} key — set {envs} (env or "
                       f".streamlit/secrets.toml). Get one free at {r['signup']}")
    return True, "ready"


def _key_from_env(r: dict) -> str | None:
    for name in r.get("key_envs", []):
        v = os.environ.get(name)
        if v:
            return v
    return None


def narrate(analysis: dict, cfg: dict, *, lang: str = "EN",
            api_key: str | None = None, facts: str | None = None,
            system: str | None = None) -> str | None:
    """Write the AI narrative, or None on any failure (caller falls back).

    `facts` overrides the grounding text (default: decision.to_markdown(analysis));
    `system` overrides the persona/system prompt. Both let other pages (e.g. the
    daily-trading shortlist) reuse this with their own data + tone.
    """
    if facts is None and not analysis.get("picks"):
        return None
    r = _resolved(cfg)
    key = api_key or _key_from_env(r)
    if r.get("requires_key", True) and not key:
        return None

    facts = facts if facts is not None else decision.to_markdown(analysis)
    lang_name = "Bahasa Indonesia" if lang == "ID" else "English"
    user_content = (
        f"Write the decision note in {lang_name}.\n\n"
        f"DATA (the only source of truth — do not add numbers not present here):\n\n"
        f"{facts}"
    )
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    payload = {
        "model": r["model"],
        "messages": [
            {"role": "system", "content": system or _SYSTEM},
            {"role": "user", "content": user_content},
        ],
        "temperature": r["temperature"],
        "max_tokens": r["max_tokens"],
        "stream": False,
    }
    if r.get("reasoning_effort"):
        payload["reasoning_effort"] = r["reasoning_effort"]
    try:
        resp = requests.post(f"{r['base_url']}/chat/completions",
                             headers=headers, json=payload, timeout=120)
        if resp.status_code != 200:
            return None
        data = resp.json()
        text = (data.get("choices") or [{}])[0].get("message", {}).get("content")
        return (text or "").strip() or None
    except Exception:
        return None
