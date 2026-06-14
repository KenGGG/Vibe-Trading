"""Local A-share data source status and access helpers."""

from __future__ import annotations

import csv
import io
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from src.ashare_data_provider import baidu_kline_dataframe, normalize_ashare_code, tencent_quote
from src.market_data import get_loader

DEFAULT_DOLT_DB_PATH = Path(os.getenv("A_SHARE_DOLT_DB_PATH", "/data/investment_data"))
DEFAULT_STATUS_SYMBOL = os.getenv("A_SHARE_STATUS_SYMBOL", "000001.SZ")

A_STOCK_DATA_LAYER_SPECS: list[dict[str, Any]] = [
    {
        "key": "market",
        "name": "行情层",
        "description": "K 线、五档盘口、估值指标、指数与 ETF 行情。",
        "capabilities": ["K线(含 MA5/10/20)", "五档盘口", "PE/PB/市值", "指数/ETF"],
        "providers": [
            {"name": "mootdx", "role": "A 股历史 / 分钟级行情"},
            {"name": "腾讯财经", "role": "实时行情 / 在线兜底"},
            {"name": "百度K线", "role": "日线补齐"},
        ],
    },
    {
        "key": "research",
        "name": "研报层",
        "description": "研报列表、PDF 下载、一致预期与自然语言搜索。",
        "capabilities": ["研报列表", "PDF下载", "一致预期", "NL搜索"],
        "providers": [
            {"name": "东财 reportapi", "role": "研报与一致预期"},
            {"name": "同花顺", "role": "研报补充"},
            {"name": "iwencai", "role": "自然语言检索"},
        ],
    },
    {
        "key": "signals",
        "name": "信号层",
        "description": "强势股、题材归因、北向资金、龙虎榜等主题信号。",
        "capabilities": ["强势股", "题材归因", "北向资金", "板块归属", "资金流向", "龙虎榜", "解禁", "行业对比"],
        "providers": [
            {"name": "同花顺", "role": "强势股 / 板块归属"},
            {"name": "东财", "role": "资金流 / 龙虎榜 / 解禁"},
        ],
    },
    {
        "key": "capital",
        "name": "资金面",
        "description": "融资融券、大宗交易、股东户数、分红送转与资金流。",
        "capabilities": ["融资融券", "大宗交易", "股东户数", "分红送转", "分钟资金流", "120日资金流"],
        "providers": [
            {"name": "东财 datacenter", "role": "资金面核心数据"},
            {"name": "东财 push2", "role": "资金流补充"},
        ],
    },
    {
        "key": "news",
        "name": "新闻层",
        "description": "个股新闻与全球资讯。",
        "capabilities": ["个股新闻", "全球资讯"],
        "providers": [
            {"name": "东财 HTTP", "role": "新闻直连"},
        ],
    },
    {
        "key": "fundamental",
        "name": "基础数据",
        "description": "季报字段、F10 资料与三大财务报表。",
        "capabilities": ["季报37字段", "F10九大类", "财报三表"],
        "providers": [
            {"name": "mootdx", "role": "基础快照"},
            {"name": "东财", "role": "F10 / 财报"},
            {"name": "新浪", "role": "基础信息补充"},
        ],
    },
    {
        "key": "announcements",
        "name": "公告层",
        "description": "沪深北全量公告。",
        "capabilities": ["沪深北全量公告"],
        "providers": [
            {"name": "巨潮 cninfo", "role": "公告主源"},
            {"name": "mootdx", "role": "公告补充"},
        ],
    },
]


@dataclass
class DoltCommandResult:
    success: bool
    output: str


def dolt_repo_path() -> Path:
    """Return the configured local Dolt repo path."""
    return DEFAULT_DOLT_DB_PATH


def _dolt_available() -> bool:
    return shutil.which("dolt") is not None


def _repo_ready(path: Path) -> bool:
    return path.exists() and path.is_dir() and (path / ".dolt").exists()


def _run_dolt(args: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["dolt", *args],
        cwd=dolt_repo_path(),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _query_csv(sql: str, *, timeout: int = 30) -> list[dict[str, str]]:
    proc = _run_dolt(["sql", "-r", "csv", "-q", sql], timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "dolt sql failed").strip())
    text = proc.stdout.strip()
    if not text:
        return []
    return list(csv.DictReader(io.StringIO(text)))


def _query_scalar(sql: str, key: str, *, timeout: int = 30) -> str | None:
    rows = _query_csv(sql, timeout=timeout)
    if not rows:
        return None
    value = rows[0].get(key)
    return value.strip() if isinstance(value, str) and value.strip() else value


def _table_exists(table: str) -> bool:
    rows = _query_csv("show tables", timeout=15)
    if not rows:
        return False
    only_key = next(iter(rows[0].keys()), "")
    return any((row.get(only_key) or "").strip() == table for row in rows)


def _normalize_local_symbol(symbol: str) -> str:
    raw = (symbol or "").strip().upper()
    if raw.startswith(("SH", "SZ", "BJ")) and len(raw) == 8:
        return f"{raw[2:]}.{raw[:2]}"
    return normalize_ashare_code(raw)


def _table_symbol_variants(code: str, table: str) -> list[str]:
    normalized = normalize_ashare_code(code)
    digits, suffix = normalized.split(".")
    if table == "final_a_stock_eod_price":
        return [f"{suffix}{digits}"]
    return [normalized]


def fetch_daily_bars_from_dolt(
    code: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame | None:
    """Fetch daily bars for one A-share symbol from the local Dolt repo."""
    path = dolt_repo_path()
    if not _dolt_available() or not _repo_ready(path):
        return None

    for table in ("final_a_stock_eod_price", "ts_a_stock_eod_price"):
        if not _table_exists(table):
            continue
        symbols = _table_symbol_variants(code, table)
        symbol_sql = ", ".join(f"'{symbol}'" for symbol in symbols)
        rows = _query_csv(
            (
                "select tradedate, symbol, open, high, low, close, volume, amount, adjclose "
                f"from {table} "
                f"where symbol in ({symbol_sql}) "
                f"and tradedate >= '{start_date}' and tradedate <= '{end_date}' "
                "order by tradedate"
            ),
            timeout=30,
        )
        if not rows:
            continue

        frame = pd.DataFrame(rows)
        frame["trade_date"] = pd.to_datetime(frame["tradedate"], errors="coerce")
        for col in ("open", "high", "low", "close", "volume", "amount", "adjclose"):
            if col in frame.columns:
                frame[col] = pd.to_numeric(frame[col], errors="coerce")
        frame["symbol"] = frame["symbol"].map(_normalize_local_symbol)
        frame = frame.dropna(subset=["trade_date", "open", "high", "low", "close"])
        if frame.empty:
            continue
        frame = frame.set_index("trade_date").sort_index()
        ordered = ["open", "high", "low", "close", "volume"]
        if "amount" in frame.columns:
            ordered.append("amount")
        if "adjclose" in frame.columns:
            ordered.append("adjclose")
        return frame[ordered]

    return None


def get_local_dolt_status() -> dict[str, Any]:
    """Return local Dolt repository status for the A-share daily database."""
    path = dolt_repo_path()
    status: dict[str, Any] = {
        "available": False,
        "path": str(path),
        "command_available": _dolt_available(),
        "repo_ready": _repo_ready(path),
        "branch": None,
        "clean": None,
        "message": "",
        "preferred_table": None,
        "latest_trade_date": None,
        "tables": [],
    }
    if not status["command_available"]:
        status["message"] = "未找到 dolt 命令。"
        return status
    if not status["repo_ready"]:
        status["message"] = "本地 A 股 Dolt 仓库不存在或未初始化。"
        return status

    proc = _run_dolt(["status"], timeout=20)
    status["available"] = proc.returncode == 0
    output = (proc.stdout or proc.stderr or "").strip()
    status["clean"] = "nothing to commit" in output.lower()
    branch_match = next((line for line in output.splitlines() if line.startswith("On branch ")), "")
    status["branch"] = branch_match.replace("On branch ", "").strip() or None
    status["message"] = output

    preferred_table = None
    for table_name in ("final_a_stock_eod_price", "ts_a_stock_eod_price", "ts_trade_day_calendar"):
        if not _table_exists(table_name):
            continue
        date_col = "date" if table_name == "ts_trade_day_calendar" else "tradedate"
        latest = _query_scalar(f"select max({date_col}) as latest from {table_name}", "latest", timeout=20)
        count = _query_scalar(f"select count(*) as cnt from {table_name}", "cnt", timeout=20)
        table_status = {
            "name": table_name,
            "latest_trade_date": latest,
            "row_count": int(count) if count and str(count).isdigit() else 0,
        }
        status["tables"].append(table_status)
        if preferred_table is None and table_name in {"final_a_stock_eod_price", "ts_a_stock_eod_price"}:
            preferred_table = table_name
            status["latest_trade_date"] = latest

    status["preferred_table"] = preferred_table
    return status


def update_local_dolt_data() -> DoltCommandResult:
    """Run ``dolt pull`` in the configured local A-share repo."""
    path = dolt_repo_path()
    if not _dolt_available():
        return DoltCommandResult(False, "未找到 dolt 命令。")
    if not _repo_ready(path):
        return DoltCommandResult(False, f"本地仓库不可用：{path}")
    proc = _run_dolt(["pull"], timeout=300)
    output = "\n".join(part for part in ((proc.stdout or "").strip(), (proc.stderr or "").strip()) if part).strip()
    return DoltCommandResult(proc.returncode == 0, output or "dolt pull 已执行，但没有输出。")


def get_a_stock_data_status() -> dict[str, Any]:
    """Return status for the network-backed a-stock-data priority chain."""
    components: list[dict[str, Any]] = []
    latest_trade_date: str | None = None

    try:
        loader_cls = get_loader("a_stock_data")
        loader = loader_cls()
        components.append({
            "name": "a_stock_data loader",
            "available": bool(loader.is_available()),
            "detail": "A 股默认 loader，优先级为 mootdx -> 腾讯 -> 百度。",
        })
    except Exception as exc:
        components.append({
            "name": "a_stock_data loader",
            "available": False,
            "detail": f"loader 初始化失败：{exc}",
        })

    try:
        from backtest.loaders.mootdx_loader import DataLoader as MootdxLoader

        mootdx_loader = MootdxLoader()
        mootdx_latest = None
        if mootdx_loader.is_available():
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            sample = mootdx_loader.fetch(
                [DEFAULT_STATUS_SYMBOL],
                start_date.isoformat(),
                end_date.isoformat(),
                interval="1D",
            ).get(DEFAULT_STATUS_SYMBOL)
            if sample is not None and not sample.empty:
                mootdx_latest = str(sample.index.max().date())
                latest_trade_date = latest_trade_date or mootdx_latest
        components.append({
            "name": "mootdx",
            "available": bool(mootdx_loader.is_available()),
            "detail": "适合 A 股历史 / 分钟级行情，优先级最高。",
            "latest_trade_date": mootdx_latest,
        })
    except Exception as exc:
        components.append({
            "name": "mootdx",
            "available": False,
            "detail": f"mootdx 不可用：{exc}",
        })

    try:
        quote = tencent_quote([DEFAULT_STATUS_SYMBOL])
        normalized = normalize_ashare_code(DEFAULT_STATUS_SYMBOL).split(".")[0]
        sample = quote.get(normalized) or {}
        tencent_latest = None
        try:
            from backtest.loaders.tencent_loader import DataLoader as TencentLoader

            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            daily_sample = TencentLoader().fetch(
                [DEFAULT_STATUS_SYMBOL],
                start_date.isoformat(),
                end_date.isoformat(),
                interval="1D",
            ).get(DEFAULT_STATUS_SYMBOL)
            if daily_sample is not None and not daily_sample.empty:
                tencent_latest = str(daily_sample.index.max().date())
                latest_trade_date = latest_trade_date or tencent_latest
        except Exception:
            tencent_latest = None
        components.append({
            "name": "腾讯行情",
            "available": bool(sample),
            "detail": f"最新价：{sample.get('price')}" if sample else "未返回可用报价。",
            "latest_trade_date": tencent_latest,
        })
    except Exception as exc:
        components.append({
            "name": "腾讯行情",
            "available": False,
            "detail": f"腾讯行情探测失败：{exc}",
        })

    try:
        frame = baidu_kline_dataframe(DEFAULT_STATUS_SYMBOL)
        baidu_latest = None if frame is None or frame.empty else str(frame.index.max().date())
        latest_trade_date = latest_trade_date or baidu_latest
        components.append({
            "name": "百度 K 线",
            "available": bool(frame is not None and not frame.empty),
            "detail": f"样本最新交易日：{baidu_latest}" if baidu_latest else "未返回日线样本。",
            "latest_trade_date": baidu_latest,
        })
    except Exception as exc:
        components.append({
            "name": "百度 K 线",
            "available": False,
            "detail": f"百度 K 线探测失败：{exc}",
        })

    available = any(bool(item.get("available")) for item in components)
    layers = _build_a_stock_data_layers(components)
    integrated_layers = sum(1 for layer in layers if layer["integrated"])
    callable_layers = sum(1 for layer in layers if layer["callable"])
    verified_layers = sum(1 for layer in layers if layer["verified"])
    return {
        "available": available,
        "latest_trade_date": latest_trade_date,
        "components": components,
        "layers": layers,
        "integration_summary": {
            "total_layers": len(layers),
            "integrated_layers": integrated_layers,
            "callable_layers": callable_layers,
            "verified_layers": verified_layers,
            "message": (
                "当前已接入并验证：本地 Dolt 日频数据库 + a-stock-data 行情层。"
                "其余六层尚未发现运行时接入代码，页面仅展示真实接入状态。"
            ),
        },
        "preferred_usage": {
            "intraday_or_realtime": "a_stock_data（mootdx / 腾讯 / 百度）",
            "fallback_daily": "a_stock_data（日线补齐与无密钥在线兜底）",
        },
    }


def get_a_share_data_overview() -> dict[str, Any]:
    """Return merged A-share data-source status and the runtime preference."""
    return {
        "as_of": datetime_now_iso(),
        "local_database": get_local_dolt_status(),
        "a_stock_data": get_a_stock_data_status(),
        "priority": {
            "historical_daily": "本地 Dolt 日频库（优先用于 A 股 1D 历史回测）",
            "intraday_or_realtime": "a_stock_data（优先用于实时 / 分钟级 / 在线补齐）",
            "fallback": "当本地库不可用或区间缺失时，回退到 a_stock_data 链路。",
        },
    }


def _build_a_stock_data_layers(components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    component_by_name = {str(item.get("name")): item for item in components}

    layers: list[dict[str, Any]] = []
    for spec in A_STOCK_DATA_LAYER_SPECS:
        provider_runtime: dict[str, dict[str, Any] | None] = {}
        if spec["key"] == "market":
            provider_runtime = {
                "mootdx": _provider_from_component(
                    component_by_name.get("mootdx"),
                    "已接入当前运行时，用于 A 股历史 / 分钟级行情优先链路。",
                ),
                "腾讯财经": _provider_from_component(
                    component_by_name.get("腾讯行情"),
                    "已接入当前运行时，用于实时行情与在线兜底。",
                ),
                "百度K线": _provider_from_component(
                    component_by_name.get("百度 K 线"),
                    "已接入当前运行时，用于日线补齐。",
                ),
            }

        providers: list[dict[str, Any]] = []
        for provider in spec["providers"]:
            runtime_status = provider_runtime.get(provider["name"])
            if runtime_status is None:
                providers.append({
                    "name": provider["name"],
                    "role": provider["role"],
                    "integrated": False,
                    "callable": False,
                    "verified": False,
                    "detail": "当前系统未发现对应运行时接入代码。",
                    "latest_trade_date": None,
                })
            else:
                providers.append({
                    "name": provider["name"],
                    "role": provider["role"],
                    **runtime_status,
                })

        integrated = any(item["integrated"] for item in providers)
        callable_ = any(item["callable"] for item in providers)
        verified = any(item["verified"] for item in providers)
        notes = (
            "当前层已接入系统，并参与实际取数优先链路。"
            if integrated
            else "当前层尚未接入系统运行时，暂不能在当前应用内调用。"
        )
        layers.append({
            "key": spec["key"],
            "name": spec["name"],
            "description": spec["description"],
            "capabilities": spec["capabilities"],
            "integrated": integrated,
            "callable": callable_,
            "verified": verified,
            "providers": providers,
            "notes": notes,
        })
    return layers


def _provider_from_component(component: dict[str, Any] | None, detail_prefix: str) -> dict[str, Any] | None:
    if component is None:
        return None

    available = bool(component.get("available"))
    detail = str(component.get("detail") or "").strip()
    combined_detail = detail_prefix if not detail else f"{detail_prefix} {detail}"
    return {
        "integrated": True,
        "callable": available,
        "verified": available,
        "detail": combined_detail,
        "latest_trade_date": component.get("latest_trade_date"),
    }


def datetime_now_iso() -> str:
    from datetime import datetime

    return datetime.now().isoformat()
