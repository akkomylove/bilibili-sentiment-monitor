from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.web.routes import router as web_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="B 站 AI 投资领域舆情聚合工具",
    description="v2 简化为单页每日简报：半导体 / 光通信 / 光芯片 三个板块的舆情、情绪、热词与板块聚焦。",
    version="2.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/web/static"), name="static")

app.include_router(web_router)
app.include_router(api_router)


@app.get("/", tags=["系统"])
def root():
    return RedirectResponse(url="/daily-brief")
