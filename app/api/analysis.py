from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.analysis import AnalysisResult

router = APIRouter(prefix="/analysis", tags=["分析结果"])


def _get_latest_analysis(
    db: Session,
    analysis_type: str,
    ref_type: str | None = None,
    ref_id: str | None = None,
):
    """查询最新的分析结果，支持 keyword_ids 多选"""
    query = db.query(AnalysisResult).filter(AnalysisResult.analysis_type == analysis_type)
    if ref_type and ref_id:
        query = query.filter(
            AnalysisResult.ref_type == ref_type,
            AnalysisResult.ref_id == ref_id,
        )
    elif ref_type:
        query = query.filter(AnalysisResult.ref_type == ref_type)
    return query.order_by(AnalysisResult.analyzed_at.desc()).first()


@router.get("/sentiment", summary="情感分析结果")
def get_sentiment(
    video_bvid: str | None = Query(None),
    keyword_id: int | None = Query(None),
    keyword_ids: str | None = Query(None),
    db: Session = Depends(get_db),
):
    if video_bvid:
        result = _get_latest_analysis(db, "sentiment", ref_type="video", ref_id=video_bvid)
    elif keyword_ids:
        ids = [s.strip() for s in keyword_ids.split(",") if s.strip()]
        result = (
            db.query(AnalysisResult)
            .filter(
                AnalysisResult.analysis_type == "sentiment",
                AnalysisResult.ref_type == "keyword",
                AnalysisResult.ref_id.in_(ids),
            )
            .order_by(AnalysisResult.analyzed_at.desc())
            .first()
        )
    elif keyword_id:
        result = _get_latest_analysis(db, "sentiment", ref_type="keyword", ref_id=str(keyword_id))
    else:
        result = _get_latest_analysis(db, "sentiment", ref_type="global")
    if not result:
        return {"status": "no_data", "message": "暂无分析结果"}
    return result.result_data


@router.get("/keywords", summary="关键词提取结果")
def get_keywords(
    video_bvid: str | None = Query(None),
    keyword_id: int | None = Query(None),
    keyword_ids: str | None = Query(None),
    db: Session = Depends(get_db),
):
    if video_bvid:
        result = _get_latest_analysis(db, "keywords", ref_type="video", ref_id=video_bvid)
    elif keyword_ids:
        ids = [s.strip() for s in keyword_ids.split(",") if s.strip()]
        result = (
            db.query(AnalysisResult)
            .filter(
                AnalysisResult.analysis_type == "keywords",
                AnalysisResult.ref_type == "keyword",
                AnalysisResult.ref_id.in_(ids),
            )
            .order_by(AnalysisResult.analyzed_at.desc())
            .first()
        )
    elif keyword_id:
        result = _get_latest_analysis(db, "keywords", ref_type="keyword", ref_id=str(keyword_id))
    else:
        result = _get_latest_analysis(db, "keywords", ref_type="global")
    if not result:
        return {"status": "no_data", "message": "暂无分析结果"}
    return result.result_data


@router.get("/trend", summary="趋势分析数据")
def get_trend(
    keyword_id: int | None = Query(None),
    keyword_ids: str | None = Query(None),
    db: Session = Depends(get_db),
):
    if keyword_ids:
        ids = [s.strip() for s in keyword_ids.split(",") if s.strip()]
        result = (
            db.query(AnalysisResult)
            .filter(
                AnalysisResult.analysis_type == "trend",
                AnalysisResult.ref_type == "keyword",
                AnalysisResult.ref_id.in_(ids),
            )
            .order_by(AnalysisResult.analyzed_at.desc())
            .first()
        )
    elif keyword_id:
        result = _get_latest_analysis(db, "trend", ref_type="keyword", ref_id=str(keyword_id))
    else:
        result = _get_latest_analysis(db, "trend", ref_type="global")
    if not result:
        return {"status": "no_data", "message": "暂无分析结果"}
    return result.result_data


@router.get("/user-profile", summary="用户画像数据")
@router.get("/user_profile", summary="用户画像数据")
def get_user_profile(
    video_bvid: str | None = Query(None),
    db: Session = Depends(get_db),
):
    result = _get_latest_analysis(db, "user_profile", ref_type="video", ref_id=video_bvid)
    if not result:
        return {"status": "no_data", "message": "暂无分析结果"}
    return result.result_data


@router.get("/image-ocr", summary="图片评论分析")
@router.get("/image_ocr", summary="图片评论分析")
def get_image_ocr(
    video_bvid: str | None = Query(None),
    db: Session = Depends(get_db),
):
    result = _get_latest_analysis(db, "image_ocr", ref_type="video", ref_id=video_bvid)
    if not result:
        return {"status": "no_data", "message": "暂无分析结果"}
    return result.result_data


@router.get("/danmaku-density", summary="弹幕密度分析")
@router.get("/danmaku_density", summary="弹幕密度分析")
def get_danmaku_density(
    video_bvid: str | None = Query(None),
    db: Session = Depends(get_db),
):
    result = _get_latest_analysis(db, "danmaku_density", ref_type="video", ref_id=video_bvid)
    if not result:
        return {"status": "no_data", "message": "暂无分析结果"}
    return result.result_data


@router.get("/topic-cluster", summary="话题聚类结果")
@router.get("/topic_cluster", summary="话题聚类结果")
def get_topic_cluster(
    keyword_id: int | None = Query(None),
    keyword_ids: str | None = Query(None),
    db: Session = Depends(get_db),
):
    if keyword_ids:
        ids = [s.strip() for s in keyword_ids.split(",") if s.strip()]
        result = (
            db.query(AnalysisResult)
            .filter(
                AnalysisResult.analysis_type == "topic_cluster",
                AnalysisResult.ref_type == "keyword",
                AnalysisResult.ref_id.in_(ids),
            )
            .order_by(AnalysisResult.analyzed_at.desc())
            .first()
        )
    elif keyword_id:
        result = _get_latest_analysis(db, "topic_cluster", ref_type="keyword", ref_id=str(keyword_id))
    else:
        result = _get_latest_analysis(db, "topic_cluster", ref_type="global")
    if not result:
        return {"status": "no_data", "message": "暂无分析结果"}
    return result.result_data


@router.get("/network", summary="评论互动网络数据")
def get_network(
    video_bvid: str | None = Query(None),
    db: Session = Depends(get_db),
):
    result = _get_latest_analysis(db, "network", ref_type="video", ref_id=video_bvid)
    if not result:
        return {"status": "no_data", "message": "暂无分析结果"}
    return result.result_data
