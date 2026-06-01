from celery import Celery

from app.config import settings

celery_app = Celery(
    "bilibili_sentiment",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.crawl",
        "app.tasks.governance",
        "app.tasks.analysis",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    # 内存优化：任务结果只保留1小时，减少Redis内存占用
    result_expires=3600,
    # 内存优化：不保存任务结果到backend（只跟踪状态）
    task_ignore_result=False,
    # 内存优化：worker最多同时处理1个任务（已用solo pool）
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    "auto-crawl-active-keywords": {
        "task": "app.tasks.crawl.auto_crawl_keywords",
        "schedule": 300.0,
    },
    "auto-run-analysis": {
        "task": "app.tasks.analysis.run_full_analysis",
        "schedule": 1800.0,
    },
    "auto-crawl-hot-search": {
        "task": "app.tasks.crawl.crawl_hot_search",
        "schedule": 3600.0,
    },
}
