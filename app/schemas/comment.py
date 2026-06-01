from datetime import datetime

from pydantic import BaseModel


class CommentResponse(BaseModel):
    id: int
    rpid: int
    video_bvid: str
    user_mid: str
    raw_content: str
    content: str
    like_count: int
    reply_count: int
    has_image: bool
    image_urls: list[str] | None
    pub_time: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CommentListResponse(BaseModel):
    items: list[CommentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
