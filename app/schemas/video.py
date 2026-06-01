from datetime import datetime

from pydantic import BaseModel


class VideoResponse(BaseModel):
    id: int
    bvid: str
    title: str
    description: str | None
    play_count: int
    danmaku_count: int
    comment_count: int
    pub_time: datetime | None
    partition_tag: str | None
    keyword_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class VideoListResponse(BaseModel):
    items: list[VideoResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
