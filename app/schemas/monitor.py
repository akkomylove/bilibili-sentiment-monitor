from datetime import datetime

from pydantic import BaseModel, Field


class MonitorKeywordCreate(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=200)
    partition_filter: str | None = None
    sort_order: str = Field(default="totalrank", pattern=r"^(totalrank|click|pubdate)$")
    crawl_interval: int = Field(default=60, ge=10)
    is_active: bool = True


class MonitorKeywordUpdate(BaseModel):
    keyword: str | None = Field(None, min_length=1, max_length=200)
    partition_filter: str | None = None
    sort_order: str | None = Field(None, pattern=r"^(totalrank|click|pubdate)$")
    crawl_interval: int | None = Field(None, ge=10)
    is_active: bool | None = None


class MonitorKeywordResponse(BaseModel):
    id: int
    keyword: str
    partition_filter: str | None
    sort_order: str
    crawl_interval: int
    is_active: bool
    last_crawled_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MonitorStatusResponse(BaseModel):
    keywords: list[MonitorKeywordResponse]
    summary: dict
