"""Celery 分析任务（v2 简化版）

v2 决策：只保留 3 个核心分析任务（情感 / 关键词 / 趋势），
砍掉 4 个分析任务（用户画像 / 图片 OCR / 弹幕密度 / 话题聚类 / 互动网络）。
"""

from app.database import SessionLocal
from app.services.analysis.keywords import extract_keywords
from app.services.analysis.sentiment import analyze_sentiment
from app.services.analysis.trend import analyze_trend
from app.tasks import celery_app


@celery_app.task(bind=True)
def run_sentiment_analysis(self, video_bvid: str | None = None, keyword_id: int | None = None, keyword_ids: list[int] | None = None):
    db = SessionLocal()
    try:
        result = analyze_sentiment(db, video_bvid=video_bvid, keyword_id=keyword_id, keyword_ids=keyword_ids)
        return {"status": "completed", "video_bvid": video_bvid, "samples": result["total_samples"]}
    finally:
        db.close()


@celery_app.task(bind=True)
def run_keyword_extraction(self, video_bvid: str | None = None, keyword_id: int | None = None, keyword_ids: list[int] | None = None):
    db = SessionLocal()
    try:
        result = extract_keywords(db, video_bvid=video_bvid, keyword_id=keyword_id, keyword_ids=keyword_ids)
        return {"status": "completed", "keywords_count": len(result["keywords"])}
    finally:
        db.close()


@celery_app.task(bind=True)
def run_trend_analysis(self, keyword_id: int | None = None, keyword_ids: list[int] | None = None):
    db = SessionLocal()
    try:
        result = analyze_trend(db, keyword_id=keyword_id)
        return {"status": "completed", "data_points": len(result["time_series"])}
    finally:
        db.close()


@celery_app.task(bind=True)
def run_full_analysis(self, video_bvid: str | None = None, keyword_id: int | None = None, keyword_ids: list[int] | None = None):
    """v2: 只跑 3 个核心分析（情感 / 关键词 / 趋势）"""
    from celery import group

    tasks = [
        run_sentiment_analysis.s(video_bvid, keyword_id, keyword_ids),
        run_keyword_extraction.s(video_bvid, keyword_id, keyword_ids),
        run_trend_analysis.s(keyword_id, keyword_ids),
    ]

    job = group(tasks)
    result = job.apply_async()
    return {"status": "dispatched", "group_id": result.id, "dimensions_total": len(tasks)}
