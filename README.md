# B站舆情监控与分析平台

## 项目结构
```
app
├── __init__.py
├── api
│   ├── __init__.py
│   ├── analysis.py
│   ├── comments.py
│   ├── export.py
│   ├── governance.py
│   ├── monitor.py
│   └── videos.py
├── config.py
├── database.py
├── dependencies.py
├── main.py
├── models
│   ├── __init__.py
│   ├── analysis.py
│   ├── base.py
│   ├── comment.py
│   ├── danmaku.py
│   ├── governance.py
│   ├── monitor.py
│   └── video.py
├── schemas
│   ├── __init__.py
│   ├── analysis.py
│   ├── comment.py
│   ├── common.py
│   ├── governance.py
│   ├── monitor.py
│   └── video.py
├── services
│   ├── analysis
│   │   ├── __init__.py
│   │   ├── danmaku_density.py
│   │   ├── image_ocr.py
│   │   ├── keywords.py
│   │   ├── network.py
│   │   ├── sentiment.py
│   │   ├── topic_cluster.py
│   │   ├── trend.py
│   │   └── user_profile.py
│   ├── crawler
│   │   ├── bilibili.py
│   │   └── danmaku_proto.py
│   └── governance
│       ├── __init__.py
│       └── engine.py
├── tasks
│   ├── __init__.py
│   ├── analysis.py
│   ├── crawl.py
│   └── governance.py
└── web
    ├── __init__.py
    ├── routes.py
    ├── static
    │   └── css
    │       └── style.css
    └── templates
        ├── base.html
        ├── dashboard.html
        ├── governance.html
        ├── report.html
        ├── video_detail.html
        └── videos.html
scripts
└── init_db.py
tests
├── conftest.py
├── services
│   ├── analysis
│   │   ├── test_keywords.py
│   │   ├── test_sentiment.py
│   │   └── test_trend.py
│   ├── crawler
│   │   └── test_bilibili.py
│   └── governance
│       └── test_engine.py

14 directories, 54 files
```

## 环境依赖
- Python 3.10+
- MySQL 8.0+
- Redis 6.0+

## 安装依赖
```bash
pip install -r requirements.txt
```

## 快速启动
```bash
# 1. 复制环境变量模板
cp .env.example .env

# 2. 编辑 .env 配置数据库和Redis
vim .env

# 3. 初始化数据库
python scripts/init_db.py

# 4. 启动后端服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 5. 启动Celery任务队列（另开终端）
python -m celery -A app.tasks worker --loglevel=info --concurrency=2

# 6. 启动Celery Beat定时调度（另开终端）
python -m celery -A app.tasks beat --loglevel=info
```

## 代码规范检查
```bash
# 代码风格检查
ruff check app/ tests/

# 代码风格自动修复
ruff check app/ tests/ --fix

# 类型检查
mypy app/
```

## 运行测试
```bash
pytest tests/ -v
```

## 访问地址
- 前端仪表盘: http://localhost:8000/dashboard
- API文档: http://localhost:8000/docs
- 管理后台: http://localhost:8000/governance

## 核心功能
- 视频/评论/弹幕数据采集（支持XML和Protobuf弹幕API）
- 情感分析、关键词提取、话题聚类、弹幕密度分析
- 数据治理流水线（去重、清洗、脱敏、格式校验）
- 数据血缘追踪与质量报告
- 报告导出（CSV/JSON/摘要）
- Celery Beat 定时自动采集与分析

## 许可证
MIT
