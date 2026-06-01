from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.comment import Comment
from app.models.monitor import MonitorKeyword
from app.models.video import Video
from app.schemas.common import PaginatedResponse
from app.schemas.monitor import (
    MonitorKeywordCreate,
    MonitorKeywordResponse,
    MonitorKeywordUpdate,
    MonitorStatusResponse,
)

router = APIRouter(prefix="/monitor", tags=["监控配置"])


@router.get(
    "/keywords",
    response_model=PaginatedResponse[MonitorKeywordResponse],
    summary="获取监控关键词列表",
)
def list_keywords(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    total = db.query(MonitorKeyword).count()
    items = (
        db.query(MonitorKeyword)
        .order_by(MonitorKeyword.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    total_pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        items=[MonitorKeywordResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "/keywords",
    response_model=MonitorKeywordResponse,
    status_code=201,
    summary="新增监控关键词",
)
def create_keyword(
    body: MonitorKeywordCreate,
    db: Session = Depends(get_db),
):
    keyword = MonitorKeyword(**body.model_dump())
    db.add(keyword)
    db.commit()
    db.refresh(keyword)
    return MonitorKeywordResponse.model_validate(keyword)


@router.put(
    "/keywords/{keyword_id}",
    response_model=MonitorKeywordResponse,
    summary="修改监控配置",
)
def update_keyword(
    keyword_id: int,
    body: MonitorKeywordUpdate,
    db: Session = Depends(get_db),
):
    keyword = db.query(MonitorKeyword).filter(MonitorKeyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(keyword, key, value)
    db.commit()
    db.refresh(keyword)
    return MonitorKeywordResponse.model_validate(keyword)


@router.delete(
    "/keywords/{keyword_id}",
    status_code=204,
    summary="删除监控关键词",
)
def delete_keyword(
    keyword_id: int,
    db: Session = Depends(get_db),
):
    keyword = db.query(MonitorKeyword).filter(MonitorKeyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")
    # 先解除视频的外键关联，避免外键约束错误
    from app.models.video import Video
    db.query(Video).filter(Video.keyword_id == keyword_id).update({"keyword_id": None})
    db.delete(keyword)
    db.commit()


@router.post(
    "/keywords/{keyword_id}/trigger",
    response_model=dict,
    summary="手动触发爬取",
)
def trigger_crawl(
    keyword_id: int,
    db: Session = Depends(get_db),
):
    keyword = db.query(MonitorKeyword).filter(MonitorKeyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")
    from app.tasks.crawl import crawl_by_keyword
    task = crawl_by_keyword.delay(keyword_id, keyword.keyword, sort_order=keyword.sort_order)
    return {
        "status": "queued",
        "keyword_id": keyword_id,
        "keyword": keyword.keyword,
        "task_id": task.id,
    }


@router.post(
    "/keywords/{keyword_id}/trigger-analysis",
    response_model=dict,
    summary="手动触发关键词分析",
)
def trigger_analysis(
    keyword_id: int,
    db: Session = Depends(get_db),
):
    keyword = db.query(MonitorKeyword).filter(MonitorKeyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")
    from app.tasks.analysis import run_full_analysis
    task = run_full_analysis.delay(keyword_id=keyword_id)
    return {
        "status": "queued",
        "keyword_id": keyword_id,
        "keyword": keyword.keyword,
        "task_id": task.id,
    }


@router.get(
    "/status",
    response_model=MonitorStatusResponse,
    summary="获取监控状态汇总",
)
def get_monitor_status(db: Session = Depends(get_db)):
    keywords = db.query(MonitorKeyword).order_by(MonitorKeyword.created_at.desc()).all()

    keyword_responses = []
    total_videos_all = 0
    total_comments_all = 0
    active_count = 0

    for kw in keywords:
        video_count = db.query(Video).filter(Video.keyword_id == kw.id).count()
        comment_count = (
            db.query(Comment)
            .join(Video, Comment.video_bvid == Video.bvid)
            .filter(Video.keyword_id == kw.id)
            .count()
        )
        total_videos_all += video_count
        total_comments_all += comment_count
        if kw.is_active:
            active_count += 1

        keyword_responses.append({
            "id": kw.id,
            "keyword": kw.keyword,
            "partition_filter": kw.partition_filter,
            "sort_order": kw.sort_order or "totalrank",
            "crawl_interval": kw.crawl_interval,
            "is_active": kw.is_active,
            "last_crawled_at": kw.last_crawled_at,
            "created_at": kw.created_at,
            "updated_at": kw.updated_at,
            "total_videos": video_count,
            "total_comments": comment_count,
        })

    return MonitorStatusResponse(
        keywords=keyword_responses,
        summary={
            "active_count": active_count,
            "total_keywords": len(keywords),
            "total_videos": total_videos_all,
            "total_comments": total_comments_all,
        },
    )


@router.get(
    "/activities",
    response_model=dict,
    summary="获取最近采集活动",
)
def get_monitor_activities(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    videos = (
        db.query(Video)
        .order_by(Video.created_at.desc())
        .limit(limit)
        .all()
    )

    activities = []
    for v in videos:
        keyword = db.query(MonitorKeyword).filter(MonitorKeyword.id == v.keyword_id).first()
        comment_count = (
            db.query(Comment)
            .filter(Comment.video_bvid == v.bvid)
            .count()
        )
        activities.append({
            "time": v.created_at.isoformat() if v.created_at else None,
            "keyword": keyword.keyword if keyword else "未知",
            "action": "crawl",
            "bvid": v.bvid,
            "title": v.title,
            "videos_added": 1,
            "comments_added": comment_count,
        })

    return {"activities": activities}
