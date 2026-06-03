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

    def fundamentals(self, symbol: str) -> dict:
        """Optional. Return a dict with keys like price, market_cap, beta,
        last_dividend, range_52w, sector, industry. Default: empty."""
        return {}

    def news(self, symbol: str, limit: int = 6) -> list[dict]:
        """Optional. Return recent headlines [{title, publisher, link, ts}]."""
        return []
