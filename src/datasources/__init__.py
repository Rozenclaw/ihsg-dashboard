"""Pluggable market-data sources. Select via config data.source."""
from __future__ import annotations

from .base import DataSource


def get_source(name: str) -> DataSource:
    name = (name or "yfinance").lower()
    if name == "yfinance":
        from .yfinance_source import YFinanceSource
        return YFinanceSource()
    if name == "synthetic":
        from .synthetic_source import SyntheticSource
        return SyntheticSource()
    raise ValueError(f"Unknown data source: {name}")
