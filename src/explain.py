"""Plain-language, live explanations of chart values — bilingual (EN / ID).

"Smart" Bahasa: technical terms investors use in English (RSI, Bollinger, SMA,
BUY/SELL/HOLD, yield, dividend, support, uptrend, target, stop-loss, lot) are
kept in English inside the Indonesian text; only the surrounding prose is
translated.
"""
from __future__ import annotations

from typing import Optional


def _fmt(x: Optional[float], dp: int = 0) -> str:
    if x is None:
        return "—"
    return f"{x:,.{dp}f}"


def legend_help(lang: str = "EN") -> str:
    if lang == "ID":
        return (
            "**Cara membaca grafik ini**\n\n"
            "- **Candle (OHLC)** — tiap candle = satu hari. Hijau = harga close "
            "lebih tinggi dari open; merah = lebih rendah. Sumbu tipisnya "
            "menunjukkan high & low hari itu.\n"
            "- **SMA50 (biru)** — rata-rata harga 50 hari (tren jangka pendek). "
            "**SMA200 (oranye)** — rata-rata 200 hari (tren jangka panjang). Saat "
            "SMA50 **di atas** SMA200, tren umumnya naik.\n"
            "- **Bollinger Band (area abu-abu)** — 'rentang normal' di sekitar "
            "harga. Menyentuh band **bawah** bisa berarti oversold/murah; band "
            "**atas** bisa berarti overbought/mahal.\n"
            "- **RSI (ungu, bawah)** — momentum 0–100. **Di atas 70** (garis "
            "merah) = overbought (bisa turun). **Di bawah 30** (garis hijau) = "
            "oversold (bisa naik). 40–60 = netral."
        )
    return (
        "**How to read this chart**\n\n"
        "- **Candles (OHLC)** — each candle is one day. Green = price closed "
        "higher than it opened; red = closed lower. The thin wicks show the "
        "day's high and low.\n"
        "- **SMA50 (blue)** — average price over the last 50 days (short-term "
        "trend). **SMA200 (orange)** — average over 200 days (long-term trend). "
        "When SMA50 is **above** SMA200, the trend is generally up.\n"
        "- **Bollinger Bands (grey shaded)** — a 'normal range' around price. "
        "Touching the **lower** band can mean oversold/cheap; the **upper** band "
        "can mean overbought/expensive.\n"
        "- **RSI (purple, bottom)** — momentum from 0–100. **Above 70** "
        "(red line) = overbought (may pull back). **Below 30** (green line) = "
        "oversold (may bounce). 40–60 = neutral."
    )


def explain_index(snap: dict, lang: str = "EN") -> str:
    if not snap or snap.get("close") is None:
        return "Belum ada data indeks." if lang == "ID" else "No index data yet."
    close = snap["close"]
    chg = snap.get("change_pct")
    rsi = snap.get("rsi")
    trend = snap.get("trend", "—")
    pos = snap.get("range_pos_pct")

    if lang == "ID":
        parts = [f"IHSG berada di **{_fmt(close)}**"]
        if chg is not None:
            parts.append(f", {'naik' if chg >= 0 else 'turun'} **{_fmt(abs(chg),2)}%** hari ini")
        s1 = "".join(parts) + "."
        bits = []
        if trend != "—":
            bits.append("Tren jangka panjang terlihat **naik** (SMA50 di atas "
                        "SMA200)." if trend in ("Uptrend", "Above SMA")
                        else "Tren jangka panjang terlihat **turun** (SMA50 di "
                        "bawah SMA200).")
        if rsi is not None:
            if rsi >= 70:
                bits.append(f"Momentum (RSI {_fmt(rsi)}) **overbought** — wajar "
                            "kalau ada jeda atau koreksi.")
            elif rsi <= 30:
                bits.append(f"Momentum (RSI {_fmt(rsi)}) **oversold** — sering "
                            "jadi zona awal rebound.")
            else:
                bits.append(f"Momentum (RSI {_fmt(rsi)}) **netral**.")
        if pos is not None:
            bits.append(f"Saat ini di sekitar **{_fmt(pos)}%** dari rentang "
                        "1 tahun (0% = terendah, 100% = tertinggi).")
        return s1 + " " + " ".join(bits)

    parts = [f"IHSG is at **{_fmt(close)}**"]
    if chg is not None:
        parts.append(f", {'up' if chg >= 0 else 'down'} **{_fmt(abs(chg),2)}%** today")
    s1 = "".join(parts) + "."
    bits = []
    if trend != "—":
        bits.append("The long-term trend looks **up** (SMA50 above SMA200)."
                    if trend in ("Uptrend", "Above SMA")
                    else "The long-term trend looks **down** (SMA50 below SMA200).")
    if rsi is not None:
        if rsi >= 70:
            bits.append(f"Momentum (RSI {_fmt(rsi)}) is **hot/overbought** — a "
                        "pause or dip wouldn't be surprising.")
        elif rsi <= 30:
            bits.append(f"Momentum (RSI {_fmt(rsi)}) is **oversold** — often a "
                        "zone where bounces start.")
        else:
            bits.append(f"Momentum (RSI {_fmt(rsi)}) is **neutral**.")
    if pos is not None:
        bits.append(f"It's sitting around **{_fmt(pos)}%** of its 1-year range "
                    "(0% = year low, 100% = year high).")
    return s1 + " " + " ".join(bits)


def explain_stock(snap: dict, cfg: dict, symbol: str = "", lang: str = "EN") -> str:
    if not snap or snap.get("close") is None:
        return "Belum ada data saham ini." if lang == "ID" else "No data for this stock yet."
    close = snap["close"]
    chg = snap.get("change_pct")
    rsi = snap.get("rsi")
    trend = snap.get("trend", "—")
    pos = snap.get("range_pos_pct")
    bb_lower = snap.get("bb_lower")
    vol, vavg = snap.get("volume"), snap.get("vol_avg20")
    lo, hi = snap.get("range52_low"), snap.get("range52_high")
    lines = []

    if lang == "ID":
        if chg is not None:
            lines.append(f"**Harga:** close terakhir **{_fmt(close)}**, "
                         f"{'naik' if chg >= 0 else 'turun'} **{_fmt(abs(chg),2)}%** hari ini.")
        else:
            lines.append(f"**Harga:** close terakhir **{_fmt(close)}**.")
        if trend in ("Uptrend", "Above SMA"):
            lines.append("**Trend:** 📈 naik — SMA50 di atas SMA200, arah jangka "
                         "menengah positif.")
        elif trend in ("Downtrend", "Below SMA"):
            lines.append("**Trend:** 📉 turun — SMA50 di bawah SMA200, arah jangka "
                         "menengah lemah. Sering lebih baik menunggu stabil dulu.")
        else:
            lines.append("**Trend:** datar / histori belum cukup.")
        if rsi is not None:
            if rsi >= 70:
                lines.append(f"**Momentum (RSI {_fmt(rsi)}):** overbought — sudah "
                             "naik cepat; mengejar di sini berisiko beli di puncak.")
            elif rsi <= 40:
                lines.append(f"**Momentum (RSI {_fmt(rsi)}):** oversold/rendah — "
                             "zona yang biasa diincar pembeli saat dip.")
            else:
                lines.append(f"**Momentum (RSI {_fmt(rsi)}):** netral.")
        if pos is not None and lo and hi:
            where = ("dekat **terendah** 1 tahun" if pos <= 25 else
                     "dekat **tertinggi** 1 tahun" if pos >= 75 else
                     "di **tengah** rentang 1 tahun")
            lines.append(f"**Posisi:** {where} (rentang {_fmt(lo)}–{_fmt(hi)}, "
                         f"sekitar ~{_fmt(pos)}% naik di rentang itu).")
        if bb_lower and close and close <= bb_lower:
            lines.append("**Bollinger:** harga **di/below band bawah** — secara "
                         "statistik tertekan ke bawah (bisa rebound, bisa juga "
                         "breakdown — konfirmasi dengan trend).")
        if vol and vavg and vavg > 0:
            ratio = vol / vavg
            if ratio >= 1.5:
                lines.append(f"**Volume:** **{_fmt(ratio,1)}× lebih besar** dari "
                             "rata-rata 20 hari — minat kuat di balik pergerakan.")
            elif ratio <= 0.6:
                lines.append(f"**Volume:** tipis ({_fmt(ratio,1)}× rata-rata) — "
                             "pergerakan dengan volume rendah kurang dapat diandalkan.")
        return "\n\n".join(lines)

    # EN
    if chg is not None:
        lines.append(f"**Price:** last close **{_fmt(close)}**, "
                     f"{'rose' if chg >= 0 else 'fell'} **{_fmt(abs(chg),2)}%** on the day.")
    else:
        lines.append(f"**Price:** last close **{_fmt(close)}**.")
    if trend in ("Uptrend", "Above SMA"):
        lines.append("**Trend:** 📈 up — SMA50 is above SMA200, so the medium-term "
                     "direction is positive.")
    elif trend in ("Downtrend", "Below SMA"):
        lines.append("**Trend:** 📉 down — SMA50 is below SMA200, so the medium-term "
                     "direction is weak. Often better to wait for it to stabilize.")
    else:
        lines.append("**Trend:** flat / not enough history to call.")
    if rsi is not None:
        if rsi >= 70:
            lines.append(f"**Momentum (RSI {_fmt(rsi)}):** overbought — it's run up "
                         "fast; chasing here risks buying a short-term top.")
        elif rsi <= 40:
            lines.append(f"**Momentum (RSI {_fmt(rsi)}):** oversold/low — the kind "
                         "of zone where dip-buyers look for entries.")
        else:
            lines.append(f"**Momentum (RSI {_fmt(rsi)}):** neutral — no extreme either way.")
    if pos is not None and lo and hi:
        where = ("near its 1-year **low**" if pos <= 25 else
                 "near its 1-year **high**" if pos >= 75 else
                 "in the **middle** of its 1-year range")
        lines.append(f"**Position:** {where} (range {_fmt(lo)}–{_fmt(hi)}, "
                     f"currently ~{_fmt(pos)}% up that range).")
    if bb_lower and close and close <= bb_lower:
        lines.append("**Bollinger:** price is **at/below the lower band** — "
                     "statistically stretched to the downside (possible bounce, or "
                     "a breakdown — confirm with the trend).")
    if vol and vavg and vavg > 0:
        ratio = vol / vavg
        if ratio >= 1.5:
            lines.append(f"**Volume:** **{_fmt(ratio,1)}× heavier** than its 20-day "
                         "average — strong interest behind the move.")
        elif ratio <= 0.6:
            lines.append(f"**Volume:** light ({_fmt(ratio,1)}× average) — moves on "
                         "low volume are less reliable.")
    return "\n\n".join(lines)


def trap_note(row: dict, lang: str = "EN") -> str:
    """Short yield-trap warning if flagged, else empty string."""
    if not row.get("yield_trap"):
        return ""
    why = row.get("trap_reasons") or ""
    if lang == "ID":
        return f"⚠️ **Risiko yield-trap** — {why}. Yield tinggi belum tentu aman."
    return f"⚠️ **Yield-trap risk** — {why}. A high yield isn't always safe."


def why_today(row: dict, lang: str = "EN") -> str:
    """A short, day-specific reason a BUY pick is worth stacking today.

    Built live from that day's metrics (yield, trend, RSI, range position),
    so it changes as the data changes. Technical terms kept in English.
    """
    dy = row.get("div_yield_pct")
    trend = row.get("trend", "")
    rsi = row.get("rsi")
    pos = row.get("range_pos_pct")
    comp = row.get("composite")
    reasons = []

    if lang == "ID":
        if dy is not None:
            reasons.append(f"dividend yield ~{_fmt(dy,2)}% (menarik untuk akumulasi)")
        if trend in ("Uptrend", "Above SMA"):
            reasons.append("trend naik (SMA50 di atas SMA200)")
        if rsi is not None:
            if rsi <= 40:
                reasons.append(f"RSI {_fmt(rsi)} oversold — diskon untuk dicicil")
            elif rsi < 70:
                reasons.append(f"RSI {_fmt(rsi)} masih sehat, belum overbought")
        if pos is not None and pos <= 40:
            reasons.append(f"masih ~{_fmt(pos)}% dari bawah rentang 1 tahun (belum mahal)")
        if comp is not None:
            reasons.append(f"composite score {_fmt(comp)}/100")
        return "; ".join(reasons) + "." if reasons else "lolos gate dividend+value."

    if dy is not None:
        reasons.append(f"dividend yield ~{_fmt(dy,2)}% (attractive to accumulate)")
    if trend in ("Uptrend", "Above SMA"):
        reasons.append("uptrend (SMA50 above SMA200)")
    if rsi is not None:
        if rsi <= 40:
            reasons.append(f"RSI {_fmt(rsi)} oversold — a discount to average in")
        elif rsi < 70:
            reasons.append(f"RSI {_fmt(rsi)} still healthy, not overbought")
    if pos is not None and pos <= 40:
        reasons.append(f"only ~{_fmt(pos)}% up its 1-year range (not expensive yet)")
    if comp is not None:
        reasons.append(f"composite score {_fmt(comp)}/100")
    return "; ".join(reasons) + "." if reasons else "passes the dividend+value gate."


def trap_note(row: dict, lang: str = "EN") -> str:
    """Warning text for a yield-trap-flagged stock."""
    reasons = row.get("trap_reasons") or ""
    if lang == "ID":
        return (f"⚠️ **Yield-trap risk:** dividend tinggi tapi terlihat kurang "
                f"berkelanjutan ({reasons}). Hati-hati — yield bisa tinggi karena "
                f"harga jatuh / payout tak wajar.")
    return (f"⚠️ **Yield-trap risk:** high dividend but looks unsustainable "
            f"({reasons}). Be careful — yield can be high because price fell or "
            f"the payout is unsustainable.")


def explain_recommendation(row: dict, lang: str = "EN") -> str:
    act = row.get("action")
    sym = row.get("symbol", "")
    comp = row.get("composite")
    dy = row.get("div_yield_pct")
    entry, target, stop = row.get("entry"), row.get("target"), row.get("stop")
    lots = row.get("lots")

    if lang == "ID":
        head = {
            "BUY": f"🟢 **{sym} — BUY.** Lolos gate dividend dan skornya bagus di "
                   "sisi value maupun timing.",
            "HOLD": f"⚪ **{sym} — HOLD.** Layak dipegang untuk dividend-nya, tapi "
                    "timing belum cukup menarik untuk menambah sekarang.",
            "SELL": f"🔴 **{sym} — SELL/hindari.** Skor lemah — momentum dan/atau "
                    "trend sedang melawan.",
            "SKIP": f"⚫ **{sym} — SKIP.** Dividend yield-nya kurang untuk lolos "
                    "strategi dividend+value ini.",
        }.get(act, f"**{sym}**")
        bits = []
        if comp is not None:
            bits.append(f"Skor total **{_fmt(comp)}/100** (60% fundamental + "
                        "40% technical).")
        if dy is not None:
            bits.append(f"Dividend yield ~**{_fmt(dy,2)}%**.")
        if act == "BUY" and entry and target and stop:
            up = (target / entry - 1) * 100
            rk = (1 - stop / entry) * 100
            bits.append(f"Rencana: beli sekitar **{_fmt(entry)}**, target profit "
                        f"~**{_fmt(target)}** (+{_fmt(up)}%), cut loss bila tembus "
                        f"**{_fmt(stop)}** (−{_fmt(rk)}%)"
                        + (f", ukuran **{lots} lot**." if lots else "."))
        return head + " " + " ".join(bits)

    head = {
        "BUY": f"🟢 **{sym} — BUY.** Passes the dividend gate and scores well on "
               "both value and timing.",
        "HOLD": f"⚪ **{sym} — HOLD.** Worth owning for the dividend, but the timing "
                "isn't compelling enough to add right now.",
        "SELL": f"🔴 **{sym} — SELL/avoid.** Weak score — momentum and/or trend are "
                "working against it.",
        "SKIP": f"⚫ **{sym} — SKIP.** Doesn't pay enough dividend to qualify for "
                "this dividend+value strategy.",
    }.get(act, f"**{sym}**")
    bits = []
    if comp is not None:
        bits.append(f"Overall score **{_fmt(comp)}/100** (60% fundamentals + "
                    "40% technicals).")
    if dy is not None:
        bits.append(f"Dividend yield ~**{_fmt(dy,2)}%**.")
    if act == "BUY" and entry and target and stop:
        up = (target / entry - 1) * 100
        rk = (1 - stop / entry) * 100
        bits.append(f"Plan: buy near **{_fmt(entry)}**, take profit around "
                    f"**{_fmt(target)}** (+{_fmt(up)}%), cut losses if it breaks "
                    f"**{_fmt(stop)}** (−{_fmt(rk)}%)"
                    + (f", suggested size **{lots} lot(s)**." if lots else "."))
    return head + " " + " ".join(bits)
