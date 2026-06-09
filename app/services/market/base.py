"""MarketData 抽象接口定义

未来可扩展：TushareMarketData、AKShareMarketData。
本轮只提供接口骨架。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MarketData(ABC):
    """股价/板块数据接口

    返回某日各板块的涨跌幅（百分比，正数=涨，负数=跌）。
    """

    @abstractmethod
    def get_sector_perf(self, date: str) -> dict[str, float]:
        """获取某日板块涨跌幅

        Args:
            date: 日期字符串，格式 YYYY-MM-DD。

        Returns:
            字典，key 是板块名称（如 "半导体"、"光通信"、"光芯片"），value 是涨跌幅（百分比）。
        """
        raise NotImplementedError

    def get_company_quote(self, code: str, date: str) -> dict[str, Any] | None:
        """获取某只股票某日行情（可选实现）

        Returns:
            {"open": ..., "close": ..., "high": ..., "low": ..., "pct_chg": ...} 或 None
        """
        return None
