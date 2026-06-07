"""DataSource interface. Implement these two methods for any provider."""
from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class DataSource(ABC):
    name: str = "base"

    @abstractmethod
    def history(self, symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
        """Return a DataFrame indexed by date with columns:
        open, high, low, close, volume (lowercase)."""
        raise NotImplementedError

    def history_batch(self, symbols, period: str = "2y",
                      interval: str = "1d") -> dict:
        """Optional bulk price fetch -> {symbol: DataFrame}. Providers that can
        fetch many symbols in one request (e.g. yfinance) should override this for
        a big speedup. Default falls back to one history() call per symbol."""
        out = {}
        for s in symbols:
            try:
                out[s] = self.history(s, period, interval)
            except Exception:
                import pandas as pd
                out[s] = pd.DataFrame()
        return out

    def fundamentals(self, symbol: str) -> dict:
        """Optional. Return a dict with keys like price, market_cap, beta,
        last_dividend, range_52w, sector, industry, name. Default: empty."""
        return {}

    def news(self, symbol: str, limit: int = 6) -> list[dict]:
        """Optional. Return recent headlines [{title, publisher, link, ts}]."""
        return []
