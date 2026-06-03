"""Decision-helper analysis engine — daily & monthly BUY-stacking write-ups.

Turns the strategy's recommendations into a structured, ranked decision aid like
a human-written research note: per-stock pros / risks / verdict, a risk-reward
table (capital, potential gain/loss, R:R), sector-concentration warnings, and
safe vs aggressive strategy notes plus a final verdict.

Everything here is DETERMINISTIC (computed from the stored snapshot), bilingual
EN/ID, and is also used as the reliable fallback when AI enrichment
(src/airesearch.py) is unavailable. Decision-support only — not financial advice.
"""
from __future__ import annotations

import pandas as pd

from . import allocate, strategy

LOT = strategy.LOT_SIZE  # 100 shares / lot on IDX


def _f(x, dp: int = 0) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "—"
    return f"{x:,.{dp}f}"


def _is_up(trend: str) -> bool:
    return trend in ("Uptrend", "Above SMA")


# --------------------------- per-stock narrative ---------------------------

def _cum_note(days_to_cum, lang: str) -> str | None:
    """Dividend-eligibility note from days-to-cum-date (negative = ex-date passed)."""
    if days_to_cum is None:
        return None
    d = int(days_to_cum)
    if d < 0:
        return ("Ex-date dividen sudah lewat — beli sekarang TIDAK berhak atas "
                "dividen yang baru dibagikan (cocok untuk akumulasi tren, bukan "
                "dividend stacking murni)." if lang == "ID" else
                "Dividend ex-date has passed — buying now does NOT qualify for the "
                "just-distributed dividend (fits trend accumulation, not pure "
                "dividend stacking).")
    if d <= 14:
        return (f"Cum-date ~{d} hari lagi — beli sebelum ex-date untuk berhak "
                "atas dividen berikutnya." if lang == "ID" else
                f"Cum-date in ~{d} day(s) — buy before the ex-date to qualify for "
                "the next dividend.")
    return None


def _pros(r: dict, lang: str) -> list[str]:
    out: list[str] = []
    comp, dy, rsi = r.get("composite"), r.get("div_yield_pct"), r.get("rsi")
    trend, conv = r.get("trend", ""), r.get("conviction", "")
    pe, pb, roe = r.get("pe"), r.get("pb"), r.get("roe")
    if lang == "ID":
        if comp is not None and comp >= 75:
            out.append(f"Composite score tinggi ({_f(comp)}/100).")
        if dy is not None:
            out.append(f"Dividend yield menarik ~{_f(dy,2)}%.")
        if _is_up(trend):
            out.append("Trend naik — SMA50 di atas SMA200.")
        if rsi is not None and rsi <= 40:
            out.append(f"RSI {_f(rsi)} mendekati oversold — area diskon.")
        elif rsi is not None and rsi < 70:
            out.append(f"RSI {_f(rsi)} sehat, belum overbought.")
        if isinstance(pe, (int, float)) and pe > 0 and pe <= 15:
            out.append(f"Valuasi murah (P/E {_f(pe,1)}).")
        if isinstance(roe, (int, float)) and roe >= 15:
            out.append(f"Profitabilitas kuat (ROE {_f(roe)}%).")
        if conv == "high":
            out.append("Fundamental & teknikal sama-sama kuat (high conviction).")
    else:
        if comp is not None and comp >= 75:
            out.append(f"High composite score ({_f(comp)}/100).")
        if dy is not None:
            out.append(f"Attractive dividend yield ~{_f(dy,2)}%.")
        if _is_up(trend):
            out.append("Uptrend — SMA50 above SMA200.")
        if rsi is not None and rsi <= 40:
            out.append(f"RSI {_f(rsi)} near oversold — a discount zone.")
        elif rsi is not None and rsi < 70:
            out.append(f"RSI {_f(rsi)} healthy, not overbought.")
        if isinstance(pe, (int, float)) and pe > 0 and pe <= 15:
            out.append(f"Cheap valuation (P/E {_f(pe,1)}).")
        if isinstance(roe, (int, float)) and roe >= 15:
            out.append(f"Strong profitability (ROE {_f(roe)}%).")
        if conv == "high":
            out.append("Fundamentals and technicals both strong (high conviction).")
    return out or (["Lolos gate dividend + value."] if lang == "ID"
                   else ["Passes the dividend + value gate."])


def _risks(r: dict, lang: str, sector_overlap: list[str]) -> list[str]:
    out: list[str] = []
    rsi, trend = r.get("rsi"), r.get("trend", "")
    cum = _cum_note(r.get("days_to_cum"), lang)
    if cum and (r.get("days_to_cum") or 0) < 0:
        out.append(cum)
    if r.get("yield_trap"):
        why = r.get("trap_reasons") or ""
        out.append((f"Risiko yield-trap ({why}) — yield tinggi belum tentu aman."
                    if lang == "ID" else
                    f"Yield-trap risk ({why}) — a high yield isn't always safe."))
    if not _is_up(trend):
        out.append(("Trend belum naik — sering lebih baik tunggu konfirmasi."
                    if lang == "ID" else
                    "Not in an uptrend — often better to wait for confirmation."))
    if rsi is not None and rsi >= 70:
        out.append((f"RSI {_f(rsi)} overbought — risiko beli di puncak jangka pendek."
                    if lang == "ID" else
                    f"RSI {_f(rsi)} overbought — risk of buying a short-term top."))
    if sector_overlap:
        others = ", ".join(sector_overlap)
        out.append((f"Overlap sektor dengan {others} — portofolio bisa terkonsentrasi."
                    if lang == "ID" else
                    f"Sector overlap with {others} — can concentrate the portfolio."))
    if not out:
        out.append(("Validasi ulang harga & jadwal dividen sebelum eksekusi."
                    if lang == "ID" else
                    "Re-validate price & dividend schedule before executing."))
    return out


def _verdict(r: dict, rank: int, lang: str) -> str:
    conv = r.get("conviction", "")
    if rank == 1:
        return ("Paling layak diprioritaskan — pilihan paling defensible dari daftar."
                if lang == "ID" else
                "Most worth prioritizing — the most defensible pick on the list.")
    if conv == "high":
        return ("Layak masuk posisi inti/kedua bila harga masih dekat entry."
                if lang == "ID" else
                "Worth a core/second position if price is still near entry.")
    return ("Masih layak, tapi bukan prioritas utama — pilih sesuai validasi & risiko."
            if lang == "ID" else
            "Still viable, but not top priority — pick per your validation & risk.")


# ----------------------------- assembly -----------------------------------

def _pick(r: dict, lots, lang: str, sector_overlap: list[str]) -> dict:
    entry, target, stop = r.get("entry"), r.get("target"), r.get("stop")
    lots = int(lots or 0)
    shares = lots * LOT
    capital = entry * shares if (entry and shares) else 0.0
    gain = (target - entry) * shares if (entry and target and shares) else 0.0
    loss = (entry - stop) * shares if (entry and stop and shares) else 0.0
    rr = (gain / loss) if loss > 0 else None
    dtc = r.get("days_to_cum")
    return {
        "symbol": r.get("symbol"), "score": r.get("composite"),
        "yield": r.get("div_yield_pct"), "entry": entry, "target": target,
        "stop": stop, "lots": lots, "shares": shares, "capital": capital,
        "gain": gain, "loss": loss, "rr": rr, "conviction": r.get("conviction", ""),
        "rsi": r.get("rsi"), "trend": r.get("trend", ""), "sector": r.get("sector"),
        "yield_trap": bool(r.get("yield_trap")),
        "ex_passed": (dtc is not None and int(dtc) < 0),
        "cum_note": _cum_note(dtc, lang),
        "pros": _pros(r, lang), "risks": _risks(r, lang, sector_overlap),
        "verdict": _verdict(r, 0, lang),  # rank filled by caller
    }


def build_analysis(cfg: dict, recs_df: pd.DataFrame, *, mode: str = "daily",
                   budget: float | None = None, num: int = 3,
                   lang: str = "EN", as_of: str | None = None) -> dict:
    """Build a structured decision-helper analysis.

    mode="daily":  rank the top-N BUY picks, size each by the model's risk-based
                   lots. mode="monthly": size by splitting `budget` across picks
                   via allocate.plan (DCA stacking).
    """
    as_of = as_of or pd.Timestamp.today().strftime("%Y-%m-%d")
    empty = {"mode": mode, "as_of": as_of, "lang": lang, "picks": [], "totals": {},
             "sector_groups": [], "strategy_safe": [], "strategy_aggressive": "",
             "final_verdict": "", "monthly_plan": None, "notes": []}
    if recs_df is None or recs_df.empty:
        return empty

    # Choose picks + per-pick lots.
    monthly_plan = None
    if mode == "monthly":
        monthly_plan = allocate.plan(float(budget or 0), recs_df, max_names=num)
        order = [(row["symbol"], row["lots"]) for row in monthly_plan["rows"]]
    else:
        buys = recs_df[recs_df["action"] == "BUY"].copy()
        if buys.empty:
            return empty
        buys["_up"] = buys["trend"].isin(["Uptrend", "Above SMA"]).astype(int)
        buys = buys.sort_values(["_up", "composite"], ascending=[False, False]).head(num)
        order = [(row["symbol"], row.get("lots")) for _, row in buys.iterrows()]
    if not order:
        return empty

    by_sym = {row["symbol"]: row.to_dict() for _, row in recs_df.iterrows()}

    # Sector overlap map among the chosen symbols.
    chosen = [s for s, _ in order]
    sector_of = {s: (by_sym.get(s, {}).get("sector") or "") for s in chosen}
    overlap = {}
    for s in chosen:
        sec = sector_of[s]
        if not sec:
            overlap[s] = []
            continue
        overlap[s] = [o for o in chosen if o != s and sector_of[o] == sec]

    picks = []
    for i, (sym, lots) in enumerate(order):
        r = by_sym.get(sym)
        if not r:
            continue
        p = _pick(r, lots, lang, overlap.get(sym, []))
        p["rank"] = i + 1
        p["verdict"] = _verdict(r, i + 1, lang)
        picks.append(p)

    totals = {
        "capital": sum(p["capital"] for p in picks),
        "gain": sum(p["gain"] for p in picks),
        "loss": sum(p["loss"] for p in picks),
    }

    # Sector groups with >1 pick (concentration).
    groups: dict[str, list[str]] = {}
    for p in picks:
        if p["sector"]:
            groups.setdefault(p["sector"], []).append(p["symbol"])
    sector_groups = [{"sector": k, "symbols": v} for k, v in groups.items() if len(v) > 1]

    notes = _notes(picks, lang)
    return {
        "mode": mode, "as_of": as_of, "lang": lang, "picks": picks, "totals": totals,
        "sector_groups": sector_groups, "monthly_plan": monthly_plan,
        "strategy_safe": _strategy_safe(picks, sector_groups, lang),
        "strategy_aggressive": _strategy_aggressive(totals, lang),
        "final_verdict": _final_verdict(picks, sector_groups, lang),
        "notes": notes,
    }


def _notes(picks: list[dict], lang: str) -> list[str]:
    out = []
    passed = [p["symbol"] for p in picks if p.get("ex_passed")]
    if passed:
        out.append((f"Beberapa ex-date dividen sudah lewat ({', '.join(passed)}) — "
                    "untuk dividend stacking murni, validasi jadwal dividen terbaru "
                    "di sumber resmi (KSEI/IDX/aplikasi sekuritas)."
                    if lang == "ID" else
                    f"Some dividend ex-dates have passed ({', '.join(passed)}) — for "
                    "pure dividend stacking, re-validate the latest schedule at an "
                    "official source (KSEI/IDX/your broker app)."))
    return out


def _strategy_safe(picks, sector_groups, lang) -> list[str]:
    if not picks:
        return []
    top = picks[0]["symbol"]
    if lang == "ID":
        steps = [f"Ambil **{top}** sebagai prioritas utama (core)."]
        if sector_groups:
            syms = sector_groups[0]["symbols"]
            steps.append(f"Pilih **salah satu** dari {', '.join(syms)} untuk hindari "
                         "konsentrasi berlebihan di sektor sama.")
        steps += ["Entry hanya bila harga masih dekat level entry model.",
                  "Pakai stop-loss secara disiplin.",
                  "Jangan average down bila harga sudah tembus stop."]
        return steps
    steps = [f"Take **{top}** as the core priority."]
    if sector_groups:
        syms = sector_groups[0]["symbols"]
        steps.append(f"Pick **only one** of {', '.join(syms)} to avoid over-"
                     "concentrating in the same sector.")
    steps += ["Only enter while price is still near the model entry level.",
              "Use the stop-loss with discipline.",
              "Don't average down once price breaks the stop."]
    return steps


def _strategy_aggressive(totals, lang) -> str:
    loss = totals.get("loss") or 0
    if lang == "ID":
        return (f"Jika tetap mengambil semua posisi, pastikan total risiko (±Rp"
                f"{_f(loss)}) masih sesuai ukuran portofolio. Idealnya risiko per "
                "posisi tidak terlalu besar terhadap total modal.")
    return (f"If you take all positions anyway, make sure total risk (±Rp{_f(loss)}) "
            "still fits your portfolio size. Ideally per-position risk stays small "
            "relative to total capital.")


def _final_verdict(picks, sector_groups, lang) -> str:
    if not picks:
        return ("Tidak ada pilihan BUY hari ini — tidak ada yang di-stack."
                if lang == "ID" else "No BUY picks — nothing to stack right now.")
    top = picks[0]["symbol"]
    alt = ""
    if sector_groups:
        alt = (f" Mulai dari **{top}** sebagai core, lalu pilih **satu saja** dari "
               f"{', '.join(sector_groups[0]['symbols'])} sesuai validasi harga, "
               "jadwal dividen, dan toleransi risiko." if lang == "ID" else
               f" Start with **{top}** as the core, then pick **just one** of "
               f"{', '.join(sector_groups[0]['symbols'])} based on price validation, "
               "dividend schedule, and risk tolerance.")
    base = (f"Prioritas terbaik: **{top}**." if lang == "ID"
            else f"Best priority: **{top}**.")
    return base + alt


# ----------------------------- markdown render -----------------------------

def to_markdown(a: dict) -> str:
    """Render the analysis as a full markdown report (deterministic fallback)."""
    lang = a.get("lang", "EN")
    ID = lang == "ID"
    if not a.get("picks"):
        return ("## Tidak ada pilihan BUY\n\nTidak ada saham berstatus BUY untuk "
                "dianalisis hari ini." if ID else
                "## No BUY picks\n\nThere are no BUY-rated stocks to analyze right now.")
    mode_lbl = ({"daily": "Harian", "monthly": "Bulanan"} if ID
                else {"daily": "Daily", "monthly": "Monthly"}).get(a["mode"], a["mode"])
    L: list[str] = []
    if ID:
        L.append(f"# Rangkuman Analisa Keputusan BUY Stacking ({mode_lbl})")
        L.append(f"\n**Tanggal acuan:** {a['as_of']}  ")
        L.append(f"**Saham dianalisis:** {', '.join(p['symbol'] for p in a['picks'])}  ")
        L.append("\n> Catatan: rangkuman analisa, bukan rekomendasi finansial final. "
                 "Validasi ulang harga, jadwal dividen, kondisi pasar, dan risiko "
                 "pribadi sebelum eksekusi.\n")
        L.append("\n## Ranking Prioritas\n")
    else:
        L.append(f"# BUY-Stacking Decision Summary ({mode_lbl})")
        L.append(f"\n**As of:** {a['as_of']}  ")
        L.append(f"**Stocks analyzed:** {', '.join(p['symbol'] for p in a['picks'])}  ")
        L.append("\n> Note: a decision summary, not final financial advice. "
                 "Re-validate price, dividend schedule, market conditions, and your "
                 "own risk before executing.\n")
        L.append("\n## Priority Ranking\n")
    medals = ["🥇", "🥈", "🥉", "④", "⑤"]
    for p in a["picks"]:
        m = medals[p["rank"] - 1] if p["rank"] <= len(medals) else f"{p['rank']}."
        L.append(f"{m} **{p['symbol']}** — score {_f(p['score'])}/100, "
                 f"yield {_f(p['yield'],2)}%")
    # per-stock
    for p in a["picks"]:
        L.append(f"\n---\n\n## {p['symbol']}\n")
        kv = (("Score", _f(p["score"])), ("Yield", _f(p["yield"], 2) + "%"),
              ("Entry", _f(p["entry"])), ("Target", _f(p["target"])),
              ("Stop", _f(p["stop"])), ("Lot", _f(p["lots"])),
              ("RSI", _f(p["rsi"])), ("Trend", p["trend"]),
              ("Conviction", p["conviction"] or "—"))
        L.append(" · ".join(f"**{k}:** {v}" for k, v in kv))
        L.append(("\n**Kelebihan**" if ID else "\n**Strengths**"))
        L += [f"- {x}" for x in p["pros"]]
        L.append(("\n**Risiko**" if ID else "\n**Risks**"))
        L += [f"- {x}" for x in p["risks"]]
        L.append(("\n**Verdict:** " if ID else "\n**Verdict:** ") + p["verdict"])
    # R/R table
    L.append(("\n---\n\n## Perbandingan Risk / Reward\n" if ID
              else "\n---\n\n## Risk / Reward Comparison\n"))
    if ID:
        L.append("| Saham | Entry | Target | Stop | Modal | Potensi Gain | "
                 "Potensi Loss | R:R |")
    else:
        L.append("| Stock | Entry | Target | Stop | Capital | Gain | Loss | R:R |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for p in a["picks"]:
        L.append(f"| {p['symbol']} | {_f(p['entry'])} | {_f(p['target'])} | "
                 f"{_f(p['stop'])} | Rp{_f(p['capital'])} | Rp{_f(p['gain'])} | "
                 f"Rp{_f(p['loss'])} | {_f(p['rr'],2)}x |")
    t = a["totals"]
    if ID:
        L.append(f"\n- **Total modal:** ±Rp{_f(t.get('capital'))}")
        L.append(f"- **Total potensi gain:** ±Rp{_f(t.get('gain'))}")
        L.append(f"- **Total potensi loss (semua kena stop):** ±Rp{_f(t.get('loss'))}")
    else:
        L.append(f"\n- **Total capital:** ±Rp{_f(t.get('capital'))}")
        L.append(f"- **Total potential gain:** ±Rp{_f(t.get('gain'))}")
        L.append(f"- **Total potential loss (all stops hit):** ±Rp{_f(t.get('loss'))}")
    # strategy notes
    L.append(("\n---\n\n## Catatan Strategi\n\n### Strategi Lebih Aman\n" if ID
              else "\n---\n\n## Strategy Notes\n\n### Safer Strategy\n"))
    for i, s in enumerate(a["strategy_safe"], 1):
        L.append(f"{i}. {s}")
    L.append(("\n### Strategi Agresif\n" if ID else "\n### Aggressive Strategy\n"))
    L.append(a["strategy_aggressive"])
    # notes / caveats
    for n in a.get("notes", []):
        L.append(f"\n> ⚠️ {n}")
    # final verdict
    L.append(("\n---\n\n## Final Verdict\n" if ID else "\n---\n\n## Final Verdict\n"))
    L.append(a["final_verdict"])
    return "\n".join(L)
