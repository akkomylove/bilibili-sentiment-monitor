from datetime import date as _date

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/web/templates")

router = APIRouter(tags=["页面"])


@router.get("/daily-brief", response_class=HTMLResponse)
async def daily_brief_page(request: Request):
    """v2 单页简报：取代旧的 dashboard/governance/report 页面"""
    return templates.TemplateResponse(
        request,
        "daily_brief.html",
        {"request": request, "today": _date.today().isoformat()},
    )


@router.get("/report", response_class=HTMLResponse)
async def report_page(request: Request):
    """v2.2 报告页：PPT 翻页式 HTML 报告（7 维度分析）"""
    return templates.TemplateResponse(
        request,
        "report.html",
        {"request": request, "today": _date.today().isoformat()},
    )


@router.get("/videos", response_class=HTMLResponse)
async def videos_page(request: Request):
    return templates.TemplateResponse(request, "videos.html", {"request": request})


@router.get("/videos/{bvid}", response_class=HTMLResponse)
async def video_detail(request: Request, bvid: str):
    return templates.TemplateResponse(request, "video_detail.html", {"request": request, "bvid": bvid})


@router.get("/monitor", response_class=HTMLResponse)
async def monitor_page(request: Request):
    return templates.TemplateResponse(request, "monitor.html", {"request": request})

# v2 删除：dashboard / governance / report / hot-search 页面路由
# 这些页面已被 daily_brief 单页取代，保留 URL 会 404 以避免误导
