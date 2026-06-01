from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.comment import Comment
from app.schemas.comment import CommentListResponse, CommentResponse

router = APIRouter(prefix="/comments", tags=["评论数据"])


@router.get(
    "/",
    response_model=CommentListResponse,
    summary="获取评论列表",
)
def list_comments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    video_bvid: str | None = Query(None, description="按视频bvid筛选"),
    db: Session = Depends(get_db),
):
    query = db.query(Comment)
    if video_bvid:
        query = query.filter(Comment.video_bvid == video_bvid)

    total = query.count()
    items = (
        query.order_by(Comment.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    total_pages = (total + page_size - 1) // page_size
    return CommentListResponse(
        items=[CommentResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{rpid}",
    response_model=CommentResponse,
    summary="获取单条评论详情",
)
def get_comment(
    rpid: int,
    db: Session = Depends(get_db),
):
    comment = db.query(Comment).filter(Comment.rpid == rpid).first()
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")
    return CommentResponse.model_validate(comment)
