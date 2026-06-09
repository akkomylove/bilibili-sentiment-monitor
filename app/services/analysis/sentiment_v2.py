"""简化版情感分析（sentiment_v2）

策略：
1. 优先用投资情感词典（SENTIMENT_BULLISH / SENTIMENT_BEARISH）进行强分类
2. 未命中词典的评论，调用 SnowNLP 评分，按 0.4/0.6 阈值分类
3. 接受 list[dict] 输入（每条评论至少包含 content 字段），便于在 pipeline 测试中直接传样本
4. 支持空评论和异常评论的降级处理

设计原则：
- 纯函数，不依赖数据库或网络
- 输入/输出 JSON-serializable，方便端到端测试断言
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from snownlp import SnowNLP

from app.services.analysis.investment_dict import SENTIMENT_BEARISH, SENTIMENT_BULLISH


# SnowNLP 分类阈值（v1 sentiment 沿用）
THRESHOLD_POSITIVE = 0.6
THRESHOLD_NEGATIVE = 0.4


def _classify_by_dict(text: str) -> str | None:
    """先查投资情感词典，命中则强分类；未命中返回 None。"""
    for kw in SENTIMENT_BULLISH:
        if kw in text:
            return "positive"
    for kw in SENTIMENT_BEARISH:
        if kw in text:
            return "negative"
    return None


def _snow_label(text: str) -> tuple[float, str]:
    """SnowNLP 兜底：返回 (score, label)"""
    try:
        score = float(SnowNLP(text).sentiments)
    except Exception:
        score = 0.5
    if score > THRESHOLD_POSITIVE:
        return score, "positive"
    if score < THRESHOLD_NEGATIVE:
        return score, "negative"
    return score, "neutral"


def _weight(like_count: int) -> float:
    """根据点赞数计算评论权重：1 + ln(like + 1)"""
    return 1.0 + math.log1p(max(like_count or 0, 0))


def analyze_sentiment_v2(comments: list[dict[str, Any]]) -> dict[str, Any]:
    """输入评论列表，输出三类情感占比。

    Args:
        comments: 评论列表，每条评论至少包含 content 字段；可包含 like_count/pub_time。
            兼容 dict 和 SQLAlchemy 对象（有 .content 属性即可）。

    Returns:
        {
            "positive_ratio": float,   # 0-1
            "neutral_ratio": float,
            "negative_ratio": float,
            "positive_count": int,
            "neutral_count": int,
            "negative_count": int,
            "total_samples": int,
            "dict_hit_rate": float,    # 词典命中占总样本的比例
            "details": list[dict],     # 每条评论的细粒度结果
        }
    """
    positive_weight = 0.0
    neutral_weight = 0.0
    negative_weight = 0.0
    positive_count = 0
    neutral_count = 0
    negative_count = 0
    dict_hit = 0
    details: list[dict[str, Any]] = []

    for c in comments:
        # 兼容 dict / ORM 对象
        content = c["content"] if isinstance(c, dict) else getattr(c, "content", "") or ""
        like_count = (
            c.get("like_count", 0)
            if isinstance(c, dict)
            else getattr(c, "like_count", 0) or 0
        )
        if isinstance(like_count, str):
            try:
                like_count = int(like_count)
            except ValueError:
                like_count = 0

        text = (content or "").strip()

        # 跳过纯空评论：算 neutral
        if not text:
            weight = _weight(like_count)
            neutral_weight += weight
            neutral_count += 1
            details.append({"label": "neutral", "method": "empty", "weight": round(weight, 2)})
            continue

        # 1) 词典强分类
        label = _classify_by_dict(text)
        method = "dict" if label else "snownlp"
        if label:
            dict_hit += 1
            score = 1.0 if label == "positive" else (0.0 if label == "negative" else 0.5)
        else:
            score, label = _snow_label(text)

        weight = _weight(like_count)
        if label == "positive":
            positive_weight += weight
            positive_count += 1
        elif label == "negative":
            negative_weight += weight
            negative_count += 1
        else:
            neutral_weight += weight
            neutral_count += 1

        details.append({
            "label": label,
            "method": method,
            "score": round(score, 3),
            "weight": round(weight, 2),
        })

    total_weight = positive_weight + neutral_weight + negative_weight
    total_samples = len(comments)

    return {
        "positive_ratio": round(positive_weight / max(total_weight, 1.0), 4),
        "neutral_ratio": round(neutral_weight / max(total_weight, 1.0), 4),
        "negative_ratio": round(negative_weight / max(total_weight, 1.0), 4),
        "positive_count": positive_count,
        "neutral_count": neutral_count,
        "negative_count": negative_count,
        "total_samples": total_samples,
        "dict_hit_rate": round(dict_hit / max(total_samples, 1), 4),
        "analyzed_at": datetime.now().isoformat(),
        "details": details,
    }
