from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rpid: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    video_bvid: Mapped[str] = mapped_column(String(20), ForeignKey("videos.bvid"), nullable=False, index=True)
    user_mid: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    reply_count: Mapped[int] = mapped_column(Integer, default=0)
    has_image: Mapped[bool] = mapped_column(Boolean, default=False)
    image_urls: Mapped[str | None] = mapped_column(JSON)
    pub_time: Mapped[str | None] = mapped_column(DateTime)
    created_at: Mapped[str] = mapped_column(
        DateTime, server_default=func.now()
    )
