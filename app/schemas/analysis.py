from datetime import datetime

from pydantic import BaseModel


class SentimentResponse(BaseModel):
    positive_ratio: float
    neutral_ratio: float
    negative_ratio: float
    total_samples: int
    trend_data: list[dict]
    analyzed_at: datetime


class KeywordsResponse(BaseModel):
    keywords: list[dict]
    total_terms: int
    analyzed_at: datetime


class TrendResponse(BaseModel):
    time_series: list[dict]
    peak_points: list[dict]
    analyzed_at: datetime
