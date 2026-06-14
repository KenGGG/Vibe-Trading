from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from backtest.loaders.a_stock_data_loader import DataLoader


def _frame() -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=6, freq="D")
    df = pd.DataFrame(
        {
            "open": [1, 2, 3, 4, 5, 6],
            "high": [2, 3, 4, 5, 6, 7],
            "low": [0, 1, 2, 3, 4, 5],
            "close": [1, 2, 3, 4, 5, 6],
            "volume": [10, 20, 30, 40, 50, 60],
        },
        index=idx,
    )
    df.index.name = "trade_date"
    return df


def test_prefers_mootdx_when_available(monkeypatch) -> None:
    loader = DataLoader()
    mootdx = SimpleNamespace(
        is_available=lambda: True,
        fetch=lambda *args, **kwargs: {"000001.SZ": _frame()},
    )
    tencent = SimpleNamespace(fetch=lambda *args, **kwargs: {"000001.SZ": _frame() * 0})
    monkeypatch.setattr(loader, "_mootdx", mootdx)
    monkeypatch.setattr(loader, "_tencent", tencent)

    out = loader.fetch(["000001.SZ"], "2026-01-01", "2026-01-06")

    assert "000001.SZ" in out
    assert out["000001.SZ"]["close"].iloc[-1] == 6
    assert {"ma5", "ma10", "ma20"} <= set(out["000001.SZ"].columns)


def test_falls_back_to_baidu_when_subloaders_empty(monkeypatch) -> None:
    loader = DataLoader()
    monkeypatch.setattr(loader, "_mootdx", SimpleNamespace(is_available=lambda: False))
    monkeypatch.setattr(loader, "_tencent", SimpleNamespace(fetch=lambda *args, **kwargs: {}))
    monkeypatch.setattr(
        "backtest.loaders.a_stock_data_loader.baidu_kline_dataframe",
        lambda code: _frame()[["open", "high", "low", "close", "volume"]],
    )

    out = loader.fetch(["000001.SZ"], "2026-01-01", "2026-01-06")

    assert "000001.SZ" in out
    assert out["000001.SZ"]["close"].iloc[0] == 1
