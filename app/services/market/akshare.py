"""AKShare 实时行情 + 本地缓存

数据流：
1. 读本地缓存（data/market_cache/YYYY-MM-DD.json）
2. miss + 是"今天" → 调 akshare.stock_zh_a_spot() 拉全 A 实时 → 过滤 6 家公司 → 落盘 → 返回
3. miss + 是历史日期 → 返回空 dict（工厂会 fallback 到 MockMarketData）
4. akshare 调用失败 → 抛 ConnectionError（工厂 fallback Mock）

板块聚合：板块 = 几个公司的平均涨跌幅（按 _SECTOR_STOCKS 定义）
"""
from __future__ import annotations

import warnings
from datetime import datetime
from typing import Any

from app.services.market.base import MarketData
from app.services.market import cache as local_cache

warnings.filterwarnings("ignore")


# 板块 → 股票清单（公司名, 股票代码）
# 来源：SECTOR_TERMS 中确认的实控上市公司 + 监控重点公司
_SECTOR_STOCKS: dict[str, list[tuple[str, str]]] = {
    "半导体": [
        ("中芯国际", "688981"),
        ("北方华创", "002371"),
        ("中微公司", "688012"),
        ("兆易创新", "603986"),
    ],
    "光通信": [
        ("中际旭创", "300308"),
        ("新易盛", "300502"),
        ("天孚通信", "300394"),
        ("剑桥科技", "603083"),
    ],
    "光芯片": [
        ("长光华芯", "688048"),
        ("源杰科技", "688498"),
        ("仕佳光子", "688313"),
        ("光库科技", "300620"),
    ],
}


def _is_today(date_str: str) -> bool:
    return date_str == datetime.now().strftime("%Y-%m-%d")


def _fetch_realtime_quotes(targets: dict[str, str]) -> dict[str, dict[str, Any]]:
    """调 akshare 拉全 A 实时行情，过滤出 targets 中的股票。

    Args:
        targets: {股票代码: 公司名}，如 {"300308": "中际旭创"}

    Returns:
        {股票代码: {name, price, prev_close, open, high, low, pct_chg, volume, timestamp}}
    """
    import akshare as ak

    df = ak.stock_zh_a_spot()
    out: dict[str, dict[str, Any]] = {}
    for _, row in df.iterrows():
        # 新浪返回代码形如 "sh600519" / "sz300308" / "bj920000"
        raw_code = str(row.get("代码", ""))
        code = raw_code[2:] if len(raw_code) > 2 and raw_code[:2] in ("sh", "sz", "bj") else raw_code
        if code not in targets:
            continue
        try:
            out[code] = {
                "name": str(row.get("名称", targets[code])),
                "price": float(row.get("最新价", 0) or 0),
                "prev_close": float(row.get("昨收", 0) or 0),
                "open": float(row.get("今开", 0) or 0),
                "high": float(row.get("最高", 0) or 0),
                "low": float(row.get("最低", 0) or 0),
                "pct_chg": float(row.get("涨跌幅", 0) or 0),
                "volume": float(row.get("成交量", 0) or 0),
                "timestamp": str(row.get("时间戳", "")),
            }
        except (TypeError, ValueError):
            continue
    return out


def _aggregate_sector_perf(stocks: dict[str, dict[str, Any]]) -> dict[str, float]:
    """按 _SECTOR_STOCKS 定义，把每只股票的 pct_chg 聚合成板块平均涨跌。"""
    out: dict[str, float] = {}
    for sector, members in _SECTOR_STOCKS.items():
        pcts = []
        for _, code in members:
            if code in stocks and stocks[code].get("pct_chg") is not None:
                pcts.append(stocks[code]["pct_chg"])
        if pcts:
            out[sector] = round(sum(pcts) / len(pcts), 2)
    return out


class AKShareMarketData(MarketData):
    """AKShare 实时 + 本地缓存优先。"""

    def __init__(self) -> None:
        self._akshare_available: bool | None = None

    def _akshare_ok(self) -> bool:
        if self._akshare_available is None:
            try:
                import akshare  # noqa: F401
                self._akshare_available = True
            except ImportError:
                self._akshare_available = False
        return self._akshare_available

    def _ensure_today_cache(self) -> dict[str, dict[str, Any]] | None:
        """确保今日缓存存在：先读本地，miss 则调 akshare 拉。返回今日 stocks dict 或 None。"""
        today = datetime.now().strftime("%Y-%m-%d")
        cached = local_cache.read_cache(today)
        if cached and cached.get("stocks"):
            return cached["stocks"]
        if not self._akshare_ok():
            return None
        targets = {code: name for members in _SECTOR_STOCKS.values() for name, code in members}
        try:
            stocks = _fetch_realtime_quotes(targets)
        except Exception:
            return None
        if not stocks:
            return None
        local_cache.write_cache(today, {
            "source": "akshare.stock_zh_a_spot",
            "stocks": stocks,
        })
        return stocks

    def get_sector_perf(self, date: str) -> dict[str, float]:
        """获取某日板块涨跌幅。"""
        # 1) 优先本地缓存
        cached = local_cache.read_cache(date)
        if cached and cached.get("stocks"):
            return _aggregate_sector_perf(cached["stocks"])

        # 2) miss + 是今日 → 调 akshare
        if _is_today(date):
            stocks = self._ensure_today_cache()
            if stocks:
                return _aggregate_sector_perf(stocks)

        # 3) miss + 历史 → 返回空（让工厂 fallback Mock）
        return {}

    def get_company_quote(self, code: str, date: str):
        """获取某只股票某日行情。"""
        cached = local_cache.read_cache(date)
        if cached and cached.get("stocks") and code in cached["stocks"]:
            return cached["stocks"][code]
        if _is_today(date):
            stocks = self._ensure_today_cache()
            if stocks and code in stocks:
                return stocks[code]
        return None
