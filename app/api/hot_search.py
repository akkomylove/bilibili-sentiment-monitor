from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.hot_search import HotSearch
from app.tasks.crawl import crawl_hot_search

router = APIRouter(prefix="/hot-search", tags=["热点话题"])


@router.get("/list", summary="获取热点话题列表")
def get_hot_search_list(db: Session = Depends(get_db)):
    items = db.query(HotSearch).order_by(HotSearch.rank.asc()).all()
    return {
        "status": "ok",
        "total": len(items),
        "items": [
            {
                "id": item.id,
                "keyword": item.keyword,
                "rank": item.rank,
                "heat_score": item.heat_score,
                "sentiment_positive": item.sentiment_positive,
                "sentiment_neutral": item.sentiment_neutral,
                "sentiment_negative": item.sentiment_negative,
                "sentiment_summary": item.sentiment_summary,
                "video_count": item.video_count,
                "comment_count": item.comment_count,
                "crawled_at": str(item.crawled_at) if item.crawled_at else None,
            }
            for item in items
        ],
    }


@router.post("/crawl", summary="触发热点话题采集")
def trigger_hot_search_crawl():
    task = crawl_hot_search.delay(max_items=10)
    return {"status": "dispatched", "task_id": task.id}
