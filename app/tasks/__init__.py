from celery import Celery

from app.config import settings

celery_app = Celery(
    "bilibili_sentiment",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.crawl",
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
    result_expires=3600,
    task_ignore_result=False,
    worker_prefetch_multiplier=1,
)

# v2: 暂不启用自动定时调度，专注基础功能
# 保留 Celery worker 启动方式以便手动 .delay() 触发任务
# 如需恢复 beat 调度，按以下模板加回：
# celery_app.conf.beat_schedule = {
#     "auto-crawl-active-keywords": {
#         "task": "app.tasks.crawl.auto_crawl_keywords",
#         "schedule": 300.0,
#     },
#     "auto-run-analysis": {
#         "task": "app.tasks.analysis.run_full_analysis",
#         "schedule": 1800.0,
#     },
#     "auto-crawl-hot-search": {
#         "task": "app.tasks.crawl.crawl_hot_search",
#         "schedule": 3600.0,
#     },
# }

# v2: 不再注册 governance 任务
import app.tasks.crawl  # noqa: F401,E402
import app.tasks.analysis  # noqa: F401,E402
