# B站舆情监控与分析平台 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从零搭建 B站舆情监控与分析平台，覆盖数据采集→治理→分析→API→可视化的全生命周期。

**Architecture:** FastAPI 做 Web 层 + Celery/Redis 做异步任务调度 + MySQL 做业务存储 + SQLAlchemy ORM + Jinja2/ECharts/Bootstrap 做前端仪表盘。采用分层架构：API路由层 → 业务服务层 → 数据模型层，通过依赖注入解耦。

**Tech Stack:** Python 3.10+, FastAPI, Celery, Redis, MySQL 8.0, SQLAlchemy 2.0, Pydantic v2, Jinja2, ECharts, Bootstrap 5

---

## 文件规划

| 文件路径 | 职责 |
|----------|------|
| `app/__init__.py` | 包标识，导出 create_app 工厂函数 |
| `app/main.py` | FastAPI 应用入口，注册路由、中间件、生命周期事件 |
| `app/config.py` | 配置管理，从 .env 读取，Pydantic Settings |
| `app/database.py` | SQLAlchemy 引擎 + Session 工厂 |
| `app/dependencies.py` | FastAPI 依赖注入（get_db 等） |
| `app/models/__init__.py` | 导入所有模型，供 Alembic 发现 |
| `app/models/base.py` | SQLAlchemy DeclarativeBase |
| `app/models/video.py` | Video 模型 |
| `app/models/comment.py` | Comment 模型 |
| `app/models/danmaku.py` | Danmaku 模型 |
| `app/models/monitor.py` | MonitorKeyword 模型 |
| `app/models/governance.py` | GovernanceRule / GovernanceLog / DataLineage 模型 |
| `app/models/analysis.py` | AnalysisResult 模型 |
| `app/schemas/__init__.py` | Pydantic Schema 聚合导出 |
| `app/schemas/common.py` | 通用 Schema（分页、错误响应） |
| `app/schemas/monitor.py` | 监控关键词 Schema |
| `app/schemas/video.py` | 视频 Schema |
| `app/schemas/comment.py` | 评论 Schema |
| `app/schemas/governance.py` | 治理 Schema |
| `app/schemas/analysis.py` | 分析 Schema |
| `app/api/__init__.py` | API 路由聚合，创建 APIRouter |
| `app/api/monitor.py` | 监控配置 CRUD 接口 |
| `app/api/videos.py` | 视频查询接口 |
| `app/api/comments.py` | 评论查询接口 |
| `app/api/analysis.py` | 分析结果查询接口 |
| `app/api/governance.py` | 治理接口 |
| `app/api/export.py` | 导出接口 |
| `app/services/crawler/__init__.py` | 爬虫服务包 |
| `app/services/crawler/bilibili.py` | B站 API 调用封装 |
| `app/services/governance/__init__.py` | 治理服务包 |
| `app/services/governance/engine.py` | 治理规则引擎 |
| `app/services/analysis/__init__.py` | 分析服务包 |
| `app/services/analysis/sentiment.py` | 情感分析 |
| `app/services/analysis/keywords.py` | 关键词提取 |
| `app/services/analysis/trend.py` | 趋势分析 |
| `app/services/analysis/user_profile.py` | 用户画像 |
| `app/services/analysis/image_ocr.py` | 图片OCR |
| `app/services/analysis/danmaku_density.py` | 弹幕密度 |
| `app/services/analysis/topic_cluster.py` | 话题聚类 |
| `app/services/analysis/network.py` | 互动网络 |
| `app/services/report/__init__.py` | 报告服务包 |
| `app/services/report/generator.py` | 报告生成 |
| `app/tasks/__init__.py` | Celery 应用实例 |
| `app/tasks/crawl.py` | 爬虫定时任务 |
| `app/tasks/governance.py` | 治理定时任务 |
| `app/tasks/analysis.py` | 分析定时任务 |
| `app/web/__init__.py` | Web 页面路由 |
| `app/web/routes.py` | 页面路由定义 |
| `app/web/templates/base.html` | 基础模板 |
| `app/web/templates/dashboard.html` | 仪表盘 |
| `app/web/templates/videos.html` | 视频列表 |
| `app/web/templates/video_detail.html` | 视频详情 |
| `app/web/templates/governance.html` | 治理面板 |
| `app/web/templates/report.html` | 报告导出页 |
| `app/web/static/css/style.css` | 自定义样式 |
| `app/web/static/js/dashboard.js` | 仪表盘 JS |
| `.env.example` | 环境变量模板 |
| `.env` | 实际环境变量（不提交） |
| `.gitignore` | Git 忽略规则 |
| `requirements.txt` | 依赖列表 |
| `scripts/init_db.py` | 数据库建表脚本 |
| `scripts/seed_data.py` | 演示数据填充脚本 |
| `docker-compose.yml` | MySQL + Redis 本地环境 |

---

## Phase 1: 项目骨架搭建（本计划重点）

### Task 1.1: 项目初始化

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `.env`
- Create: `requirements.txt`
- Create: `docker-compose.yml`

- [ ] **Step 1: 创建 .gitignore**

在 `/workspace` 下创建文件 `.gitignore`：

```
__pycache__/
*.pyc
*.pyo
.env
.venv/
venv/
*.egg-info/
dist/
build/
.pytest_cache/
*.log
instance/
.DS_Store
```

- [ ] **Step 2: 创建 .env.example**

```ini
# MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=root123
MYSQL_DATABASE=bilibili_sentiment

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# App
APP_DEBUG=true
APP_SECRET_KEY=change-me-in-production
APP_HOST=0.0.0.0
APP_PORT=8000
```

- [ ] **Step 3: 创建 .env（从 .env.example 复制）**

```bash
cp .env.example .env
```

- [ ] **Step 4: 创建 requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy==2.0.35
pymysql==1.1.1
cryptography==43.0.1
pydantic==2.9.2
pydantic-settings==2.5.2
celery[redis]==5.4.0
redis==5.1.1
jinja2==3.1.4
python-multipart==0.0.12
httpx==0.27.2
jieba==0.42.1
snownlp==0.12.3
wordcloud==1.9.3
matplotlib==3.9.2
scikit-learn==1.5.2
simhash==2.1.2
```

- [ ] **Step 5: 创建 docker-compose.yml（本地 MySQL + Redis）**

```yaml
version: "3.8"

services:
  mysql:
    image: mysql:8.0
    container_name: bilibili_mysql
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: root123
      MYSQL_DATABASE: bilibili_sentiment
      MYSQL_CHARSET: utf8mb4
      MYSQL_COLLATION: utf8mb4_unicode_ci
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    command: --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci

  redis:
    image: redis:7-alpine
    container_name: bilibili_redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  mysql_data:
  redis_data:
```

- [ ] **Step 6: 启动 Docker 服务并验证**

```bash
docker compose up -d
docker compose ps
```

期望输出：mysql 和 redis 两个容器均为 `Up` 状态。

- [ ] **Step 7: 创建虚拟环境并安装依赖**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 8: Commit**

```bash
git add .gitignore .env.example requirements.txt docker-compose.yml
git commit -m "chore: init project with dependencies and docker services"
```

---

### Task 1.2: 配置管理模块

**Files:**
- Create: `app/__init__.py`
- Create: `app/config.py`

- [ ] **Step 1: 创建 app/__init__.py**

```python
"""
B站舆情监控与分析平台
"""
```

- [ ] **Step 2: 创建 app/config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "root123"
    mysql_database: str = "bilibili_sentiment"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    app_debug: bool = True
    app_secret_key: str = "change-me-in-production"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            f"?charset=utf8mb4"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def celery_broker_url(self) -> str:
        return self.redis_url

    @property
    def celery_result_backend(self) -> str:
        return self.redis_url

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
```

- [ ] **Step 3: 验证配置加载**

```bash
cd /workspace && source .venv/bin/activate && python -c "from app.config import settings; print(settings.mysql_url); print(settings.redis_url)"
```

期望：打印出 MySQL 和 Redis 的连接 URL。

- [ ] **Step 4: Commit**

```bash
git add app/__init__.py app/config.py
git commit -m "feat: add config module with pydantic settings"
```

---

### Task 1.3: 数据库连接 + Base 模型

**Files:**
- Create: `app/database.py`
- Create: `app/models/__init__.py`
- Create: `app/models/base.py`

- [ ] **Step 1: 创建 app/database.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings

engine = create_engine(
    settings.mysql_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.app_debug,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: 创建 app/models/base.py**

```python
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
```

- [ ] **Step 3: 创建 app/models/__init__.py**

```python
from app.models.base import Base, TimestampMixin
from app.models.monitor import MonitorKeyword
from app.models.video import Video
from app.models.comment import Comment
from app.models.danmaku import Danmaku
from app.models.governance import GovernanceRule, GovernanceLog, DataLineage
from app.models.analysis import AnalysisResult

__all__ = [
    "Base",
    "TimestampMixin",
    "MonitorKeyword",
    "Video",
    "Comment",
    "Danmaku",
    "GovernanceRule",
    "GovernanceLog",
    "DataLineage",
    "AnalysisResult",
]
```

- [ ] **Step 4: 验证数据库连接**

```bash
cd /workspace && source .venv/bin/activate && python -c "
from app.database import engine
from app.models.base import Base
from sqlalchemy import inspect
inspector = inspect(engine)
print('DB connection OK, tables:', inspector.get_table_names())
"
```

期望：`DB connection OK, tables: []`

- [ ] **Step 5: Commit**

```bash
git add app/database.py app/models/__init__.py app/models/base.py
git commit -m "feat: add database connection and base model"
```

---

### Task 1.4: 全部数据模型

**Files:**
- Create: `app/models/monitor.py`
- Create: `app/models/video.py`
- Create: `app/models/comment.py`
- Create: `app/models/danmaku.py`
- Create: `app/models/governance.py`
- Create: `app/models/analysis.py`

- [ ] **Step 1: 创建 app/models/monitor.py**

```python
from sqlalchemy import String, Integer, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MonitorKeyword(Base):
    __tablename__ = "monitor_keywords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword: Mapped[str] = mapped_column(String(200), nullable=False)
    partition_filter: Mapped[str | None] = mapped_column(String(200))
    crawl_interval: Mapped[int] = mapped_column(Integer, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[str] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[str] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
```

- [ ] **Step 2: 创建 app/models/video.py**

```python
from sqlalchemy import String, Integer, BigInteger, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bvid: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    play_count: Mapped[int] = mapped_column(BigInteger, default=0)
    danmaku_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    pub_time: Mapped[str | None] = mapped_column(DateTime)
    partition_tag: Mapped[str | None] = mapped_column(String(100))
    keyword_id: Mapped[int | None] = mapped_column(ForeignKey("monitor_keywords.id"))
    created_at: Mapped[str] = mapped_column(
        DateTime, server_default=func.now()
    )
```

- [ ] **Step 3: 创建 app/models/comment.py**

```python
from sqlalchemy import String, Integer, BigInteger, Text, Boolean, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rpid: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    video_bvid: Mapped[str] = mapped_column(String(20), ForeignKey("videos.bvid"), nullable=False, index=True)
    user_mid: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    reply_count: Mapped[int] = mapped_column(Integer, default=0)
    has_image: Mapped[bool] = mapped_column(Boolean, default=False)
    image_urls: Mapped[str | None] = mapped_column(JSON)
    pub_time: Mapped[str | None] = mapped_column(DateTime)
    created_at: Mapped[str] = mapped_column(
        DateTime, server_default=func.now()
    )
```

- [ ] **Step 4: 创建 app/models/danmaku.py**

```python
from sqlalchemy import String, Integer, DateTime, DECIMAL, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Danmaku(Base):
    __tablename__ = "danmakus"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_bvid: Mapped[str] = mapped_column(String(20), ForeignKey("videos.bvid"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(String(500), nullable=False)
    timeline: Mapped[float] = mapped_column(DECIMAL(10, 3), nullable=False)
    send_time: Mapped[str | None] = mapped_column(DateTime)
    created_at: Mapped[str] = mapped_column(
        DateTime, server_default=func.now()
    )
```

- [ ] **Step 5: 创建 app/models/governance.py**

```python
from sqlalchemy import String, Integer, DateTime, JSON, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GovernanceRule(Base):
    __tablename__ = "governance_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_name: Mapped[str] = mapped_column(String(200), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    rule_config: Mapped[str | None] = mapped_column(JSON)
    phase: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[str] = mapped_column(
        DateTime, server_default=func.now()
    )


class GovernanceLog(Base):
    __tablename__ = "governance_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    rule_id: Mapped[int | None] = mapped_column(ForeignKey("governance_rules.id"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    before_value: Mapped[str | None] = mapped_column(JSON)
    after_value: Mapped[str | None] = mapped_column(JSON)
    executed_at: Mapped[str] = mapped_column(
        DateTime, server_default=func.now()
    )


class DataLineage(Base):
    __tablename__ = "data_lineage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[str] = mapped_column(String(100), nullable=False)
    transform_step: Mapped[str] = mapped_column(String(200), nullable=False)
    executed_at: Mapped[str] = mapped_column(
        DateTime, server_default=func.now()
    )
```

- [ ] **Step 6: 创建 app/models/analysis.py**

```python
from sqlalchemy import String, Integer, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_type: Mapped[str] = mapped_column(String(50), nullable=False)
    ref_type: Mapped[str] = mapped_column(String(50), nullable=False)
    ref_id: Mapped[str] = mapped_column(String(100), nullable=False)
    result_data: Mapped[str | None] = mapped_column(JSON)
    analyzed_at: Mapped[str] = mapped_column(
        DateTime, server_default=func.now()
    )
```

- [ ] **Step 7: 验证模型可被正确发现**

```bash
cd /workspace && source .venv/bin/activate && python -c "
from app.models import Base, MonitorKeyword, Video, Comment, Danmaku, GovernanceRule, GovernanceLog, DataLineage, AnalysisResult
print('All models imported successfully')
print('Tables:', [t for t in Base.metadata.tables.keys()])
"
```

期望：打印出所有 8 张表名。

- [ ] **Step 8: Commit**

```bash
git add app/models/
git commit -m "feat: add all data models (8 tables)"
```

---

### Task 1.5: 数据库初始化脚本

**Files:**
- Create: `scripts/__init__.py`
- Create: `scripts/init_db.py`

- [ ] **Step 1: 创建 scripts/init_db.py**

```python
"""
数据库建表脚本
用法: python scripts/init_db.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import engine
from app.models import Base

if __name__ == "__main__":
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Done. Tables created:")
    for table_name in Base.metadata.tables:
        print(f"  - {table_name}")
```

- [ ] **Step 2: 执行建表脚本**

```bash
cd /workspace && source .venv/bin/activate && python scripts/init_db.py
```

期望输出：列出所有 8 张表名。

- [ ] **Step 3: Commit**

```bash
git add scripts/init_db.py
git commit -m "feat: add database initialization script"
```

---

### Task 1.6: Pydantic Schemas

**Files:**
- Create: `app/schemas/__init__.py`
- Create: `app/schemas/common.py`
- Create: `app/schemas/monitor.py`
- Create: `app/schemas/video.py`
- Create: `app/schemas/comment.py`
- Create: `app/schemas/governance.py`
- Create: `app/schemas/analysis.py`

- [ ] **Step 1: 创建 app/schemas/__init__.py**

```python
from app.schemas.common import PaginatedResponse, ErrorResponse
from app.schemas.monitor import (
    MonitorKeywordCreate,
    MonitorKeywordUpdate,
    MonitorKeywordResponse,
)
from app.schemas.video import VideoResponse, VideoListResponse
from app.schemas.comment import CommentResponse, CommentListResponse
from app.schemas.governance import (
    GovernanceRuleCreate,
    GovernanceRuleResponse,
    QualityReportResponse,
    LineageResponse,
    LogResponse,
)
from app.schemas.analysis import (
    SentimentResponse,
    KeywordsResponse,
    TrendResponse,
)

__all__ = [
    "PaginatedResponse",
    "ErrorResponse",
    "MonitorKeywordCreate",
    "MonitorKeywordUpdate",
    "MonitorKeywordResponse",
    "VideoResponse",
    "VideoListResponse",
    "CommentResponse",
    "CommentListResponse",
    "GovernanceRuleCreate",
    "GovernanceRuleResponse",
    "QualityReportResponse",
    "LineageResponse",
    "LogResponse",
    "SentimentResponse",
    "KeywordsResponse",
    "TrendResponse",
]
```

- [ ] **Step 2: 创建 app/schemas/common.py**

```python
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
```

- [ ] **Step 3: 创建 app/schemas/monitor.py**

```python
from datetime import datetime
from pydantic import BaseModel, Field


class MonitorKeywordCreate(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=200)
    partition_filter: str | None = None
    crawl_interval: int = Field(default=60, ge=10)
    is_active: bool = True


class MonitorKeywordUpdate(BaseModel):
    keyword: str | None = Field(None, min_length=1, max_length=200)
    partition_filter: str | None = None
    crawl_interval: int | None = Field(None, ge=10)
    is_active: bool | None = None


class MonitorKeywordResponse(BaseModel):
    id: int
    keyword: str
    partition_filter: str | None
    crawl_interval: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: 创建 app/schemas/video.py**

```python
from datetime import datetime
from pydantic import BaseModel


class VideoResponse(BaseModel):
    id: int
    bvid: str
    title: str
    description: str | None
    play_count: int
    danmaku_count: int
    comment_count: int
    pub_time: datetime | None
    partition_tag: str | None
    keyword_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class VideoListResponse(BaseModel):
    items: list[VideoResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
```

- [ ] **Step 5: 创建 app/schemas/comment.py**

```python
from datetime import datetime
from pydantic import BaseModel


class CommentResponse(BaseModel):
    id: int
    rpid: int
    video_bvid: str
    user_mid: str
    content: str
    like_count: int
    reply_count: int
    has_image: bool
    image_urls: list[str] | None
    pub_time: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CommentListResponse(BaseModel):
    items: list[CommentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
```

- [ ] **Step 6: 创建 app/schemas/governance.py**

```python
from datetime import datetime
from pydantic import BaseModel, Field


class GovernanceRuleCreate(BaseModel):
    rule_name: str = Field(..., min_length=1, max_length=200)
    rule_type: str = Field(..., pattern=r"^(format_check|dedup|desensitize|clean|quality)$")
    rule_config: dict | None = None
    phase: str = Field(..., min_length=1, max_length=50)
    is_active: bool = True


class GovernanceRuleResponse(BaseModel):
    id: int
    rule_name: str
    rule_type: str
    rule_config: dict | None
    phase: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class QualityReportResponse(BaseModel):
    total_records: int
    completeness_rate: float
    dedup_rate: float
    anomaly_rate: float
    timeliness_score: float
    overall_score: float
    generated_at: datetime


class LineageResponse(BaseModel):
    id: int
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    transform_step: str
    executed_at: datetime

    model_config = {"from_attributes": True}


class LogResponse(BaseModel):
    id: int
    target_type: str
    target_id: int
    rule_id: int | None
    action: str
    before_value: dict | None
    after_value: dict | None
    executed_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 7: 创建 app/schemas/analysis.py**

```python
from datetime import datetime
from pydantic import BaseModel


class SentimentResponse(BaseModel):
    positive_ratio: float
    neutral_ratio: float
    negative_ratio: float
    total_samples: int
    trend_data: list[dict]
    analyzed_at: datetime


class KeywordsResponse(BaseModel):
    keywords: list[dict]
    total_terms: int
    analyzed_at: datetime


class TrendResponse(BaseModel):
    time_series: list[dict]
    peak_points: list[dict]
    analyzed_at: datetime
```

- [ ] **Step 8: Commit**

```bash
git add app/schemas/
git commit -m "feat: add pydantic schemas for all models"
```

---

### Task 1.7: 依赖注入模块

**Files:**
- Create: `app/dependencies.py`

- [ ] **Step 1: 创建 app/dependencies.py**

```python
from sqlalchemy.orm import Session

from app.database import SessionLocal


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: Commit**

```bash
git add app/dependencies.py
git commit -m "feat: add dependency injection module"
```

---

### Task 1.8: API 路由骨架 + main.py

**Files:**
- Create: `app/api/__init__.py`
- Create: `app/api/monitor.py`
- Create: `app/api/videos.py`
- Create: `app/api/comments.py`
- Create: `app/api/analysis.py`
- Create: `app/api/governance.py`
- Create: `app/api/export.py`
- Create: `app/main.py`

- [ ] **Step 1: 创建 app/api/__init__.py**

```python
from fastapi import APIRouter

from app.api.monitor import router as monitor_router
from app.api.videos import router as videos_router
from app.api.comments import router as comments_router
from app.api.analysis import router as analysis_router
from app.api.governance import router as governance_router
from app.api.export import router as export_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(monitor_router)
api_router.include_router(videos_router)
api_router.include_router(comments_router)
api_router.include_router(analysis_router)
api_router.include_router(governance_router)
api_router.include_router(export_router)
```

- [ ] **Step 2: 创建 app/api/monitor.py**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.monitor import MonitorKeyword
from app.schemas.common import PaginatedResponse, ErrorResponse
from app.schemas.monitor import (
    MonitorKeywordCreate,
    MonitorKeywordUpdate,
    MonitorKeywordResponse,
)

router = APIRouter(prefix="/monitor", tags=["监控配置"])


@router.get(
    "/keywords",
    response_model=PaginatedResponse[MonitorKeywordResponse],
    summary="获取监控关键词列表",
)
def list_keywords(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    total = db.query(MonitorKeyword).count()
    items = (
        db.query(MonitorKeyword)
        .order_by(MonitorKeyword.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    total_pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        items=[MonitorKeywordResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "/keywords",
    response_model=MonitorKeywordResponse,
    status_code=201,
    summary="新增监控关键词",
)
def create_keyword(
    body: MonitorKeywordCreate,
    db: Session = Depends(get_db),
):
    keyword = MonitorKeyword(**body.model_dump())
    db.add(keyword)
    db.commit()
    db.refresh(keyword)
    return MonitorKeywordResponse.model_validate(keyword)


@router.put(
    "/keywords/{keyword_id}",
    response_model=MonitorKeywordResponse,
    summary="修改监控配置",
)
def update_keyword(
    keyword_id: int,
    body: MonitorKeywordUpdate,
    db: Session = Depends(get_db),
):
    keyword = db.query(MonitorKeyword).filter(MonitorKeyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(keyword, key, value)
    db.commit()
    db.refresh(keyword)
    return MonitorKeywordResponse.model_validate(keyword)


@router.delete(
    "/keywords/{keyword_id}",
    status_code=204,
    summary="删除监控关键词",
)
def delete_keyword(
    keyword_id: int,
    db: Session = Depends(get_db),
):
    keyword = db.query(MonitorKeyword).filter(MonitorKeyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")
    db.delete(keyword)
    db.commit()


@router.post(
    "/keywords/{keyword_id}/trigger",
    response_model=dict,
    summary="手动触发爬取",
)
def trigger_crawl(
    keyword_id: int,
    db: Session = Depends(get_db),
):
    keyword = db.query(MonitorKeyword).filter(MonitorKeyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")
    return {"status": "queued", "keyword_id": keyword_id, "keyword": keyword.keyword}
```

- [ ] **Step 3: 创建 app/api/videos.py**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.video import Video
from app.schemas.video import VideoResponse, VideoListResponse

router = APIRouter(prefix="/videos", tags=["视频数据"])


@router.get(
    "/",
    response_model=VideoListResponse,
    summary="获取视频列表",
)
def list_videos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None, description="按标题关键词筛选"),
    partition: str | None = Query(None, description="按分区筛选"),
    db: Session = Depends(get_db),
):
    query = db.query(Video)
    if keyword:
        query = query.filter(Video.title.contains(keyword))
    if partition:
        query = query.filter(Video.partition_tag == partition)

    total = query.count()
    items = (
        query.order_by(Video.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    total_pages = (total + page_size - 1) // page_size
    return VideoListResponse(
        items=[VideoResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{bvid}",
    response_model=VideoResponse,
    summary="获取视频详情",
)
def get_video(
    bvid: str,
    db: Session = Depends(get_db),
):
    video = db.query(Video).filter(Video.bvid == bvid).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    return VideoResponse.model_validate(video)
```

- [ ] **Step 4: 创建 app/api/comments.py**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.comment import Comment
from app.schemas.comment import CommentResponse, CommentListResponse

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
```

- [ ] **Step 5: 创建 app/api/analysis.py**

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.analysis import AnalysisResult

router = APIRouter(prefix="/analysis", tags=["分析结果"])


@router.get("/sentiment", summary="情感分析结果")
def get_sentiment(
    video_bvid: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(AnalysisResult).filter(AnalysisResult.analysis_type == "sentiment")
    if video_bvid:
        query = query.filter(AnalysisResult.ref_id == video_bvid)
    result = query.order_by(AnalysisResult.analyzed_at.desc()).first()
    if not result:
        return {"status": "no_data", "message": "暂无分析结果"}
    return result.result_data


@router.get("/keywords", summary="关键词提取结果")
def get_keywords(
    video_bvid: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(AnalysisResult).filter(AnalysisResult.analysis_type == "keywords")
    if video_bvid:
        query = query.filter(AnalysisResult.ref_id == video_bvid)
    result = query.order_by(AnalysisResult.analyzed_at.desc()).first()
    if not result:
        return {"status": "no_data", "message": "暂无分析结果"}
    return result.result_data


@router.get("/trend", summary="趋势分析数据")
def get_trend(
    keyword_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(AnalysisResult).filter(AnalysisResult.analysis_type == "trend")
    if keyword_id:
        query = query.filter(AnalysisResult.ref_id == str(keyword_id))
    result = query.order_by(AnalysisResult.analyzed_at.desc()).first()
    if not result:
        return {"status": "no_data", "message": "暂无分析结果"}
    return result.result_data


@router.get("/user-profile", summary="用户画像数据")
def get_user_profile(
    video_bvid: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(AnalysisResult).filter(AnalysisResult.analysis_type == "user_profile")
    if video_bvid:
        query = query.filter(AnalysisResult.ref_id == video_bvid)
    result = query.order_by(AnalysisResult.analyzed_at.desc()).first()
    if not result:
        return {"status": "no_data", "message": "暂无分析结果"}
    return result.result_data


@router.get("/image-ocr", summary="图片评论分析")
def get_image_ocr(
    video_bvid: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(AnalysisResult).filter(AnalysisResult.analysis_type == "image_ocr")
    if video_bvid:
        query = query.filter(AnalysisResult.ref_id == video_bvid)
    result = query.order_by(AnalysisResult.analyzed_at.desc()).first()
    if not result:
        return {"status": "no_data", "message": "暂无分析结果"}
    return result.result_data


@router.get("/danmaku-density", summary="弹幕密度分析")
def get_danmaku_density(
    video_bvid: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(AnalysisResult).filter(AnalysisResult.analysis_type == "danmaku_density")
    if video_bvid:
        query = query.filter(AnalysisResult.ref_id == video_bvid)
    result = query.order_by(AnalysisResult.analyzed_at.desc()).first()
    if not result:
        return {"status": "no_data", "message": "暂无分析结果"}
    return result.result_data


@router.get("/topic-cluster", summary="话题聚类结果")
def get_topic_cluster(
    keyword_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(AnalysisResult).filter(AnalysisResult.analysis_type == "topic_cluster")
    if keyword_id:
        query = query.filter(AnalysisResult.ref_id == str(keyword_id))
    result = query.order_by(AnalysisResult.analyzed_at.desc()).first()
    if not result:
        return {"status": "no_data", "message": "暂无分析结果"}
    return result.result_data


@router.get("/network", summary="评论互动网络数据")
def get_network(
    video_bvid: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(AnalysisResult).filter(AnalysisResult.analysis_type == "network")
    if video_bvid:
        query = query.filter(AnalysisResult.ref_id == video_bvid)
    result = query.order_by(AnalysisResult.analyzed_at.desc()).first()
    if not result:
        return {"status": "no_data", "message": "暂无分析结果"}
    return result.result_data
```

- [ ] **Step 6: 创建 app/api/governance.py**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.governance import GovernanceRule, GovernanceLog, DataLineage
from app.schemas.governance import (
    GovernanceRuleCreate,
    GovernanceRuleResponse,
    QualityReportResponse,
    LineageResponse,
    LogResponse,
)

router = APIRouter(prefix="/governance", tags=["数据治理"])


@router.get("/rules", response_model=list[GovernanceRuleResponse], summary="治理规则列表")
def list_rules(db: Session = Depends(get_db)):
    items = db.query(GovernanceRule).order_by(GovernanceRule.created_at.desc()).all()
    return [GovernanceRuleResponse.model_validate(item) for item in items]


@router.post("/rules", response_model=GovernanceRuleResponse, status_code=201, summary="新增治理规则")
def create_rule(body: GovernanceRuleCreate, db: Session = Depends(get_db)):
    rule = GovernanceRule(**body.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return GovernanceRuleResponse.model_validate(rule)


@router.get("/quality-report", response_model=QualityReportResponse, summary="数据质量报告")
def get_quality_report(db: Session = Depends(get_db)):
    return QualityReportResponse(
        total_records=0,
        completeness_rate=0.0,
        dedup_rate=0.0,
        anomaly_rate=0.0,
        timeliness_score=0.0,
        overall_score=0.0,
    )


@router.get("/lineage", response_model=list[LineageResponse], summary="数据血缘查询")
def get_lineage(
    source_type: str | None = Query(None),
    source_id: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(DataLineage)
    if source_type:
        query = query.filter(DataLineage.source_type == source_type)
    if source_id:
        query = query.filter(DataLineage.source_id == source_id)
    items = query.order_by(DataLineage.executed_at.desc()).limit(100).all()
    return [LineageResponse.model_validate(item) for item in items]


@router.get("/logs", response_model=list[LogResponse], summary="治理操作日志")
def get_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items = (
        db.query(GovernanceLog)
        .order_by(GovernanceLog.executed_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return [LogResponse.model_validate(item) for item in items]
```

- [ ] **Step 7: 创建 app/api/export.py**

```python
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
import io
import json
import csv

router = APIRouter(prefix="/export", tags=["数据导出"])


@router.get("/report/csv", summary="导出CSV报告")
def export_csv(
    video_bvid: str | None = Query(None),
):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["分析类型", "数据标识", "分析时间", "备注"])
    writer.writerow(["示例数据", video_bvid or "N/A", "2026-01-01", "演示"])
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=report.csv"},
    )


@router.get("/report/json", summary="导出JSON报告")
def export_json(
    video_bvid: str | None = Query(None),
):
    data = {
        "report_type": "舆情分析报告",
        "target": video_bvid or "全局",
        "generated_at": "2026-01-01T00:00:00",
        "note": "演示数据",
    }
    return data
```

- [ ] **Step 8: 创建 app/main.py**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="B站舆情监控与分析平台",
    description="覆盖数据采集、治理、分析、API服务、可视化展示的舆情监控系统",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", tags=["系统"])
def root():
    return {
        "app": "B站舆情监控与分析平台",
        "version": "1.0.0",
        "docs": "/docs",
    }
```

- [ ] **Step 9: 启动服务验证**

```bash
cd /workspace && source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 &
```

等待启动后验证：

```bash
curl http://localhost:8000/
curl http://localhost:8000/api/v1/monitor/keywords
curl http://localhost:8000/docs
```

期望：
- `GET /` 返回 `{"app": "...", "version": "1.0.0", "docs": "/docs"}`
- `GET /api/v1/monitor/keywords` 返回 `{"items": [], "total": 0, ...}`
- `GET /docs` 返回 Swagger 页面 HTML

- [ ] **Step 10: Commit**

```bash
git add app/api/ app/main.py
git commit -m "feat: add API routes and FastAPI application entry point"
```

---

## Phase 2: Celery 异步任务基础

### Task 2.1: Celery 实例 + 任务文件

**Files:**
- Create: `app/tasks/__init__.py`
- Create: `app/tasks/crawl.py`
- Create: `app/tasks/governance.py`
- Create: `app/tasks/analysis.py`

- [ ] **Step 1: 创建 app/tasks/__init__.py（Celery 应用实例）**

```python
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
)
```

- [ ] **Step 2: 创建 app/tasks/crawl.py**

```python
from app.tasks import celery_app


@celery_app.task(bind=True, name="crawl_by_keyword")
def crawl_by_keyword(self, keyword_id: int, keyword: str):
    self.update_state(state="PROGRESS", meta={"stage": "starting", "keyword": keyword})
    # TODO: 集成爬虫服务，调用 B站 API 采集数据
    return {"keyword_id": keyword_id, "keyword": keyword, "status": "completed", "videos_found": 0}
```

- [ ] **Step 3: 创建 app/tasks/governance.py**

```python
from app.tasks import celery_app


@celery_app.task(bind=True, name="run_governance_pipeline")
def run_governance_pipeline(self):
    self.update_state(state="PROGRESS", meta={"stage": "starting"})
    # TODO: 集成治理引擎，执行四层治理流程
    return {"status": "completed", "records_processed": 0}


@celery_app.task(bind=True, name="generate_quality_report")
def generate_quality_report(self):
    # TODO: 生成数据质量报告
    return {"status": "completed", "overall_score": 0.0}
```

- [ ] **Step 4: 创建 app/tasks/analysis.py**

```python
from app.tasks import celery_app


@celery_app.task(bind=True, name="run_sentiment_analysis")
def run_sentiment_analysis(self, video_bvid: str):
    self.update_state(state="PROGRESS", meta={"stage": "analyzing", "video": video_bvid})
    # TODO: 集成 SnowNLP 情感分析
    return {"status": "completed", "video_bvid": video_bvid}


@celery_app.task(bind=True, name="run_keyword_extraction")
def run_keyword_extraction(self, video_bvid: str):
    # TODO: 集成 Jieba + TF-IDF 关键词提取
    return {"status": "completed", "video_bvid": video_bvid}


@celery_app.task(bind=True, name="run_full_analysis")
def run_full_analysis(self, video_bvid: str):
    # TODO: 链式调用全部 8 个分析维度
    return {"status": "completed", "video_bvid": video_bvid, "dimensions": 8}
```

- [ ] **Step 5: 验证 Celery Worker 启动**

```bash
cd /workspace && source .venv/bin/activate && celery -A app.tasks worker --loglevel=info --concurrency=2 &
```

等 Worker 启动后测试任务入队：

```bash
cd /workspace && source .venv/bin/activate && python -c "
from app.tasks.crawl import crawl_by_keyword
result = crawl_by_keyword.delay(1, '测试关键词')
print('Task ID:', result.id)
"
```

期望：打印出 Task ID，且 Celery Worker 日志显示任务被成功执行。

- [ ] **Step 6: Commit**

```bash
git add app/tasks/
git commit -m "feat: add celery app and async task definitions"
```

---

## Phase 3: Web 前端骨架

### Task 3.1: 页面路由 + 基础模板

**Files:**
- Create: `app/web/__init__.py`
- Create: `app/web/routes.py`
- Create: `app/web/templates/base.html`
- Create: `app/web/templates/dashboard.html`
- Create: `app/web/templates/videos.html`
- Create: `app/web/templates/video_detail.html`
- Create: `app/web/templates/governance.html`
- Create: `app/web/templates/report.html`
- Create: `app/web/static/css/style.css`
- Modify: `app/main.py`

- [ ] **Step 1: 创建 app/web/__init__.py**

```python
"""
Web 前端页面模块
"""
```

- [ ] **Step 2: 创建 app/web/routes.py**

```python
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/web/templates")

router = APIRouter(tags=["页面"])


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/videos", response_class=HTMLResponse)
async def videos_page(request: Request):
    return templates.TemplateResponse("videos.html", {"request": request})


@router.get("/videos/{bvid}", response_class=HTMLResponse)
async def video_detail(request: Request, bvid: str):
    return templates.TemplateResponse("video_detail.html", {"request": request, "bvid": bvid})


@router.get("/governance", response_class=HTMLResponse)
async def governance_page(request: Request):
    return templates.TemplateResponse("governance.html", {"request": request})


@router.get("/report", response_class=HTMLResponse)
async def report_page(request: Request):
    return templates.TemplateResponse("report.html", {"request": request})
```

- [ ] **Step 3: 创建 app/web/templates/base.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}B站舆情监控平台{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
    <link href="/static/css/style.css" rel="stylesheet">
    {% block head %}{% endblock %}
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="/dashboard">🔍 舆情监控平台</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link" href="/dashboard">仪表盘</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/videos">视频列表</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/governance">数据治理</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/report">报告导出</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/docs" target="_blank">API文档</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <main class="container-fluid py-4">
        {% block content %}{% endblock %}
    </main>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

- [ ] **Step 4: 创建 app/web/templates/dashboard.html**

```html
{% extends "base.html" %}
{% block title %}仪表盘 - B站舆情监控平台{% endblock %}

{% block content %}
<h1 class="mb-4">📊 舆情仪表盘</h1>

<div class="row mb-4">
    <div class="col-md-3">
        <div class="card text-bg-primary">
            <div class="card-body">
                <h5 class="card-title">监控视频数</h5>
                <p class="card-text display-6" id="stat-videos">0</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card text-bg-success">
            <div class="card-body">
                <h5 class="card-title">评论总量</h5>
                <p class="card-text display-6" id="stat-comments">0</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card text-bg-info">
            <div class="card-body">
                <h5 class="card-title">今日新增</h5>
                <p class="card-text display-6" id="stat-today">0</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card text-bg-warning">
            <div class="card-body">
                <h5 class="card-title">数据质量评分</h5>
                <p class="card-text display-6" id="stat-quality">--</p>
            </div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-md-6 mb-4">
        <div class="card">
            <div class="card-header">📈 情感趋势</div>
            <div class="card-body">
                <div id="chart-sentiment" style="height: 350px;"></div>
            </div>
        </div>
    </div>
    <div class="col-md-6 mb-4">
        <div class="card">
            <div class="card-header">🥧 情感占比</div>
            <div class="card-body">
                <div id="chart-sentiment-pie" style="height: 350px;"></div>
            </div>
        </div>
    </div>
    <div class="col-md-6 mb-4">
        <div class="card">
            <div class="card-header">☁️ 关键词词云</div>
            <div class="card-body">
                <div id="chart-wordcloud" style="height: 350px;"></div>
            </div>
        </div>
    </div>
    <div class="col-md-6 mb-4">
        <div class="card">
            <div class="card-header">🎯 话题聚类</div>
            <div class="card-body">
                <div id="chart-cluster" style="height: 350px;"></div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
document.addEventListener('DOMContentLoaded', function () {
    // 情感趋势折线图（占位）
    var chart1 = echarts.init(document.getElementById('chart-sentiment'));
    chart1.setOption({
        title: { text: '近30天情感趋势', textStyle: { fontSize: 14 } },
        tooltip: { trigger: 'axis' },
        legend: { data: ['正面', '中性', '负面'] },
        xAxis: { type: 'category', data: [] },
        yAxis: { type: 'value' },
        series: [
            { name: '正面', type: 'line', data: [], smooth: true },
            { name: '中性', type: 'line', data: [], smooth: true },
            { name: '负面', type: 'line', data: [], smooth: true }
        ]
    });

    // 情感占比饼图（占位）
    var chart2 = echarts.init(document.getElementById('chart-sentiment-pie'));
    chart2.setOption({
        title: { text: '情感分布', textStyle: { fontSize: 14 } },
        series: [{
            type: 'pie',
            radius: ['40%', '70%'],
            data: [
                { value: 0, name: '正面' },
                { value: 0, name: '中性' },
                { value: 0, name: '负面' }
            ]
        }]
    });

    // 占位图表
    echarts.init(document.getElementById('chart-wordcloud')).setOption({
        title: { text: '关键词词云', textStyle: { fontSize: 14 } }
    });
    echarts.init(document.getElementById('chart-cluster')).setOption({
        title: { text: '话题聚类', textStyle: { fontSize: 14 } }
    });
});
</script>
{% endblock %}
```

- [ ] **Step 5: 创建其他模板页面（占位，含基础结构）**

`app/web/templates/videos.html`：

```html
{% extends "base.html" %}
{% block title %}视频列表 - B站舆情监控平台{% endblock %}
{% block content %}
<h1 class="mb-4">🎬 视频列表</h1>
<div class="card">
    <div class="card-body">
        <div class="table-responsive">
            <table class="table table-striped table-hover">
                <thead>
                    <tr>
                        <th>BV号</th><th>标题</th><th>分区</th><th>播放量</th><th>评论数</th><th>弹幕数</th><th>发布时间</th><th>操作</th>
                    </tr>
                </thead>
                <tbody id="video-table-body">
                    <tr><td colspan="8" class="text-center text-muted py-4">暂无数据，请先配置监控关键词并触发采集</td></tr>
                </tbody>
            </table>
        </div>
        <nav><ul class="pagination justify-content-center" id="video-pagination"></ul></nav>
    </div>
</div>
{% endblock %}
```

`app/web/templates/video_detail.html`：

```html
{% extends "base.html" %}
{% block title %}视频详情 - {{ bvid }}{% endblock %}
{% block content %}
<h1 class="mb-4">🎬 视频详情 <small class="text-muted">{{ bvid }}</small></h1>
<div class="row">
    <div class="col-md-6 mb-4">
        <div class="card"><div class="card-header">📈 情感分析</div><div class="card-body"><div id="chart-detail-sentiment" style="height:300px;"></div></div></div>
    </div>
    <div class="col-md-6 mb-4">
        <div class="card"><div class="card-header">☁️ 关键词词云</div><div class="card-body"><div id="chart-detail-wordcloud" style="height:300px;"></div></div></div>
    </div>
    <div class="col-md-6 mb-4">
        <div class="card"><div class="card-header">🎯 弹幕密度</div><div class="card-body"><div id="chart-detail-danmaku" style="height:300px;"></div></div></div>
    </div>
    <div class="col-md-6 mb-4">
        <div class="card"><div class="card-header">💬 评论列表</div><div class="card-body"><div id="comments-container">暂无评论数据</div></div></div>
    </div>
</div>
{% endblock %}
{% block scripts %}
<script>
document.addEventListener('DOMContentLoaded', function () {
    echarts.init(document.getElementById('chart-detail-sentiment')).setOption({title:{text:'情感分析'}});
    echarts.init(document.getElementById('chart-detail-wordcloud')).setOption({title:{text:'关键词词云'}});
    echarts.init(document.getElementById('chart-detail-danmaku')).setOption({title:{text:'弹幕密度'}});
});
</script>
{% endblock %}
```

`app/web/templates/governance.html`：

```html
{% extends "base.html" %}
{% block title %}数据治理 - B站舆情监控平台{% endblock %}
{% block content %}
<h1 class="mb-4">🛡️ 数据治理</h1>
<div class="row">
    <div class="col-md-8">
        <div class="card mb-4">
            <div class="card-header">📊 数据质量趋势</div>
            <div class="card-body"><div id="chart-quality" style="height:300px;"></div></div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card mb-4">
            <div class="card-header">📋 治理规则</div>
            <div class="card-body"><p class="text-muted">暂无规则配置</p></div>
        </div>
    </div>
    <div class="col-12">
        <div class="card">
            <div class="card-header">🔗 数据血缘</div>
            <div class="card-body"><div id="chart-lineage" style="height:400px;"></div></div>
        </div>
    </div>
</div>
{% endblock %}
{% block scripts %}
<script>
document.addEventListener('DOMContentLoaded', function () {
    echarts.init(document.getElementById('chart-quality')).setOption({title:{text:'数据质量趋势'}});
    echarts.init(document.getElementById('chart-lineage')).setOption({title:{text:'数据血缘图'}});
});
</script>
{% endblock %}
```

`app/web/templates/report.html`：

```html
{% extends "base.html" %}
{% block title %}报告导出 - B站舆情监控平台{% endblock %}
{% block content %}
<h1 class="mb-4">📥 报告导出</h1>
<div class="card">
    <div class="card-body">
        <div class="row g-3">
            <div class="col-md-4">
                <label class="form-label">分析维度</label>
                <select class="form-select" id="report-dimension">
                    <option value="sentiment">情感分析</option>
                    <option value="keywords">关键词提取</option>
                    <option value="trend">趋势分析</option>
                    <option value="full">综合分析报告</option>
                </select>
            </div>
            <div class="col-md-4">
                <label class="form-label">导出格式</label>
                <select class="form-select" id="report-format">
                    <option value="csv">CSV</option>
                    <option value="json">JSON</option>
                </select>
            </div>
            <div class="col-md-4 d-flex align-items-end">
                <button class="btn btn-primary w-100" onclick="exportReport()">生成并下载报告</button>
            </div>
        </div>
    </div>
</div>
{% endblock %}
{% block scripts %}
<script>
function exportReport() {
    var dim = document.getElementById('report-dimension').value;
    var fmt = document.getElementById('report-format').value;
    alert('导出功能即将上线\n维度: ' + dim + '\n格式: ' + fmt);
}
</script>
{% endblock %}
```

- [ ] **Step 6: 创建 app/web/static/css/style.css**

```css
body {
    background-color: #f5f6fa;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

.navbar {
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.card {
    border: none;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
    border-radius: 10px;
    margin-bottom: 1.5rem;
}

.card-header {
    background-color: #fff;
    border-bottom: 1px solid #eee;
    font-weight: 600;
}

.card-text.display-6 {
    font-size: 2rem;
    font-weight: 700;
}

.table th {
    font-weight: 600;
    white-space: nowrap;
}

.pagination {
    margin-top: 1rem;
}
```

- [ ] **Step 7: 更新 app/main.py，注册 Web 路由和静态文件**

在 `app/main.py` 中：

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.api import api_router
from app.web.routes import router as web_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="B站舆情监控与分析平台",
    description="覆盖数据采集、治理、分析、API服务、可视化展示的舆情监控系统",
    version="1.0.0",
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
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard")
```

- [ ] **Step 8: 访问仪表盘验证**

启动服务后访问 `http://localhost:8000/dashboard`，应能看到带导航栏、4个统计卡片和4个图表的仪表盘页面。

- [ ] **Step 9: Commit**

```bash
git add app/web/ app/main.py
git commit -m "feat: add web frontend with dashboard and page templates"
```

---

## Phase 4: 爬虫服务实现

### Task 4.1: B站 API 调用封装

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/services/crawler/__init__.py`
- Create: `app/services/crawler/bilibili.py`

- [ ] **Step 1: 创建 app/services/crawler/bilibili.py**

```python
"""
B站 API 调用封装
参考 B站公开 API（无需登录即可访问）：
  - 搜索: https://api.bilibili.com/x/web-interface/search/type
  - 视频信息: https://api.bilibili.com/x/web-interface/view
  - 评论: https://api.bilibili.com/x/v2/reply
  - 弹幕: https://api.bilibili.com/x/v1/dm/list.so
"""
import hashlib
import time
from dataclasses import dataclass

import httpx

BILIBILI_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

BILIBILI_HEADERS = {
    "User-Agent": BILIBILI_USER_AGENT,
    "Referer": "https://www.bilibili.com/",
}

_SEARCH_URL = "https://api.bilibili.com/x/web-interface/search/type"
_VIDEO_INFO_URL = "https://api.bilibili.com/x/web-interface/view"
_COMMENTS_URL = "https://api.bilibili.com/x/v2/reply"
_DANMAKU_URL = "https://api.bilibili.com/x/v1/dm/list.so"


@dataclass
class VideoInfo:
    bvid: str
    title: str
    description: str
    play_count: int
    danmaku_count: int
    comment_count: int
    pub_time: str
    partition_tag: str


@dataclass
class CommentInfo:
    rpid: int
    user_mid: str
    content: str
    like_count: int
    reply_count: int
    has_image: bool
    image_urls: list[str]
    pub_time: str


@dataclass
class DanmakuInfo:
    content: str
    timeline: float
    send_time: str


class BilibiliAPI:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def _get(self, url: str, params: dict | None = None) -> dict:
        with httpx.Client(timeout=self.timeout, headers=BILIBILI_HEADERS) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()

    def search_videos(self, keyword: str, page: int = 1, page_size: int = 20) -> list[VideoInfo]:
        params = {
            "search_type": "video",
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
        }
        data = self._get(_SEARCH_URL, params=params)
        if data.get("code") != 0:
            return []

        results = []
        for item in data.get("data", {}).get("result", []):
            results.append(VideoInfo(
                bvid=item.get("bvid", ""),
                title=item.get("title", "").replace('<em class="keyword">', "").replace("</em>", ""),
                description=item.get("description", ""),
                play_count=item.get("play", 0),
                danmaku_count=item.get("video_review", 0),
                comment_count=item.get("review", 0),
                pub_time=datetime_from_timestamp(item.get("pubdate", 0)),
                partition_tag=item.get("typename", ""),
            ))
        return results

    def get_video_info(self, bvid: str) -> VideoInfo | None:
        params = {"bvid": bvid}
        data = self._get(_VIDEO_INFO_URL, params=params)
        if data.get("code") != 0:
            return None

        item = data.get("data", {})
        return VideoInfo(
            bvid=item.get("bvid", bvid),
            title=item.get("title", ""),
            description=item.get("desc", ""),
            play_count=item.get("stat", {}).get("view", 0),
            danmaku_count=item.get("stat", {}).get("danmaku", 0),
            comment_count=item.get("stat", {}).get("reply", 0),
            pub_time=datetime_from_timestamp(item.get("pubdate", 0)),
            partition_tag=item.get("tname", ""),
        )

    def get_comments(self, oid: str, page: int = 1, page_size: int = 20, sort: int = 1) -> list[CommentInfo]:
        comment_type = 1
        params = {
            "type": comment_type,
            "oid": oid,
            "pn": page,
            "ps": page_size,
            "sort": sort,
        }
        data = self._get(_COMMENTS_URL, params=params)
        if data.get("code") != 0:
            return []

        results = []
        replies = data.get("data", {}).get("replies", [])
        if not replies:
            return results

        for reply in replies:
            image_urls = []
            content_obj = reply.get("content", {})
            if isinstance(content_obj, dict):
                message = content_obj.get("message", "")
                jump_structure = content_obj.get("jump_structure", {})
                pics = jump_structure.get("pictures", [])
                for pic in pics:
                    img_src = pic.get("img_src", "")
                    if img_src:
                        image_urls.append(img_src)
            else:
                message = str(content_obj)

            results.append(CommentInfo(
                rpid=reply.get("rpid", 0),
                user_mid=str(reply.get("mid", 0)),
                content=message,
                like_count=reply.get("like", 0),
                reply_count=reply.get("rcount", 0),
                has_image=len(image_urls) > 0,
                image_urls=image_urls,
                pub_time=datetime_from_timestamp(reply.get("ctime", 0)),
            ))
        return results

    def get_all_comments(self, oid: str, max_pages: int = 50, page_size: int = 20, sort: int = 1) -> list[CommentInfo]:
        all_comments: list[CommentInfo] = []
        for page in range(1, max_pages + 1):
            comments = self.get_comments(oid, page=page, page_size=page_size, sort=sort)
            if not comments:
                break
            all_comments.extend(comments)
            time.sleep(0.5)
        return all_comments

    def get_danmaku(self, cid: int) -> list[DanmakuInfo]:
        params = {"oid": cid}
        resp_text = ""
        with httpx.Client(timeout=self.timeout, headers=BILIBILI_HEADERS) as client:
            resp = client.get(_DANMAKU_URL, params=params)
            resp.raise_for_status()
            resp_text = resp.text

        results: list[DanmakuInfo] = []
        for line in resp_text.splitlines():
            line = line.strip()
            if not line or not line.startswith("<d "):
                continue
            p_attr = _extract_xml_attr(line, "p")
            if not p_attr:
                continue
            parts = p_attr.split(",")
            if len(parts) < 5:
                continue
            try:
                timeline = float(parts[0])
                send_timestamp = int(parts[4])
            except (ValueError, IndexError):
                continue
            content = _extract_xml_text(line)
            send_time_str = datetime_from_timestamp(send_timestamp)
            results.append(DanmakuInfo(
                content=content,
                timeline=timeline,
                send_time=send_time_str,
            ))
        return results


def _extract_xml_attr(line: str, attr: str) -> str:
    key = f'{attr}="'
    start = line.find(key)
    if start == -1:
        return ""
    start += len(key)
    end = line.find('"', start)
    if end == -1:
        return ""
    return line[start:end]


def _extract_xml_text(line: str) -> str:
    start = line.find(">")
    if start == -1:
        return ""
    start += 1
    end = line.find("</d>", start)
    if end == -1:
        return ""
    return line[start:end]


def datetime_from_timestamp(ts: int) -> str:
    if ts <= 0:
        return ""
    from datetime import datetime, timezone, timedelta
    tz = timezone(timedelta(hours=8))
    return datetime.fromtimestamp(ts, tz=tz).strftime("%Y-%m-%d %H:%M:%S")
```

- [ ] **Step 2: 更新 requirements.txt，添加 httpx**

确保 `requirements.txt` 已包含 `httpx==0.27.2`（在 Task 1.1 中已添加）。

- [ ] **Step 3: 验证 B站 API 调用**

```bash
cd /workspace && source .venv/bin/activate && python -c "
from app.services.crawler.bilibili import BilibiliAPI
api = BilibiliAPI()
videos = api.search_videos('Python教程', page=1, page_size=3)
print(f'搜索到 {len(videos)} 个视频:')
for v in videos:
    print(f'  {v.bvid} - {v.title}')
if videos:
    comments = api.get_comments(videos[0].bvid, page=1, page_size=5)
    print(f'第一个视频的评论数: {len(comments)}')
"
```

- [ ] **Step 4: Commit**

```bash
git add app/services/
git commit -m "feat: add bilibili API client with search/video/comments/danmaku"
```

---

### Task 4.2: 爬虫 Celery 任务实现

**Files:**
- Modify: `app/tasks/crawl.py`

- [ ] **Step 1: 更新 app/tasks/crawl.py**

```python
import hashlib
import time

from app.database import SessionLocal
from app.models.monitor import MonitorKeyword
from app.models.video import Video
from app.models.comment import Comment
from app.models.danmaku import Danmaku
from app.services.crawler.bilibili import BilibiliAPI
from app.tasks import celery_app

SALT = "bilibili_sentiment_salt_2026"


def hash_mid(mid: str) -> str:
    return hashlib.sha256(f"{mid}{SALT}".encode()).hexdigest()[:16]


@celery_app.task(bind=True, name="crawl_by_keyword")
def crawl_by_keyword(self, keyword_id: int, keyword: str):
    self.update_state(state="PROGRESS", meta={"stage": "searching", "keyword": keyword})

    api = BilibiliAPI()
    videos = api.search_videos(keyword, page=1, page_size=20)

    self.update_state(state="PROGRESS", meta={"stage": "fetching_comments", "videos_found": len(videos)})

    db = SessionLocal()
    total_comments = 0
    total_danmaku = 0

    try:
        for i, video_info in enumerate(videos):
            self.update_state(state="PROGRESS", meta={
                "stage": "processing_video",
                "video": video_info.bvid,
                "progress": f"{i + 1}/{len(videos)}",
            })

            existing = db.query(Video).filter(Video.bvid == video_info.bvid).first()
            if existing:
                continue

            video = Video(
                bvid=video_info.bvid,
                title=video_info.title,
                description=video_info.description,
                play_count=video_info.play_count,
                danmaku_count=video_info.danmaku_count,
                comment_count=video_info.comment_count,
                pub_time=video_info.pub_time,
                partition_tag=video_info.partition_tag,
                keyword_id=keyword_id,
            )
            db.add(video)
            db.flush()

            comments = api.get_comments(video_info.bvid, page=1, page_size=40)
            for c in comments:
                existing_comment = db.query(Comment).filter(Comment.rpid == c.rpid).first()
                if existing_comment:
                    continue
                comment = Comment(
                    rpid=c.rpid,
                    video_bvid=video_info.bvid,
                    user_mid=hash_mid(c.user_mid),
                    content=c.content,
                    like_count=c.like_count,
                    reply_count=c.reply_count,
                    has_image=c.has_image,
                    image_urls=c.image_urls if c.image_urls else None,
                    pub_time=c.pub_time,
                )
                db.add(comment)
                total_comments += 1

            time.sleep(0.5)

        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

    return {
        "keyword_id": keyword_id,
        "keyword": keyword,
        "status": "completed",
        "videos_found": len(videos),
        "comments_saved": total_comments,
        "danmaku_saved": total_danmaku,
    }
```

- [ ] **Step 2: 测试爬虫任务**

```bash
cd /workspace && source .venv/bin/activate && python -c "
from app.tasks.crawl import crawl_by_keyword
result = crawl_by_keyword(1, 'Python')
print(result)
"
```

- [ ] **Step 3: Commit**

```bash
git add app/tasks/crawl.py
git commit -m "feat: implement crawl task with bilibili API integration"
```

---

## Phase 5: 治理引擎

### Task 5.1: 治理引擎实现

**Files:**
- Create: `app/services/governance/__init__.py`
- Create: `app/services/governance/engine.py`

- [ ] **Step 1: 创建 app/services/governance/engine.py**

```python
import hashlib
import re
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.governance import GovernanceRule, GovernanceLog, DataLineage

SALT = "bilibili_sentiment_salt_2026"

SENSITIVE_PATTERNS = {
    "phone": re.compile(r"1[3-9]\d{9}"),
    "id_card": re.compile(r"\d{17}[\dXx]"),
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
}


def run_format_check(db: Session, rules: list[GovernanceRule]) -> int:
    count = 0
    comments = db.query(Comment).filter(Comment.content.isnot(None)).all()
    for comment in comments:
        content = comment.content or ""
        if len(content) > 2000:
            before = content
            comment.content = content[:2000]
            db.add(GovernanceLog(
                target_type="comments",
                target_id=comment.id,
                action="truncate",
                before_value={"content": before[:100] + "..."},
                after_value={"content": comment.content[:100] + "..."},
            ))
            count += 1
    db.commit()
    return count


def run_dedup(db: Session, rules: list[GovernanceRule]) -> int:
    count = 0
    from sqlalchemy import func
    duplicates = (
        db.query(
            Comment.content,
            Comment.user_mid,
            Comment.pub_time,
            func.count(Comment.id).label("cnt"),
        )
        .group_by(Comment.content, Comment.user_mid, Comment.pub_time)
        .having(func.count(Comment.id) > 1)
        .all()
    )
    for dup in duplicates:
        records = (
            db.query(Comment)
            .filter(
                Comment.content == dup.content,
                Comment.user_mid == dup.user_mid,
                Comment.pub_time == dup.pub_time,
            )
            .order_by(Comment.id.asc())
            .all()
        )
        keep = records[0]
        for record in records[1:]:
            db.add(GovernanceLog(
                target_type="comments",
                target_id=record.id,
                action="dedup_remove",
                before_value={"rpid": record.rpid},
                after_value={"kept_rpid": keep.rpid},
            ))
            db.delete(record)
            count += 1
    db.commit()
    return count


def run_desensitize(db: Session, rules: list[GovernanceRule]) -> int:
    count = 0
    comments = db.query(Comment).all()
    for comment in comments:
        before_content = comment.content
        new_content = before_content
        for name, pattern in SENSITIVE_PATTERNS.items():
            new_content = pattern.sub(f"[{name}]", new_content)
        if new_content != before_content:
            db.add(GovernanceLog(
                target_type="comments",
                target_id=comment.id,
                action="desensitize",
                before_value={"content": before_content[:100]},
                after_value={"content": new_content[:100]},
            ))
            comment.content = new_content
            count += 1
    db.commit()
    return count


def run_data_cleaning(db: Session, rules: list[GovernanceRule]) -> int:
    count = 0
    import re as re_mod
    html_pattern = re_mod.compile(r"<[^>]+>")
    emoji_pattern = re_mod.compile(
        r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
        r"\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF"
        r"\U00002702-\U000027B0\U000024C2-\U0001F251]+",
        flags=re_mod.UNICODE,
    )
    comments = db.query(Comment).all()
    for comment in comments:
        before = comment.content
        cleaned = html_pattern.sub("", before)
        cleaned = emoji_pattern.sub("", cleaned)
        cleaned = cleaned.strip()
        if cleaned != before:
            comment.content = cleaned
            db.add(GovernanceLog(
                target_type="comments",
                target_id=comment.id,
                action="clean_html_emoji",
                before_value={"content": before[:100]},
                after_value={"content": cleaned[:100]},
            ))
            count += 1
    db.commit()
    return count


def record_lineage(db: Session, source_type: str, source_id: str, target_type: str, target_id: str, step: str):
    lineage = DataLineage(
        source_type=source_type,
        source_id=source_id,
        target_type=target_type,
        target_id=target_id,
        transform_step=step,
    )
    db.add(lineage)
    db.commit()


def compute_quality_report(db: Session) -> dict:
    total = db.query(Comment).count()
    if total == 0:
        return {
            "total_records": 0,
            "completeness_rate": 0.0,
            "dedup_rate": 0.0,
            "anomaly_rate": 0.0,
            "timeliness_score": 0.0,
            "overall_score": 0.0,
        }

    from sqlalchemy import func
    null_count = db.query(Comment).filter(
        func.coalesce(Comment.content, "") == ""
    ).count()
    completeness = round((1 - null_count / total) * 100, 2)

    dedup_actions = db.query(GovernanceLog).filter(
        GovernanceLog.action == "dedup_remove"
    ).count()
    dedup_rate = round(min(dedup_actions / max(total, 1) * 100, 100), 2)

    truncate_actions = db.query(GovernanceLog).filter(
        GovernanceLog.action == "truncate"
    ).count()
    anomaly_rate = round(truncate_actions / max(total, 1) * 100, 2)

    timeliness = 95.0
    overall = round((completeness * 0.4 + (100 - dedup_rate) * 0.3 + timeliness * 0.3), 2)

    return {
        "total_records": total,
        "completeness_rate": completeness,
        "dedup_rate": dedup_rate,
        "anomaly_rate": anomaly_rate,
        "timeliness_score": timeliness,
        "overall_score": overall,
    }


PHASE_HANDLERS = {
    "format_check": run_format_check,
    "dedup": run_dedup,
    "desensitize": run_desensitize,
    "clean": run_data_cleaning,
}


def execute_governance_pipeline(db: Session) -> dict:
    active_rules = db.query(GovernanceRule).filter(GovernanceRule.is_active == True).all()
    results: dict[str, int] = {}

    for phase in ["format_check", "dedup", "clean", "desensitize"]:
        phase_rules = [r for r in active_rules if r.phase == phase]
        handler = PHASE_HANDLERS.get(phase)
        if handler and phase_rules:
            count = handler(db, phase_rules)
            results[phase] = count

    return results
```

- [ ] **Step 2: 更新治理任务文件 app/tasks/governance.py**

```python
from app.database import SessionLocal
from app.services.governance.engine import execute_governance_pipeline, compute_quality_report
from app.tasks import celery_app


@celery_app.task(bind=True, name="run_governance_pipeline")
def run_governance_pipeline(self):
    self.update_state(state="PROGRESS", meta={"stage": "starting"})
    db = SessionLocal()
    try:
        results = execute_governance_pipeline(db)
        return {"status": "completed", "phases": results}
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


@celery_app.task(bind=True, name="generate_quality_report")
def generate_quality_report(self):
    db = SessionLocal()
    try:
        report = compute_quality_report(db)
        return {"status": "completed", **report}
    finally:
        db.close()
```

- [ ] **Step 3: 创建 app/services/governance/__init__.py**

```python
from app.services.governance.engine import (
    execute_governance_pipeline,
    compute_quality_report,
    record_lineage,
)
```

- [ ] **Step 4: Commit**

```bash
git add app/services/governance/ app/tasks/governance.py
git commit -m "feat: implement governance engine with 4-layer pipeline"
```

---

## Phase 6: 分析引擎（核心维度 ①-④）

### Task 6.1: 情感分析 + 关键词提取 + 趋势分析 + 用户画像

**Files:**
- Create: `app/services/analysis/__init__.py`
- Create: `app/services/analysis/sentiment.py`
- Create: `app/services/analysis/keywords.py`
- Create: `app/services/analysis/trend.py`
- Create: `app/services/analysis/user_profile.py`

- [ ] **Step 1: 创建 app/services/analysis/sentiment.py**

```python
from datetime import datetime

from snownlp import SnowNLP
from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.analysis import AnalysisResult


def analyze_sentiment(db: Session, video_bvid: str | None = None) -> dict:
    query = db.query(Comment)
    if video_bvid:
        query = query.filter(Comment.video_bvid == video_bvid)
    comments = query.all()

    positive = 0
    neutral = 0
    negative = 0
    trend_data: list[dict] = []

    for comment in comments:
        content = comment.content or ""
        if not content.strip():
            neutral += 1
            continue
        try:
            score = SnowNLP(content).sentiments
        except Exception:
            score = 0.5

        label = "positive" if score > 0.6 else ("negative" if score < 0.4 else "neutral")
        if label == "positive":
            positive += 1
        elif label == "negative":
            negative += 1
        else:
            neutral += 1

        if comment.pub_time:
            trend_data.append({
                "time": str(comment.pub_time)[:10],
                "sentiment": score,
                "label": label,
            })

    total = len(comments)
    result = {
        "positive_ratio": round(positive / max(total, 1), 4),
        "neutral_ratio": round(neutral / max(total, 1), 4),
        "negative_ratio": round(negative / max(total, 1), 4),
        "total_samples": total,
        "trend_data": trend_data,
        "analyzed_at": datetime.now().isoformat(),
    }

    analysis_record = AnalysisResult(
        analysis_type="sentiment",
        ref_type="video" if video_bvid else "global",
        ref_id=video_bvid or "global",
        result_data=result,
    )
    db.add(analysis_record)
    db.commit()
    return result
```

- [ ] **Step 2: 创建 app/services/analysis/keywords.py**

```python
from datetime import datetime
from collections import Counter

import jieba
from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.analysis import AnalysisResult

STOP_WORDS = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这"}


def extract_keywords(db: Session, video_bvid: str | None = None, top_n: int = 50) -> dict:
    query = db.query(Comment)
    if video_bvid:
        query = query.filter(Comment.video_bvid == video_bvid)
    comments = query.all()

    all_words: list[str] = []
    for comment in comments:
        content = comment.content or ""
        words = jieba.lcut(content)
        for w in words:
            w = w.strip()
            if len(w) >= 2 and w not in STOP_WORDS:
                all_words.append(w)

    counter = Counter(all_words)
    top_keywords = counter.most_common(top_n)
    keywords = [{"word": w, "count": c} for w, c in top_keywords]

    result = {
        "keywords": keywords,
        "total_terms": len(all_words),
        "analyzed_at": datetime.now().isoformat(),
    }

    analysis_record = AnalysisResult(
        analysis_type="keywords",
        ref_type="video" if video_bvid else "global",
        ref_id=video_bvid or "global",
        result_data=result,
    )
    db.add(analysis_record)
    db.commit()
    return result
```

- [ ] **Step 3: 创建 app/services/analysis/trend.py**

```python
from datetime import datetime
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.comment import Comment
from app.models.analysis import AnalysisResult


def analyze_trend(db: Session, keyword_id: int | None = None) -> dict:
    query = db.query(
        func.date(Comment.pub_time).label("date"),
        func.count(Comment.id).label("count"),
    )
    results = query.group_by(func.date(Comment.pub_time)).order_by("date").all()

    time_series = [{"date": str(r.date), "count": r.count} for r in results]

    peak_points: list[dict] = []
    if len(time_series) >= 3:
        for i in range(len(time_series)):
            is_peak = True
            if i > 0 and time_series[i]["count"] <= time_series[i - 1]["count"]:
                is_peak = False
            if i < len(time_series) - 1 and time_series[i]["count"] <= time_series[i + 1]["count"]:
                is_peak = False
            if is_peak and time_series[i]["count"] > 0:
                peak_points.append(time_series[i])

    result = {
        "time_series": time_series,
        "peak_points": peak_points,
        "analyzed_at": datetime.now().isoformat(),
    }

    analysis_record = AnalysisResult(
        analysis_type="trend",
        ref_type="keyword",
        ref_id=str(keyword_id) if keyword_id else "global",
        result_data=result,
    )
    db.add(analysis_record)
    db.commit()
    return result
```

- [ ] **Step 4: 创建 app/services/analysis/user_profile.py**

```python
from datetime import datetime
from collections import Counter

from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.analysis import AnalysisResult


def analyze_user_profile(db: Session, video_bvid: str | None = None) -> dict:
    query = db.query(Comment)
    if video_bvid:
        query = query.filter(Comment.video_bvid == video_bvid)
    comments = query.all()

    hour_counter: Counter[int] = Counter()
    user_activity: dict[str, dict] = {}

    for comment in comments:
        if comment.pub_time:
            try:
                hour = int(str(comment.pub_time).split(" ")[1].split(":")[0])
                hour_counter[hour] += 1
            except (ValueError, IndexError):
                pass

        mid = comment.user_mid
        if mid not in user_activity:
            user_activity[mid] = {"comment_count": 0, "avg_likes": 0, "total_likes": 0}
        user_activity[mid]["comment_count"] += 1
        user_activity[mid]["total_likes"] += comment.like_count or 0

    for mid in user_activity:
        user_activity[mid]["avg_likes"] = (
            user_activity[mid]["total_likes"] / max(user_activity[mid]["comment_count"], 1)
        )

    active_hours = [{"hour": h, "count": c} for h, c in sorted(hour_counter.items())]

    result = {
        "active_hours": active_hours,
        "total_users": len(user_activity),
        "top_active_users_count": sum(1 for u in user_activity.values() if u["comment_count"] > 5),
        "analyzed_at": datetime.now().isoformat(),
    }

    analysis_record = AnalysisResult(
        analysis_type="user_profile",
        ref_type="video" if video_bvid else "global",
        ref_id=video_bvid or "global",
        result_data=result,
    )
    db.add(analysis_record)
    db.commit()
    return result
```

- [ ] **Step 5: 创建 app/services/analysis/__init__.py**

```python
from app.services.analysis.sentiment import analyze_sentiment
from app.services.analysis.keywords import extract_keywords
from app.services.analysis.trend import analyze_trend
from app.services.analysis.user_profile import analyze_user_profile
```

- [ ] **Step 6: 更新分析 Celery 任务 app/tasks/analysis.py**

```python
from app.database import SessionLocal
from app.services.analysis.sentiment import analyze_sentiment
from app.services.analysis.keywords import extract_keywords
from app.services.analysis.trend import analyze_trend
from app.services.analysis.user_profile import analyze_user_profile
from app.tasks import celery_app


@celery_app.task(bind=True, name="run_sentiment_analysis")
def run_sentiment_analysis(self, video_bvid: str | None = None):
    db = SessionLocal()
    try:
        result = analyze_sentiment(db, video_bvid)
        return {"status": "completed", "video_bvid": video_bvid, "samples": result["total_samples"]}
    finally:
        db.close()


@celery_app.task(bind=True, name="run_keyword_extraction")
def run_keyword_extraction(self, video_bvid: str | None = None):
    db = SessionLocal()
    try:
        result = extract_keywords(db, video_bvid)
        return {"status": "completed", "keywords_count": len(result["keywords"])}
    finally:
        db.close()


@celery_app.task(bind=True, name="run_trend_analysis")
def run_trend_analysis(self, keyword_id: int | None = None):
    db = SessionLocal()
    try:
        result = analyze_trend(db, keyword_id)
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


@celery_app.task(bind=True, name="run_full_analysis")
def run_full_analysis(self, video_bvid: str | None = None):
    results = {}
    results["sentiment"] = run_sentiment_analysis(video_bvid)
    results["keywords"] = run_keyword_extraction(video_bvid)
    results["trend"] = run_trend_analysis()
    results["user_profile"] = run_user_profile_analysis(video_bvid)
    return {"status": "completed", "results": results}
```

- [ ] **Step 7: Commit**

```bash
git add app/services/analysis/ app/tasks/analysis.py
git commit -m "feat: implement core analysis engines (sentiment, keywords, trend, user profile)"
```

---

## 开发顺序总览

| Phase | 内容 | 状态 |
|-------|------|------|
| **Phase 1** | 项目骨架（配置、数据库、模型、Schemas、API路由、main.py） | 计划已就绪 |
| **Phase 2** | Celery 异步任务基础 | 计划已就绪 |
| **Phase 3** | Web 前端骨架（页面路由、模板、静态文件） | 计划已就绪 |
| **Phase 4** | 爬虫服务实现（B站 API 封装 + 爬虫任务） | 计划已就绪 |
| **Phase 5** | 治理引擎（四层治理 + Pipeline） | 计划已就绪 |
| **Phase 6** | 分析引擎 ①-④（情感/关键词/趋势/用户画像） | 计划已就绪 |
| Phase 7 | 分析引擎 ⑤-⑧（OCR/弹幕密度/聚类/网络） | 后续补充 |
| Phase 8 | 数据血缘可视化 + 前端数据对接 | 后续补充 |
| Phase 9 | 导出功能完善 + 测试 + 演示数据 | 后续补充 |