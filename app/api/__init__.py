from fastapi import APIRouter

from app.api.analysis import router as analysis_router
from app.api.comments import router as comments_router
from app.api.monitor import router as monitor_router
from app.api.videos import router as videos_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(monitor_router)
api_router.include_router(videos_router)
api_router.include_router(comments_router)
api_router.include_router(analysis_router)

# v2: governance/export/hot_search 已删除
# from app.api.governance import router as governance_router
# from app.api.export import router as export_router
# from app.api.hot_search import router as hot_search_router
