"""MarketData 抽象接口

v2.2 真实数据源：AKShare + 本地缓存（每日拉一次 6 家重点公司实时价）
v2.2 兜底：MockMarketData（写死字典 + 确定性扰动）

工厂 get_market_data() 返回 AKShareMarketData，由调用方在数据缺失时
fallback 到 MockMarketData（见 daily_brief._market_snapshot）。
"""
from __future__ import annotations

from app.services.market.akshare import AKShareMarketData
from app.services.market.base import MarketData
from app.services.market.mock import MockMarketData


def get_market_data() -> MarketData:
    """工厂函数：默认返回 AKShare 实时 + 本地缓存实现。

    注：akshare 包不存在时 AKShareMarketData 会自动降级返回空，
    不需要在此处 try/except。调用方负责 fallback。
    """
    return AKShareMarketData()


__all__ = ["AKShareMarketData", "MarketData", "MockMarketData", "get_market_data"]
