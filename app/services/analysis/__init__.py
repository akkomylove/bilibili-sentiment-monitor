# v2 简化为双轨：
# - 自动定时分析（Celery beat → tasks/analysis.py → analyze_sentiment/keywords/trend + 写 AnalysisResult 表）
# - 每日简报（api/daily-brief → daily_brief.py → analyze_sentiment_v2(comments) + TemplateSummarizer）
# 两路并存，签名不同：v1 接 db session，v2 接 comments 列表

from app.services.analysis.investment_dict import (
    SENTIMENT_BEARISH,
    SENTIMENT_BULLISH,
    SECTOR_TERMS,
    detect_sector,
)
from app.services.analysis.keywords import (
    extract_keywords,
    extract_keywords_from_texts,
    extract_keywords_v2,
)
from app.services.analysis.sentiment import analyze_sentiment
from app.services.analysis.sentiment_v2 import analyze_sentiment_v2
from app.services.analysis.trend import analyze_trend

# v2 删除：danmaku_density / image_ocr / network / topic_cluster / user_profile
# 这些分析维度在 v2 简化中下线，目录/文件均已清理

__all__ = [
    "SENTIMENT_BEARISH",
    "SENTIMENT_BULLISH",
    "SECTOR_TERMS",
    "detect_sector",
    "analyze_sentiment",      # v1: db session → 写 AnalysisResult 表（Celery 自动）
    "analyze_sentiment_v2",   # v2: comments list → 内存计算（每日简报）
    "analyze_trend",          # v1: db session
    "extract_keywords",       # v1: db session
    "extract_keywords_from_texts",  # v2: texts list
    "extract_keywords_v2",    # v2: texts list（增强版）
]
