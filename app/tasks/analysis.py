from app.database import SessionLocal
from app.services.analysis.danmaku_density import analyze_danmaku_density
from app.services.analysis.image_ocr import analyze_image_comments
from app.services.analysis.keywords import extract_keywords
from app.services.analysis.network import analyze_interaction_network
from app.services.analysis.sentiment import analyze_sentiment
from app.services.analysis.topic_cluster import analyze_topic_cluster
from app.services.analysis.trend import analyze_trend
from app.services.analysis.user_profile import analyze_user_profile
from app.tasks import celery_app


@celery_app.task(bind=True, name="run_sentiment_analysis")
def run_sentiment_analysis(self, video_bvid: str | None = None, keyword_id: int | None = None, keyword_ids: list[int] | None = None):
    db = SessionLocal()
    try:
        result = analyze_sentiment(db, video_bvid=video_bvid, keyword_id=keyword_id, keyword_ids=keyword_ids)
        return {"status": "completed", "video_bvid": video_bvid, "samples": result["total_samples"]}
    finally:
        db.close()


@celery_app.task(bind=True, name="run_keyword_extraction")
def run_keyword_extraction(self, video_bvid: str | None = None, keyword_id: int | None = None, keyword_ids: list[int] | None = None):
    db = SessionLocal()
    try:
        result = extract_keywords(db, video_bvid=video_bvid, keyword_id=keyword_id, keyword_ids=keyword_ids)
        return {"status": "completed", "keywords_count": len(result["keywords"])}
    finally:
        db.close()


@celery_app.task(bind=True, name="run_trend_analysis")
def run_trend_analysis(self, keyword_id: int | None = None, keyword_ids: list[int] | None = None):
    db = SessionLocal()
    try:
        result = analyze_trend(db, keyword_id=keyword_id)
        return {"status": "completed", "data_points": len(result["time_series"])}
    finally:
        db.close()


@celery_app.task(bind=True, name="run_user_profile_analysis")
def run_user_profile_analysis(self, video_bvid: str | None = None):
    db = SessionLocal()
    try:
        result = analyze_user_profile(db, video_bvid)
        return {"status": "completed", "total_users": result["total_users"]}
    finally:
        db.close()


@celery_app.task(bind=True, name="run_image_ocr_analysis")
def run_image_ocr_analysis(self, video_bvid: str | None = None):
    db = SessionLocal()
    try:
        result = analyze_image_comments(db, video_bvid)
        return {"status": "completed", "image_comments": result["image_comment_count"], "ocr_success": result["ocr_success_count"]}
    finally:
        db.close()


@celery_app.task(bind=True, name="run_danmaku_density_analysis")
def run_danmaku_density_analysis(self, video_bvid: str | None = None):
    db = SessionLocal()
    try:
        result = analyze_danmaku_density(db, video_bvid)
        return {"status": "completed", "total_danmaku": result["total_danmaku"], "peaks": result["peak_count"]}
    finally:
        db.close()


@celery_app.task(bind=True, name="run_topic_cluster_analysis")
def run_topic_cluster_analysis(self, video_bvid: str | None = None, keyword_id: int | None = None, keyword_ids: list[int] | None = None):
    db = SessionLocal()
    try:
        result = analyze_topic_cluster(db, video_bvid=video_bvid, keyword_id=keyword_id, keyword_ids=keyword_ids)
        return {"status": "completed", "n_clusters": result["n_clusters"], "total_comments": result["total_comments"]}
    finally:
        db.close()


@celery_app.task(bind=True, name="run_network_analysis")
def run_network_analysis(self, video_bvid: str | None = None):
    db = SessionLocal()
    try:
        result = analyze_interaction_network(db, video_bvid)
        return {"status": "completed", "total_users": result["total_users"], "interactions": result["total_interactions"]}
    finally:
        db.close()


@celery_app.task(bind=True, name="run_full_analysis")
def run_full_analysis(self, video_bvid: str | None = None, keyword_id: int | None = None, keyword_ids: list[int] | None = None):
    from celery import group

    tasks = [
        run_sentiment_analysis.s(video_bvid, keyword_id, keyword_ids),
        run_keyword_extraction.s(video_bvid, keyword_id, keyword_ids),
        run_trend_analysis.s(keyword_id, keyword_ids),
        run_user_profile_analysis.s(video_bvid),
        run_image_ocr_analysis.s(video_bvid),
        run_danmaku_density_analysis.s(video_bvid),
        run_topic_cluster_analysis.s(video_bvid, keyword_id, keyword_ids),
        run_network_analysis.s(video_bvid),
    ]

    job = group(tasks)
    result = job.apply_async()
    return {"status": "dispatched", "group_id": result.id, "dimensions_total": len(tasks)}
