"""Utilities adapted from a-stock-data for A-share market access."""

from __future__ import annotations

import urllib.request
import re
from typing import Any

import pandas as pd
import requests

_A_SHARE_RE = re.compile(r"^(?:SH|SZ|BJ)?(\d{6})(?:\.(SH|SZ|BJ))?$", re.I)


def normalize_ashare_code(code: str) -> str:
    """Normalize an A-share symbol to ``000001.SZ`` form."""
    raw = (code or "").strip().upper()
    match = _A_SHARE_RE.match(raw)
    if not match:
        return raw
    digits = match.group(1)
    suffix = match.group(2) or market_suffix(digits)
    return f"{digits}.{suffix}"


def bare_ashare_code(code: str) -> str:
    """Return the 6-digit ticker when *code* looks like a CN equity symbol."""
    normalized = normalize_ashare_code(code)
    return normalized.split(".")[0] if "." in normalized else normalized


def market_suffix(code: str) -> str:
    digits = str(code).strip()
    if digits.startswith(("6", "9")):
        return "SH"
    if digits.startswith("8"):
        return "BJ"
    return "SZ"


def market_prefix(code: str) -> str:
    return market_suffix(code).lower()


def tencent_quote(codes: list[str]) -> dict[str, dict[str, Any]]:
    """Fetch Tencent Finance quote snapshots for A-shares / indices / ETFs."""
    digits = [bare_ashare_code(code) for code in codes if bare_ashare_code(code).isdigit()]
    if not digits:
        return {}
    prefixed = [f"{market_prefix(code)}{code}" for code in digits]
    url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = resp.read().decode("gbk", errors="ignore")

    result: dict[str, dict[str, Any]] = {}
    for line in data.strip().split(";"):
        if not line.strip() or "=" not in line or '"' not in line:
            continue
        key = line.split("=")[0].split("_")[-1]
        vals = line.split('"')[1].split("~")
        if len(vals) < 53:
            continue
        code = key[2:]
        result[code] = {
            "code": code,
            "name": vals[1],
            "price": _safe_float(vals[3]),
            "last_close": _safe_float(vals[4]),
            "open": _safe_float(vals[5]),
            "high": _safe_float(vals[33]),
            "low": _safe_float(vals[34]),
            "change_amt": _safe_float(vals[31]),
            "change_pct": _safe_float(vals[32]),
            "amount_wan": _safe_float(vals[37]),
            "turnover_rate": _safe_float(vals[38]),
            "pe_ttm": _safe_float(vals[39]),
            "amplitude_pct": _safe_float(vals[43]),
            "total_mv_yi": _safe_float(vals[44]),
            "circ_mv_yi": _safe_float(vals[45]),
            "pb": _safe_float(vals[46]),
            "limit_up": _safe_float(vals[47]),
            "limit_down": _safe_float(vals[48]),
            "volume_ratio": _safe_float(vals[49]),
            "pe_static": _safe_float(vals[52]),
        }
    return result


def baidu_kline_dataframe(code: str, *, start_time: str = "", k_type: str = "1") -> pd.DataFrame | None:
    """Return a normalized daily bar DataFrame from Baidu's K-line endpoint."""
    digits = bare_ashare_code(code)
    if not digits.isdigit():
        return None

    params = {
        "all": "1",
        "isIndex": "false",
        "isBk": "false",
        "isBlock": "false",
        "isFutures": "false",
        "isStock": "true",
        "newFormat": "1",
        "group": "quotation_kline_ab",
        "finClientType": "pc",
        "code": digits,
        "start_time": start_time,
        "ktype": k_type,
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/vnd.finance-web.v1+json",
        "Origin": "https://gushitong.baidu.com",
        "Referer": "https://gushitong.baidu.com/",
    }
    resp = requests.get(
        "https://finance.pae.baidu.com/selfselect/getstockquotation",
        params=params,
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    payload = resp.json()
    market_data = (((payload.get("Result") or {}).get("newMarketData")) or {})
    keys = market_data.get("keys") or []
    rows_blob = market_data.get("marketData") or ""
    rows = [row.split(",") for row in rows_blob.split(";") if row.strip()]
    if not keys or not rows:
        return None

    frame = pd.DataFrame(rows, columns=keys[: len(rows[0])])
    rename_map = {
        "time": "trade_date",
        "date": "trade_date",
        "open": "open",
        "close": "close",
        "high": "high",
        "low": "low",
        "volume": "volume",
        "ma5avgprice": "ma5",
        "ma10avgprice": "ma10",
        "ma20avgprice": "ma20",
    }
    if {"time", "open", "close", "high", "low"} - set(frame.columns):
        return None
    keep_cols = [col for col in frame.columns if col in rename_map]
    frame = frame[keep_cols].rename(columns=rename_map)
    frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="coerce")
    for col in ("open", "high", "low", "close", "volume", "ma5", "ma10", "ma20"):
        if col in frame.columns:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame = frame.dropna(subset=["trade_date", "open", "high", "low", "close"])
    if frame.empty:
        return None
    frame = frame.set_index("trade_date").sort_index()
    if "volume" not in frame.columns:
        frame["volume"] = 0.0
    ordered = ["open", "high", "low", "close", "volume"]
    extras = [col for col in ("ma5", "ma10", "ma20") if col in frame.columns]
    return frame[ordered + extras]


def full_valuation(code: str) -> dict[str, Any]:
    digits = bare_ashare_code(code)
    return tencent_quote([digits]).get(digits, {})


def _safe_float(value: str) -> float | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None
