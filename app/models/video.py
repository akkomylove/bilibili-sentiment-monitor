from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bvid: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    play_count: Mapped[int] = mapped_column(BigInteger, default=0)
    danmaku_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    pub_time: Mapped[str | None] = mapped_column(DateTime)
    partition_tag: Mapped[str | None] = mapped_column(String(100))
    keyword_id: Mapped[int | None] = mapped_column(ForeignKey("monitor_keywords.id", ondelete="SET NULL"))
    created_at: Mapped[str] = mapped_column(
        DateTime, server_default=func.now()
    )
