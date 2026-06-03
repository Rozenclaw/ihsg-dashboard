"""Live data via yfinance (Yahoo Finance, unofficial). Covers ^JKSE + *.JK."""
from __future__ import annotations

import pandas as pd

from .base import DataSource


class YFinanceSource(DataSource):
    name = "yfinance"

    def __init__(self):
        try:
            import yfinance as yf  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "yfinance not installed. Run: pip install -r requirements.txt"
            ) from e

    def history(self, symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
        import yfinance as yf
        df = yf.download(symbol, period=period, interval=interval,
                         progress=False, auto_adjust=True)
        if df is None or df.empty:
            return pd.DataFrame()
        # yfinance may return a MultiIndex column frame for single symbols.
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.rename(columns={
            "Open": "open", "High": "high", "Low": "low",
            "Close": "close", "Volume": "volume",
        })
        keep = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
        df = df[keep].dropna(how="all")
        df.index = pd.to_datetime(df.index)
        return df

    def fundamentals(self, symbol: str) -> dict:
        import yfinance as yf
        try:
            t = yf.Ticker(symbol)
            info = t.info or {}
        except Exception:
            return {}
        low = info.get("fiftyTwoWeekLow")
        high = info.get("fiftyTwoWeekHigh")
        rng = f"{low}-{high}" if low and high else None

        # Yahoo gives some ratios as fractions (0.18 = 18%); normalize to %.
        def _pct(v):
            return v * 100 if isinstance(v, (int, float)) else None

        # Forward ex-dividend date (epoch seconds) -> ISO date, if available.
        ex_div = info.get("exDividendDate")
        ex_div_iso = None
        if ex_div:
            try:
                ex_div_iso = pd.to_datetime(ex_div, unit="s").strftime("%Y-%m-%d")
            except Exception:
                try:
                    ex_div_iso = pd.to_datetime(ex_div).strftime("%Y-%m-%d")
                except Exception:
                    ex_div_iso = None

        price = info.get("currentPrice") or info.get("regularMarketPrice")

        # Dividend yield, computed the robust way: annual dividend per share /
        # price. This is immune to Yahoo's format changes (their `dividendYield`
        # field flipped between fraction and percent in 2025, causing a 100x bug).
        # Prefer the trailing annual dividend rate (actual cash paid last 12mo).
        annual_div = (info.get("trailingAnnualDividendRate")
                      or info.get("dividendRate")
                      or info.get("lastDividendValue"))
        div_yield = None
        if annual_div and price and price > 0:
            div_yield = round(annual_div / price * 100, 2)
        else:
            # Fallback: Yahoo's own yield field, auto-detecting its format.
            raw = info.get("dividendYield") or info.get("trailingAnnualDividendYield")
            if isinstance(raw, (int, float)) and raw > 0:
                # If <= 1 it's almost always a fraction (0.0067); if it's a
                # plausible percent already (e.g. 5.2) keep it. Cap sanity at 60%.
                div_yield = round(raw * 100, 2) if raw <= 0.6 else round(raw, 2)
                if div_yield > 60:   # clearly a mis-scaled value -> rescale down
                    div_yield = round(div_yield / 100, 2)

        return {
            "price": price,
            "market_cap": info.get("marketCap"),
            "beta": info.get("beta"),
            "last_dividend": annual_div,
            "range_52w": rng,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            # Richer fundamentals (Tier 1). payout/ROE/earnings are still
            # fractions in Yahoo, so _pct (×100) is correct for those.
            "pe": info.get("trailingPE") or info.get("forwardPE"),
            "pb": info.get("priceToBook"),
            "roe": _pct(info.get("returnOnEquity")),
            "debt_to_equity": info.get("debtToEquity"),
            "payout_ratio": _pct(info.get("payoutRatio")),
            "earnings_growth": _pct(info.get("earningsGrowth")
                                    or info.get("earningsQuarterlyGrowth")),
            "dividend_yield": div_yield,
            "ex_dividend_date": ex_div_iso,
            "updated_at": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def news(self, symbol: str, limit: int = 6) -> list[dict]:
        """Free headlines via yfinance. Returns [{title, publisher, link, ts}]."""
        import yfinance as yf
        try:
            items = yf.Ticker(symbol).news or []
        except Exception:
            return []
        out = []
        for it in items[:limit]:
            # yfinance news shape varies; handle both flat and {'content': {...}}.
            c = it.get("content", it)
            title = c.get("title") or it.get("title")
            if not title:
                continue
            pub = (c.get("provider", {}) or {}).get("displayName") \
                if isinstance(c.get("provider"), dict) else it.get("publisher")
            link = (c.get("canonicalUrl", {}) or {}).get("url") if isinstance(
                c.get("canonicalUrl"), dict) else it.get("link")
            out.append({"title": title, "publisher": pub or "", "link": link or "",
                        "ts": c.get("pubDate") or it.get("providerPublishTime")})
        return out
