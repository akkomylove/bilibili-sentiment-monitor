# B 站 AI 投资领域舆情聚合工具

> 一个聚焦半导体 / 光通信 / 光芯片三大板块的 B 站舆情 + 行情对齐分析平台

## 项目概述

本项目从 B 站抓取 AI 投资领域的视频与高赞评论，对评论做关键词提取、情感分析与时间趋势分析，并结合 A 股板块行情数据（AKShare 实时价），产出可滚动翻页的舆情周报与单日简报。

**核心定位**

- **垂直领域**：AI 投资三大板块（半导体 / 光通信 / 光芯片），共 24 个监控关键词
- **数据源**：B 站（视频元数据 + 评论 + 弹幕）+ 新浪财经行情（AKShare）
- **产出形态**：JSON API（程序消费） + 单页日报 / PPT 翻页周报（人工阅读）
- **运行模式**：手动触发 + Celery worker 异步执行（v2 暂不启用 Beat 定时调度）

**v2.1 相比 v1 的变化**

| 维度 | v1.0 | v2.1 |
|---|---|---|
| 分析维度 | 八维（治理/网络/聚类/用户画像...） | 三维（关键词 / 情感 / 趋势） + 行情对齐 |
| 目标场景 | 通用舆情监控 | AI 投资领域专项 |
| 前端页面 | dashboard / governance / hot_search 多页 | 单页 daily-brief + 报告页 report |
| 调度模式 | Celery Beat 5/30/60 分钟循环 | 手动触发（前端按钮 + API） |
| 板块数据 | 通用 | 半导体 / 光通信 / 光芯片 自定义板块→股票映射 |
| 报告展示 | 静态 JSON 导出 | PPT 翻页式 HTML 报告 |

---

## 架构与数据流

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Bilibili 公开 API                            │
│                  (search / video detail / reply)                    │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ httpx (无 cookie / 有 cookie 双模式)
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Celery Worker (solo pool, concurrency=1)                           │
│  app/tasks/crawl.py  app/tasks/analysis.py                          │
│                                                                     │
│  [1] crawl_by_keyword     [2] run_full_analysis                      │
│      ↓ 写 MySQL                ↓ 读 MySQL                           │
│      videos/comments          keywords/sentiment/trend              │
│      danmaku(可选)            → analysis_results(JSON)              │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FastAPI (uvicorn, port 8010)                                       │
│  app/api/{monitor,videos,comments,analysis}.py  +  app/web/routes.py│
│                                                                     │
│  [/api/v1/...]  JSON (供程序消费)                                   │
│  [/daily-brief] 单日简报 HTML                                       │
│  [/report]      PPT 翻页报告 HTML                                   │
│  [/monitor]     关键词管理 HTML                                      │
│  [/videos]      视频列表 HTML                                       │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ 读
                           ▼
┌─────────────────┐ ┌──────────────────┐ ┌────────────────────────┐
│ MySQL 8.0       │ │ Redis 7          │ │ AKShare 新浪行情        │
│ (utf8mb4)       │ │ Celery broker    │ │ stock_zh_a_spot()      │
│ port 3307       │ │ port 6380        │ │ + 本地缓存              │
│ 5 张表          │ │                  │ │ data/market_cache/     │
└─────────────────┘ └──────────────────┘ └────────────────────────┘
```

**关键数据流**

1. 用户在前端 `/monitor` 页点击"全量采集" → `POST /api/v1/monitor/keywords/{id}/trigger`
2. API 立即返回 task_id，后台通过 Celery 异步执行 `crawl_by_keyword`
3. Worker 调 B 站 API 拉视频/评论，按 `bvid`/`rpid` 去重，写入 `videos`/`comments`
4. 用户点击"分析" → `POST /api/v1/monitor/keywords/{id}/trigger-analysis`
5. Worker 跑 `run_full_analysis`（3 个 group 子任务并行），结果写入 `analysis_results`
6. 用户访问 `/daily-brief` 或 `/report` → 后端实时聚合 7 维度数据 → 渲染 HTML

---

## 技术栈

| 类别 | 选型 | 用途 |
|---|---|---|
| Web 框架 | FastAPI 0.110+ | REST API + 模板渲染 |
| ASGI | uvicorn[standard] | 启动服务 |
| ORM | SQLAlchemy 2.0+ | MySQL 访问 |
| 数据库 | MySQL 8.0 | 主存储（utf8mb4） |
| 任务队列 | Celery 5.3+ | 异步爬取与分析 |
| Broker | Redis 7 | Celery broker + result backend |
| 文本分析 | jieba + snownlp | 中文分词 + 情感极性 |
| 行情数据 | AKShare 1.13+ | A 股实时价（新浪源） |
| HTTP 客户端 | httpx | Bilibili API 调用 |
| 配置 | pydantic-settings | .env 加载 |
| 模板 | Jinja2 | HTML 渲染 |
| 容器化 | docker-compose | MySQL + Redis 一键起 |

完整依赖见 [requirements.txt](requirements.txt)。

---

## 目录结构

```
d:\bilibili-sentiment-monitor\
├── app/                        # 业务代码
│   ├── api/                    # REST 端点
│   │   ├── monitor.py          # 关键词管理 + 触发爬取/分析
│   │   ├── videos.py           # 视频列表/详情
│   │   ├── comments.py         # 评论列表
│   │   └── analysis.py         # 情感/关键词/趋势查询 + 简报/报告聚合
│   ├── web/                    # 前端 (Jinja2 模板)
│   │   ├── routes.py           # 页面路由：/daily-brief /report /monitor /videos
│   │   └── templates/          # 5 个 HTML 模板
│   ├── services/               # 业务服务
│   │   ├── crawler/            # B 站 API 封装
│   │   ├── analysis/           # 关键词提取 / 情感 / 趋势
│   │   ├── market/             # 行情数据（AKShare / Mock）
│   │   ├── summarizer/         # 模板化摘要生成
│   │   └── daily_brief.py      # 单页简报聚合入口
│   ├── tasks/                  # Celery 任务
│   │   ├── crawl.py            # crawl_by_keyword (主爬虫)
│   │   └── analysis.py         # run_full_analysis (3 子任务并行)
│   ├── models/                 # SQLAlchemy ORM (5 张表)
│   ├── schemas/                # Pydantic 数据校验
│   ├── config.py               # 全局配置 (Settings)
│   ├── database.py             # SQLAlchemy engine + session
│   ├── dependencies.py         # FastAPI Depends
│   └── main.py                 # FastAPI 入口
├── config/
│   └── sectors.yaml            # 监控板块/关键词/阈值/抓取参数
├── docs/                       # 设计/规约/执行计划
│   ├── adr/                    # 架构决策记录
│   ├── superpowers/plans/      # 实施计划
│   ├── superpowers/specs/      # 设计与规约
│   └── README.md               # 文档索引
├── tests/                      # pytest 单元测试
├── scripts/                    # 一次性诊断脚本
├── logs/                       # 运行时日志 (.gitignore)
├── data/market_cache/          # 行情缓存 (.gitignore)
├── .env.example                # 环境变量模板
├── .gitignore
├── docker-compose.yml          # MySQL + Redis 一键启动
├── requirements.txt
├── start.bat                   # Windows 一键启动（uvicorn + celery）
└── README.md
```

---

## 数据库 Schema

5 张表，全部 `utf8mb4`：

```sql
-- 监控关键词配置
monitor_keywords
  id PK
  keyword           varchar(200)   -- 搜索词
  partition_filter  varchar(200)   -- B站分区过滤
  crawl_interval    int            -- 抓取间隔（分钟，v2 不再使用）
  is_active         bool
  sort_order        varchar(20)    -- B站搜索排序：totalrank/pubdate/click
  last_crawled_at   datetime
  created_at        datetime
  updated_at        datetime

-- 视频
videos
  id PK
  bvid              varchar(20) UNIQUE  -- B站视频 ID
  title             varchar(500)
  description       text
  play_count        bigint
  danmaku_count     int
  comment_count     int
  pub_time          datetime
  partition_tag     varchar(100)
  keyword_id        FK→monitor_keywords(id) ON DELETE SET NULL
  created_at        datetime

-- 评论
comments
  id PK
  rpid              bigint UNIQUE       -- B站评论 ID
  video_bvid        FK→videos(bvid)
  user_mid          varchar(100)        -- B站 user hash (非真实 ID)
  raw_content       text
  content           text                -- 清洗后
  like_count        int
  reply_count       int
  has_image         bool
  image_urls        json
  pub_time          datetime
  parent_rpid       bigint (0=顶级评论)
  created_at        datetime

-- 弹幕（v2 已不再采集，保留表）
danmaku
  ...

-- 分析结果（所有类型共用一张表，result_data 是 JSON）
analysis_results
  id PK
  analysis_type     varchar(50)  -- keywords / sentiment / trend
  ref_type          varchar(50)  -- keyword / video / global
  ref_id            varchar(100) -- keyword_id 或 bvid 或 "global"
  result_data       json
  analyzed_at       datetime
```

**索引**

- `videos.bvid` UNIQUE
- `videos.keyword_id`（按关键词过滤）
- `comments.rpid` UNIQUE
- `comments.video_bvid`（按视频过滤）
- `comments.parent_rpid`（顶级评论 vs 回复）
- `analysis_results` 复合索引 `(analysis_type, ref_type, ref_id, analyzed_at)`

---

## API 概览

所有 API 前缀 `/api/v1`。完整 OpenAPI 文档：启动后访问 `http://localhost:8010/docs`。

### 监控配置

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/monitor/keywords?page&page_size` | 关键词列表（分页） |
| POST | `/monitor/keywords` | 新增关键词 |
| PUT | `/monitor/keywords/{id}` | 修改关键词配置 |
| DELETE | `/monitor/keywords/{id}` | 删除（自动解除视频外键） |
| GET | `/monitor/status` | 全部关键词的采集汇总 |
| GET | `/monitor/activities?limit` | 最近采集活动 |
| POST | `/monitor/keywords/{id}/trigger` | **手动触发爬取**（返回 task_id） |
| POST | `/monitor/keywords/{id}/trigger-analysis` | **手动触发分析**（返回 task_id） |

### 视频 / 评论

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/videos?page&page_size&keyword_id` | 视频列表 |
| GET | `/videos/{bvid}` | 视频详情 |
| GET | `/videos/{bvid}/comments?page` | 视频评论列表 |

### 分析结果

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/analysis/sentiment?keyword_id&video_bvid` | 最新情感分析 |
| GET | `/analysis/keywords?keyword_id&video_bvid` | 最新关键词提取 |
| GET | `/analysis/trend?keyword_id` | 趋势分析 |
| GET | `/analysis/brief?keyword_id&video_bvid` | 3-5 句中文简报文本 |

### 单页简报 / 报告

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/analysis/daily-brief?date&start_date&end_date&sector` | 单页简报 JSON（前端 `/daily-brief` 用） |
| GET | `/analysis/report-daily?date&start_date&end_date&sector` | 7 维度报告 JSON（前端 `/report` 用） |

**日期参数互斥规则**（简报/报告接口）

- `date=2026-06-09` → 单日（v1 旧行为）
- `start_date=2026-06-01&end_date=2026-06-09` → 区间
- 仅 `start_date` → start_date 至最新
- 仅 `end_date` → 最早至 end_date
- 全不传 → 不过滤，返回所有监控视频
- 单日模式下当天无数据 → 回退到最近 7 天

### 页面路由

| 路径 | 说明 |
|---|---|
| `/` | 重定向到 `/daily-brief` |
| `/daily-brief` | 单页简报（HTML） |
| `/report` | PPT 翻页式周报（HTML） |
| `/monitor` | 关键词管理 |
| `/videos` | 视频列表 |
| `/videos/{bvid}` | 视频详情 |

---

## 核心模块详解

### 1. 爬虫 `app/tasks/crawl.py`

**入口**：`crawl_by_keyword.delay(keyword_id, keyword, max_pages, max_videos_per_keyword, sort_order)`

**行为**：

1. 读 `config/sectors.yaml` 获取限速参数
2. 调 B 站 `search/type=video` 翻页，每页 20 个
3. 截断到 `max_videos_per_keyword=20`（用户硬性要求）
4. 对每个视频：调 `video/view` 拿详情 → 调 `reply` 拿评论 → 调 `danmaku.proto` 拿弹幕
5. 视频去重：已存在的 `bvid` **不跳过**，只更新 `play_count`/`comment_count`，并增量爬新评论（用 `rpid` 去重）
6. 实时打印进度到 Celery worker 窗口（`[CRAWL] [SEARCH] [VIDEO n/total]` 日志）

**限速策略**：

- `max_pages=3, max_videos_per_keyword=20` → 单关键词最多 60 个搜索结果 → 取 20
- 单次"全量采集"理论上限：24 关键词 × 20 视频 = 480 个视频
- B 站风控：高频（< 15 分钟）会触发 412 / cookie 失效，**生产环境建议 ≥ 1 小时**

### 2. 分析 `app/tasks/analysis.py`

**入口**：`run_full_analysis.delay(keyword_id=...)`

**行为**：用 `celery.group()` 并行跑 3 个子任务：

- `analyze_keywords`：jieba 分词 + 投资词典过滤 + 频次统计
- `analyze_sentiment`：snownlp + 投资领域情感词典修正（"利好/看多/梭哈" 等投资语境词）
- `analyze_trend`：按天/小时桶聚合评论时间分布

每个子任务写一行 `analysis_results`，`result_data` 是 JSON。

### 3. 单页简报 `app/services/daily_brief.py`

**入口**：`build_daily_brief(db, date_str, start_str, end_str, sector)`

**返回结构**：

```python
{
  "headline": "...",           # 1 句话整体描述
  "summary": {                 # TemplateSummarizer 输出
    "headline": "...",
    "key_insights": [...],     # 3 条要点
    "editor_takeaway": [...],  # 3-4 句模板化结论
  },
  "metrics": { ... },          # 视频数/评论数/情感分布
  "videos": [...],             # 视频列表（去重后）
  "keywords_top": [...],       # 高频词 Top 20
  "sector_focus": [            # 板块聚焦（v2.1 新增）
    {"sector": "光通信", "pct": 12.5, "companies": ["中际旭创", ...]}
  ],
  "market_snapshot": {         # 行情快照（v2.1 新增）
    "sectors": [...],
    "stocks": [...],
    "is_mock": False
  },
  "comment_time_distribution": [...],  # 时间分布
  "risk_opportunity_signals": [...],   # 风险/机会词
  "sector_sentiment_alignment": [...], # 舆情 vs 行情对齐
  "range_label": "本期",       # v2.1 动态
}
```

### 4. 行情数据 `app/services/market/`

**接口**：`MarketData`（base.py）

- `get_sector_perf(date_str) -> {sector: pct_chg}` 板块涨跌幅
- `get_stock_snapshot(codes) -> {code: {price, pct_chg, ...}}` 个股快照

**实现**：

- `AKShareMarketData`（akshare.py）— 真实数据
  - 数据流：本地缓存 → miss + 是今日 → 调 `ak.stock_zh_a_spot()` → 写本地
  - 板块→股票清单硬编码在 `_SECTOR_STOCKS`（半导体 4 / 光通信 4 / 光芯片 4）
  - **注意**：东财源（`stock_board_industry_*_em`）经常 `RemoteDisconnected`，故只用新浪源
- `MockMarketData`（mock.py）— 兜底，历史日期用 mock
- `get_market_data()` 工厂：返回 `AKShareMarketData()`

**缓存**：`data/market_cache/YYYY-MM-DD.json` 存每日 12 只重点公司实时价。

### 5. 摘要生成 `app/services/summarizer/template.py`

**接口**：`TemplateSummarizer.summarize(comments, range_label="本期")`

**输出**：`{headline, key_insights, editor_takeaway, sentiment_distribution, top_terms}`

**实现要点**：

- 整体态势（情感分布百分比）
- 最强板块（`sector_focus` 中涨幅最高）
- 热议词（关键词 Top 5）
- 拼接成 3-4 句中文模板化结论

---

## 开发环境

### 前置依赖

| 工具 | 版本 | 用途 |
|---|---|---|
| Python | 3.10+ | 运行时 |
| Docker Desktop | 最新 | MySQL + Redis 容器 |
| Windows | 10/11 | `start.bat` 适配 |

### 5 分钟启动

```bash
# 1. 克隆
git clone https://github.com/akkomylove/bilibili-sentiment-monitor.git
cd bilibili-sentiment-monitor

# 2. 安装依赖
pip install -r requirements.txt

# 3. 复制环境变量模板，按需修改
cp .env.example .env
# Windows: copy .env.example .env

# 4. 一键启动（拉 MySQL + Redis + 起 uvicorn + 起 Celery worker）
start.bat
```

启动后自动打开 `http://localhost:8010`，重定向到 `/daily-brief`。

### 手动启动（Linux / macOS）

```bash
docker compose up -d
# 等待 MySQL 就绪
python -m uvicorn app.main:app --host 0.0.0.0 --port 8010 &
celery -A app.tasks worker --loglevel=info --concurrency=1 -P solo
```

### 环境变量 `.env`

```ini
# MySQL（默认与 docker-compose.yml 一致）
MYSQL_HOST=localhost
MYSQL_PORT=3307
MYSQL_USER=root
MYSQL_PASSWORD=root123
MYSQL_DATABASE=bilibili_sentiment

# Redis
REDIS_HOST=localhost
REDIS_PORT=6380

# B 站（可选，匿名访问也能跑，但高频会被风控）
BILIBILI_COOKIE=SESSDATA=xxx; bili_jct=xxx
```

### 初始化数据库

v2.1 **不使用 Alembic**。所有表在首次启动时由 SQLAlchemy `Base.metadata.create_all()` 自动创建。

---

## 部署

### 生产环境清单

- [ ] 修改 `docker-compose.yml` 中的 `MYSQL_ROOT_PASSWORD`（不要用 `root123`）
- [ ] 设置强 `APP_SECRET_KEY`（替换 `change-me-in-production`）
- [ ] 反向代理（Nginx / Caddy）+ HTTPS
- [ ] Celery worker 用 supervisor / systemd 守护
- [ ] Celery Beat 按需启用（v2 暂未启用自动调度）
- [ ] 日志收集（`logs/uvicorn.out` / `logs/celery_worker.log`）
- [ ] 行情缓存定期重拉（每天 18:00 收盘后）

### Docker Compose 现状

仅 MySQL + Redis 容器。**FastAPI + Celery 通过 `start.bat` 启动**（Windows 优先）。

如需 Linux 部署，可把 uvicorn + celery 也打包成 Docker（不包含在本仓库）。

---

## 扩展指南

### 新增一个监控板块

1. 编辑 `config/sectors.yaml`，加 `sectors: - name: ... keywords: ...` 块
2. 编辑 `app/services/analysis/investment_dict.py`：
   - 加板块名到 `SECTOR_TERMS`
   - 加 `STOP_TERMS` 中需要过滤的噪声词
3. 编辑 `app/services/market/akshare.py`：
   - 在 `_SECTOR_STOCKS` 加板块对应股票清单
4. 重启 Celery worker（让新板块的词典/股票加载到内存）
5. 触发 `run_full_analysis` 让新板块出现在简报中

### 新增一个分析维度

参考 `app/services/analysis/keywords.py` / `sentiment_v2.py` / `trend.py` 的模式：

1. 在 `app/services/analysis/` 加新文件
2. 在 `app/tasks/analysis.py` 加新 Celery 任务
3. 在 `app/api/analysis.py` 加新查询端点
4. 在 `app/models/analysis.py` 不用改表（`result_data` 是 JSON 任意结构）
5. 在 `app/services/daily_brief.py` 的 `build_daily_brief()` 聚合新维度

### 切换行情数据源

实现 `app/services/market/base.py` 的 `MarketData` 接口，在 `app/services/market/__init__.py` 的工厂函数返回新实现即可。

---

## 已知限制

| 限制 | 原因 | 计划 |
|---|---|---|
| B 站风控：高频采集触发 412 | 公开 API 限速 | Beat 调度间隔 ≥ 1 小时 |
| AKShare 东财源 `RemoteDisconnected` | 第三方反爬 | 已切到新浪源；如失效需手写 HTTP 兜底 |
| 报告页 7 维度首屏渲染慢 | 30+ 视频聚合 SQL 走 `IN (...)` | 可加 `videos.pub_time` 索引 + 缓存 |
| `analysis_results.analyzed_at` 显示 8h 偏移 | DB naive timestamp | 改 tz-aware + UTC 转换 |
| Celery `group()` 父任务 result 一直 PENDING | 子任务已成功，result backend 不刷新 | 通过 DB 验证；用 chord 替代 |
| 无 Alembic 迁移 | 简化开发 | 改 schema 时手工 `DROP TABLE` 或写 SQL 脚本 |
| `daily_brief` 单日模式无数据时回退 7 天 | v1 旧行为 | v2.1 已支持显式 `start_date`/`end_date` 替代 |

---

## 文档

| 文档 | 用途 |
|---|---|
| [docs/README.md](docs/README.md) | 文档目录索引 |
| [docs/adr/0001-simplify-to-investment-tool.md](docs/adr/0001-simplify-to-investment-tool.md) | v1 → v2 演进动机 |
| [docs/superpowers/specs/2026-05-31-ai-investment-bilibili-sentiment-v2-design.md](docs/superpowers/specs/2026-05-31-ai-investment-bilibili-sentiment-v2-design.md) | v2 总体设计 |
| [docs/superpowers/specs/2026-05-31-ai-investment-bilibili-sentiment-harness.md](docs/superpowers/specs/2026-05-31-ai-investment-bilibili-sentiment-harness.md) | v2 操作手册 |
| [docs/superpowers/plans/2026-05-31-ai-investment-bilibili-sentiment-execution-plan.md](docs/superpowers/plans/2026-05-31-ai-investment-bilibili-sentiment-execution-plan.md) | 实施计划 |
| `docs/superpowers/specs/2026-05-29-*.md` | v1.0 毕设设计（**已废弃**） |

---

## 路线图

- [ ] 启用 Celery Beat 自动调度（每关键词独立 cron）
- [ ] Alembic 数据库迁移
- [ ] 行情数据每日 18:00 自动重拉缓存
- [ ] 报告页支持板块对比
- [ ] 接入 LLM 生成 `editor_takeaway`（替代当前模板化结论）
- [ ] 实时 WebSocket 推送采集进度

---

## 贡献

欢迎 PR。请确保：

1. 代码风格与现有模块一致（中文注释 + 英文变量名）
2. 关键函数有 docstring
3. 新增依赖加到 [requirements.txt](requirements.txt) 并加分组注释
4. 隐私：不要提交 `.env` / cookie / 真实密码（已在 `.gitignore` 兜底）
5. 大改前先开 Issue 讨论

---

## 隐私与安全

- **真实数据不入库**：B 站用户 hash 用 `user_mid` 字段，**不存储真实 UID**
- **Cookie 通过环境变量**：`BILIBILI_COOKIE` 从 `.env` 读取，`.env` 已在 `.gitignore`
- **MySQL 密码**：默认 `root123` 是 Docker 本地开发密码，**生产环境必须修改**
- **API Secret**：`APP_SECRET_KEY` 默认 `change-me-in-production`，**生产环境必须修改**

---

## License

本仓库尚未指定 License（默认保留所有权利）。如需公开使用/分发，请先联系作者。
