from sqlalchemy import DECIMAL, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Danmaku(Base):
    __tablename__ = "danmakus"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_bvid: Mapped[str] = mapped_column(String(20), ForeignKey("videos.bvid"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(String(500), nullable=False)
    timeline: Mapped[float] = mapped_column(DECIMAL(10, 3), nullable=False)
    send_time: Mapped[str | None] = mapped_column(DateTime)
    created_at: Mapped[str] = mapped_column(
        DateTime, server_default=func.now()
    )
