from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class HotSearch(Base):
    __tablename__ = "hot_searches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword: Mapped[str] = mapped_column(String(200), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    heat_score: Mapped[int] = mapped_column(Integer, default=0)
    sentiment_positive: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment_neutral: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment_negative: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment_summary: Mapped[str | None] = mapped_column(Text)
    video_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    crawled_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
