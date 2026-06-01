from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.video import Video
from app.schemas.video import VideoListResponse, VideoResponse

router = APIRouter(prefix="/videos", tags=["视频数据"])


@router.get(
    "/",
    response_model=VideoListResponse,
    summary="获取视频列表",
)
def list_videos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None, description="按标题关键词筛选"),
    partition: str | None = Query(None, description="按分区筛选"),
    sort_by: str = Query("created_at", description="排序字段: created_at/view_count/comment_count"),
    sort_order: str = Query("desc", description="排序方向: asc/desc"),
    db: Session = Depends(get_db),
):
    query = db.query(Video)
    if keyword:
        query = query.filter(Video.title.contains(keyword))
    if partition:
        query = query.filter(Video.partition_tag == partition)

    order_col = getattr(Video, sort_by, Video.created_at)
    if sort_order == "desc":
        query = query.order_by(order_col.desc())
    else:
        query = query.order_by(order_col.asc())

    total = query.count()
    items = (
        query.offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    total_pages = (total + page_size - 1) // page_size
    return VideoListResponse(
        items=[VideoResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{bvid}/danmaku", summary="获取视频弹幕列表")
def get_video_danmaku(
    bvid: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    from app.models.danmaku import Danmaku

    query = db.query(Danmaku).filter(Danmaku.video_bvid == bvid)
    total = query.count()
    items = (
        query.order_by(Danmaku.timeline.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [
            {
                "id": item.id,
                "content": item.content,
                "timeline": float(item.timeline),
                "send_time": str(item.send_time) if item.send_time else None,
            }
            for item in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/{bvid}",
    response_model=VideoResponse,
    summary="获取视频详情",
)
def get_video(
    bvid: str,
    db: Session = Depends(get_db),
):
    video = db.query(Video).filter(Video.bvid == bvid).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    return VideoResponse.model_validate(video)


@router.post(
    "/{bvid}/trigger-comments",
    summary="手动触发深度评论采集",
)
def trigger_comments_crawl(bvid: str):
    from app.tasks.crawl import crawl_comments_deep
    task = crawl_comments_deep.delay(bvid, max_pages=20)
    return {"status": "queued", "bvid": bvid, "task_id": task.id}


@router.post(
    "/{bvid}/trigger-danmaku",
    summary="手动触发Protobuf弹幕采集",
)
def trigger_danmaku_crawl(bvid: str):
    from app.tasks.crawl import crawl_danmaku_proto
    task = crawl_danmaku_proto.delay(bvid)
    return {"status": "queued", "bvid": bvid, "task_id": task.id}


@router.post(
    "/{bvid}/trigger-analysis",
    summary="手动触发单视频全量分析",
)
def trigger_video_analysis(bvid: str):
    from app.tasks.analysis import run_full_analysis
    task = run_full_analysis.delay(bvid)
    return {"status": "queued", "bvid": bvid, "task_id": task.id}
