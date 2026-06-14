"""A-share loader backed by the a-stock-data source priority."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import pandas as pd

from backtest.loaders.base import cached_loader_fetch, validate_date_range
from backtest.loaders.registry import register
from src.a_share_data_sources import fetch_daily_bars_from_dolt
from src.ashare_data_provider import baidu_kline_dataframe, normalize_ashare_code

logger = logging.getLogger(__name__)


@register
class DataLoader:
    """A-share loader using the a-stock-data priority chain."""

    name = "a_stock_data"
    markets = {"a_share"}
    requires_auth = False

    def __init__(self) -> None:
        self._mootdx = None
        self._tencent = None

    def is_available(self) -> bool:
        return True

    def fetch(
        self,
        codes: List[str],
        start_date: str,
        end_date: str,
        *,
        interval: str = "1D",
        fields: Optional[List[str]] = None,
    ) -> Dict[str, pd.DataFrame]:
        validate_date_range(start_date, end_date)
        result: Dict[str, pd.DataFrame] = {}
        for raw_code in codes:
            code = normalize_ashare_code(raw_code)
            try:
                df = cached_loader_fetch(
                    source=self.name,
                    symbol=code,
                    timeframe=interval,
                    start_date=start_date,
                    end_date=end_date,
                    fields=fields,
                    fetch=lambda code=code: self._fetch_one(code, start_date, end_date, interval),
                )
                if df is not None and not df.empty:
                    result[code] = self._attach_mas(df)
            except Exception as exc:
                logger.warning("a_stock_data failed for %s: %s", code, exc)
        return result

    def _fetch_one(
        self,
        code: str,
        start_date: str,
        end_date: str,
        interval: str,
    ) -> Optional[pd.DataFrame]:
        fetchers = []
        if interval == "1D":
            fetchers.append(self._fetch_via_local_dolt)
        fetchers.extend((self._fetch_via_mootdx, self._fetch_via_tencent, self._fetch_via_baidu))
        for fetcher in fetchers:
            try:
                df = fetcher(code, start_date, end_date, interval)
            except Exception as exc:
                logger.debug("%s fallback failed for %s: %s", fetcher.__name__, code, exc)
                df = None
            if df is not None and not df.empty:
                return df
        return None

    def _fetch_via_local_dolt(
        self,
        code: str,
        start_date: str,
        end_date: str,
        interval: str,
    ) -> Optional[pd.DataFrame]:
        if interval != "1D":
            return None
        return fetch_daily_bars_from_dolt(code, start_date, end_date)

    def _fetch_via_mootdx(
        self,
        code: str,
        start_date: str,
        end_date: str,
        interval: str,
    ) -> Optional[pd.DataFrame]:
        if self._mootdx is None:
            from backtest.loaders.mootdx_loader import DataLoader as MootdxLoader

            self._mootdx = MootdxLoader()
        if not self._mootdx.is_available():
            return None
        data = self._mootdx.fetch([code], start_date, end_date, interval=interval)
        return data.get(code)

    def _fetch_via_tencent(
        self,
        code: str,
        start_date: str,
        end_date: str,
        interval: str,
    ) -> Optional[pd.DataFrame]:
        if interval != "1D":
            return None
        if self._tencent is None:
            from backtest.loaders.tencent_loader import DataLoader as TencentLoader

            self._tencent = TencentLoader()
        data = self._tencent.fetch([code], start_date, end_date, interval=interval)
        return data.get(code)

    def _fetch_via_baidu(
        self,
        code: str,
        start_date: str,
        end_date: str,
        interval: str,
    ) -> Optional[pd.DataFrame]:
        if interval != "1D":
            return None
        df = baidu_kline_dataframe(code)
        if df is None or df.empty:
            return None
        return df.loc[start_date:end_date]

    @staticmethod
    def _attach_mas(df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy().sort_index()
        if "close" not in out.columns:
            return out
        for period in (5, 10, 20):
            col = f"ma{period}"
            if col not in out.columns:
                out[col] = out["close"].rolling(period, min_periods=1).mean()
        return out
