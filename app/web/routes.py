from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/web/templates")

router = APIRouter(tags=["页面"])


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html", {"request": request})


@router.get("/videos", response_class=HTMLResponse)
async def videos_page(request: Request):
    return templates.TemplateResponse(request, "videos.html", {"request": request})


@router.get("/videos/{bvid}", response_class=HTMLResponse)
async def video_detail(request: Request, bvid: str):
    return templates.TemplateResponse(request, "video_detail.html", {"request": request, "bvid": bvid})


@router.get("/governance", response_class=HTMLResponse)
async def governance_page(request: Request):
    return templates.TemplateResponse(request, "governance.html", {"request": request})


@router.get("/report", response_class=HTMLResponse)
async def report_page(request: Request):
    return templates.TemplateResponse(request, "report.html", {"request": request})


@router.get("/monitor", response_class=HTMLResponse)
async def monitor_page(request: Request):
    return templates.TemplateResponse(request, "monitor.html", {"request": request})


@router.get("/hot-search", response_class=HTMLResponse)
async def hot_search_page(request: Request):
    return templates.TemplateResponse(request, "hot_search.html", {"request": request})
