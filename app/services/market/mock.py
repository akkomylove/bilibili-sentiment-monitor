"""MockMarketData

返回固定涨跌幅或带轻微扰动的 mock 数据，用于：
1. 端到端测试（不依赖真实数据源）
2. UI 演示
3. 联调时占位

未来替换为 TushareMarketData / AKShareMarketData 时，保持 MarketData 接口即可。
"""

from __future__ import annotations

import hashlib
from typing import Any

from app.services.market.base import MarketData


# 基础涨跌幅表（按板块）
_BASE_PERF = {
    "半导体": -2.3,
    "光通信": +1.5,
    "光芯片": -0.8,
    "AI 算力": +0.6,
    "CPO": +2.1,
    "PCB": -1.2,
}

# 重点公司行情模板
_COMPANY_QUOTES = {
    "中际旭创": {"open": 142.5, "close": 148.6, "high": 150.2, "low": 140.3, "pct_chg": +4.28},
    "新易盛": {"open": 88.0, "close": 91.5, "high": 92.7, "low": 86.4, "pct_chg": +3.98},
    "天孚通信": {"open": 110.0, "close": 108.4, "high": 111.5, "low": 107.0, "pct_chg": -1.45},
    "中芯国际": {"open": 56.0, "close": 54.2, "high": 56.5, "low": 53.8, "pct_chg": -3.21},
    "长光华芯": {"open": 48.0, "close": 49.5, "high": 50.2, "low": 47.6, "pct_chg": +3.13},
    "源杰科技": {"open": 130.0, "close": 128.4, "high": 131.5, "low": 127.0, "pct_chg": -1.23},
}


def _seeded_noise(date: str, key: str, amplitude: float = 0.5) -> float:
    """根据 (date, key) 生成确定性的伪随机扰动，幅度 ±amplitude

    用 MD5(date+key) 转为 [0, 1) 区间再映射。
    """
    h = hashlib.md5(f"{date}|{key}".encode()).hexdigest()
    seed = int(h[:8], 16) / 0xFFFFFFFF  # [0, 1)
    return (seed - 0.5) * 2 * amplitude  # [-amp, +amp]


class MockMarketData(MarketData):
    """固定模板 + 确定性扰动的 Mock 实现

    相同日期 + 板块 → 相同结果（便于测试断言）。
    """

    def __init__(self, noise_amplitude: float = 0.5) -> None:
        self.noise_amplitude = noise_amplitude

    def get_sector_perf(self, date: str) -> dict[str, float]:
        result: dict[str, float] = {}
        for sector, base in _BASE_PERF.items():
            noise = _seeded_noise(date, sector, self.noise_amplitude)
            result[sector] = round(base + noise, 2)
        return result

    def get_company_quote(self, code: str, date: str) -> dict[str, Any] | None:
        if code not in _COMPANY_QUOTES:
            return None
        quote = dict(_COMPANY_QUOTES[code])
        # 加一点日期相关扰动
        noise = _seeded_noise(date, code, 0.3)
        quote["pct_chg"] = round(quote["pct_chg"] + noise, 2)
        quote["close"] = round(quote["close"] * (1 + noise / 100), 2)
        return quote
