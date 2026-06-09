"""本地行情缓存

设计目标：
- 每次 akshare 拉到的行情，落盘到 data/market_cache/YYYY-MM-DD.json
- 历史日期的查询全部从本地读，不依赖外网
- 当日查询：先读本地 → miss 才调 akshare → 调完即落盘

存储格式（每个日期一个 JSON）::

    {
      "date": "2026-06-09",
      "fetched_at": "2026-06-09 21:30:00",
      "source": "akshare.stock_zh_a_spot",
      "stocks": {
        "300308": {"name": "中际旭创", "price": 148.6, "prev_close": 142.5,
                   "open": 142.5, "high": 150.2, "low": 140.3,
                   "pct_chg": 4.28, "volume": 12345678, "timestamp": "15:30:02"}
      }
    }

注：只存我们关心的 6 家公司（_FOCUS_COMPANIES），不全量存 5000+ 股票。
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


# 缓存根目录：项目根/data/market_cache/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CACHE_DIR = _PROJECT_ROOT / "data" / "market_cache"


def _ensure_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _path_for(date_str: str) -> Path:
    """某日缓存文件路径"""
    return CACHE_DIR / f"{date_str}.json"


def has_cache(date_str: str) -> bool:
    """某日是否已有本地缓存"""
    return _path_for(date_str).exists()


def read_cache(date_str: str) -> dict[str, Any] | None:
    """读某日缓存；不存在或损坏返回 None"""
    p = _path_for(date_str)
    if not p.exists():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def write_cache(date_str: str, payload: dict[str, Any]) -> Path:
    """写某日缓存（覆盖式）。返回写入路径。"""
    _ensure_dir()
    p = _path_for(date_str)
    payload = {
        "date": date_str,
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **payload,
    }
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return p


def list_cached_dates() -> list[str]:
    """列出所有已缓存的日期（升序）"""
    if not CACHE_DIR.exists():
        return []
    dates = []
    for p in CACHE_DIR.glob("*.json"):
        dates.append(p.stem)
    return sorted(dates)
