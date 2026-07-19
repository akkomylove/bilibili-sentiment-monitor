# B 站 AI 投资领域舆情聚合工具

> 聚焦半导体 / 光通信 / 光芯片三大板块的 B 站舆情 + 行情对齐分析平台  
> 24 个监控关键词 · 手动触发采集 · 7 维度可视化简报 · PPT 翻页报告

## 核心能力

- **舆情采集**：基于 B 站公开 API 抓取视频与评论，单关键词采集上限 20 个视频，每视频 Top 20 高赞评论及楼中楼回复，按 `bvid`/`rpid` 去重
- **情感分析**：自建投资情感词典（看多/看空词库）+ SnowNLP 双层判定，引入点赞数对数加权提升高赞评论影响力
- **行情对齐**：对接 AKShare 新浪行情源，拉取全 A 实时价并过滤 12 家重点公司，本地 JSON 缓存（每日落盘，命中即读不走网络）
- **可视化简报**：7 维度报告（板块情感饼图 / 评论时间分布 / 风险机会词信号 / 舆情-行情对齐），支持今日/7天/30天/90天/自定义时间区间

## 架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Bilibili 公开 API                            │
│                  (search / video detail / reply)                    │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ httpx
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Celery Worker (solo pool, concurrency=1)                           │
│  [1] crawl_by_keyword     [2] run_full_analysis (3 子任务并行)       │
│      ↓ 写 MySQL                ↓ 读 MySQL → analysis_results(JSON)  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FastAPI (uvicorn, port 8010)                                       │
│  [/api/v1/...]  JSON API    [/daily-brief] 单日简报 HTML              │
│  [/report]      PPT 翻页报告  [/monitor] 关键词管理 HTML               │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────┐ ┌──────────────────┐ ┌────────────────────────────┐
│ MySQL 8.0       │ │ Redis 7          │ │ AKShare 新浪行情             │
│ 5 张表 (utf8mb4) │ │ Celery broker    │ │ + 本地 JSON 缓存             │
└─────────────────┘ └──────────────────┘ └────────────────────────────┘
```

## 技术栈

| 类别 | 选型 |
|------|------|
| Web 框架 | FastAPI + uvicorn |
| ORM | SQLAlchemy 2.0 |
| 数据库 | MySQL 8.0 |
| 任务队列 | Celery 5.3 + Redis 7 |
| 文本分析 | jieba + SnowNLP + 自建投资情感词典 |
| 行情数据 | AKShare 1.13（新浪源） |
| 前端 | Jinja2 模板 + ECharts |
| 容器化 | docker-compose（MySQL + Redis） |

## 快速开始

```bash
# 1. 克隆
git clone https://github.com/akkomylove/bilibili-sentiment-monitor.git
cd bilibili-sentiment-monitor

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 按需修改 MySQL / Redis / B 站 Cookie

# 4. 一键启动（拉容器 + 起服务 + 起 Worker）
start.bat
# 浏览器自动打开 http://localhost:8010
```

## 项目结构

```text
bilibili-sentiment-monitor/
├── app/
│   ├── api/                    # REST 端点（monitor/videos/comments/analysis）
│   ├── web/                    # Jinja2 前端页面
│   ├── services/               # 业务服务（爬虫/分析/行情/摘要）
│   ├── tasks/                  # Celery 异步任务
│   ├── models/                 # SQLAlchemy ORM（5 张表）
│   └── schemas/                # Pydantic 数据校验
├── config/
│   └── sectors.yaml            # 监控板块/关键词/抓取参数
├── tests/                      # pytest 单元测试
├── docs/                       # 设计文档/ADR/实施计划
├── docker-compose.yml          # MySQL + Redis 一键启动
├── .env.example                # 环境变量模板
├── requirements.txt
└── start.bat                   # Windows 一键启动
```

## 文档

| 文档 | 用途 |
|------|------|
| [docs/README.md](docs/README.md) | 文档目录索引 |
| [docs/adr/](docs/adr/) | 架构决策记录 |
| [docs/superpowers/specs/](docs/superpowers/specs/) | 设计与规约 |

完整 API 文档启动后访问 `http://localhost:8010/docs`。

## License

本仓库尚未指定 License（默认保留所有权利）。如需公开使用/分发，请先联系作者。