# v2 简化：仅保留通用分页/错误/Monitor/Video/Comment 的 schema
# analysis 专用 schema 已在 endpoint 内联 dict 定义，不再单独 Pydantic 化

from app.schemas.comment import CommentListResponse, CommentResponse
from app.schemas.common import ErrorResponse, PaginatedResponse
from app.schemas.monitor import (
    MonitorKeywordCreate,
    MonitorKeywordResponse,
    MonitorKeywordUpdate,
)
from app.schemas.video import VideoListResponse, VideoResponse

__all__ = [
    "PaginatedResponse",
    "ErrorResponse",
    "MonitorKeywordCreate",
    "MonitorKeywordUpdate",
    "MonitorKeywordResponse",
    "VideoResponse",
    "VideoListResponse",
    "CommentResponse",
    "CommentListResponse",
]
