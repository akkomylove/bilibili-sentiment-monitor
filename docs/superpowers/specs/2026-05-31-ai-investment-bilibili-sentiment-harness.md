# AI 投资 B 站舆情聚合工具 —— Harness 文档

> 描述项目**怎么跑、怎么测、怎么维护、怎么扩展**。新人接手时读完这份就能上手。

> 归档日期：2026-05-31
> 状态：操作手册（与代码同步）

---

---

## 1. 项目一句话定义

**为 AI 领域投资者打造的 B 站舆情聚合工具**：每天 9:00 自动抓取半导体/光通信/光芯片相关视频，提取评论情绪和关键词，生成一份"今日 AI 投资舆情简报"。

---

## 2. 配置说明

### 2.1 投资领域配置 `config/sectors.yaml`

```yaml
sectors:
  - name: "半导体"
    keywords: ["半导体", "芯片", "晶圆厂", "ASML", "中芯国际", "台积电", "GPU"]
    hot_threshold:
      min_play: 10000
      min_comment: 50
  - name: "光通信"
    keywords: ["光模块", "光通信", "CPO", "800G", "1.6T", "LPO", "硅光"]
    hot_threshold:
      min_play: 5000
      min_comment: 30
  - name: "光芯片"
    keywords: ["光芯片", "激光器", "DFB", "EML", "VCSEL", "探测器"]
    hot_threshold:
      min_play: 5000
      min_comment: 30

crawl:
  max_videos_per_keyword: 10   # 每个关键词最多抓多少视频
  max_comments_per_video: 100  # 每个视频最多取多少评论
  reply_top_percent: 10        # 取回复的前 10%（按点赞数）
  schedule: "0 9 * * *"        # 每天 9:00 抓取
```

**修改后无需重启服务**（YAML 在 Celery 任务执行时加载）。

### 2.2 环境变量 `.env`

```ini
# MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=ai_invest_sentiment

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# B 站认证（重要！不配会被反爬拦截）
BILIBILI_COOKIE=SESSDATA=xxx; bili_jct=xxx

# App
APP_DEBUG=true
APP_PORT=8010
```

> **注意**：本项目端口已统一为 **8010**（`start.bat` 启动脚本默认端口）。
> 原文档中的 8000 端口为旧版默认值。

### 2.2.1 B 站 Wbi 签名（2024 年后接口必备）

```ini
# Wbi 签名密钥（从 B 站 nav 接口动态获取，部分接口需要）
BILIBILI_WBI_IMG_URL=https://i0.hdslb.com/bfs/wbi/xxx.png
BILIBILI_WBI_SUB_URL=https://i0.hdslb.com/bfs/wbi/xxx.png
```

> **2024 年起**，B 站搜索等接口强制要求 Wbi 签名。未配置会导致搜索返回空。
> 这两个字段由 `get_wbi_keys()` 在 `app/services/crawler/bilibili.py` 启动时自动从 B 站 nav 接口拉取，
> 无需手动配置，但需要登录态 Cookie 才能拿到。

### 2.3 投资词典 `app/services/analysis/investment_dict.py`

```python
SENTIMENT_BULLISH = ["突破", "创新高", "订单饱满", "供不应求", "扩产", "涨价", "看好", "加仓", "翻倍", "超预期", "满产"]
SENTIMENT_BEARISH = ["下跌", "破位", "砍单", "库存高企", "产能过剩", "看空", "减仓", "腰斩", "不及预期", "减产", "需求疲软"]

SECTOR_TERMS = {
    "半导体": ["晶圆", "制程", "光刻机", "EUV", "DUV", "良率", "封测", "Fab", "HBM", "先进封装", "CoWoS"],
    "光通信": ["光模块", "800G", "1.6T", "CPO", "LPO", "硅光", "EML", "DSP", "数通", "电信"],
    "光芯片": ["DFB", "EML", "VCSEL", "激光器", "探测器", "外延片", "InP", "GaAs"],
}
```

---

## 3. 启动指南

### 3.1 第一次启动

```bash
# 1. 安装依赖
pip install fastapi uvicorn sqlalchemy pymysql redis celery httpx pydantic pydantic-settings jieba snownlp pyyaml pytest

# 2. 初始化数据库
python scripts/init_db.py

# 3. 启动 FastAPI（终端 1）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8010

# 4. 启动 Celery Worker（终端 2）
python -m celery -A app.tasks worker --loglevel=info --concurrency=1 -P solo

# 5. 启动 Celery Beat（终端 3，仅当需要定时）
python -m celery -A app.tasks beat --loglevel=info

# 6. 访问简报页面
open http://localhost:8010/daily-brief
```

### 3.1.1 一键启动（推荐）

```bash
# Windows
start.bat
```

`start.bat` 会自动：
1. 杀掉占用 8010 端口的 Python 进程
2. 启动 Docker 容器（MySQL 3307、Redis 6380）
3. 启动 FastAPI、Celery Worker、Celery Beat 三个进程

### 3.2 手动触发一次采集

```python
from app.tasks.crawl import crawl_by_keyword
task = crawl_by_keyword.delay(keyword_id=1, keyword="半导体")
print(f"Task ID: {task.id}")
# 查 Celery Worker 日志看执行结果
```

### 3.3 重启策略

| 场景 | 操作 |
|------|------|
| 修改了 `config/sectors.yaml` | 无需重启，下次任务执行时生效 |
| 修改了 `app/services/analysis/*.py` | 重启 Celery Worker |
| 修改了 `app/api/*.py` 或 `app/web/templates/*.html` | uvicorn 已 reload 自动生效 |
| 修改了数据模型 | 重启所有 + 跑数据库迁移 |

---

## 4. 数据流（端到端）

```
┌──────────────────────────────────────────────────────────────┐
│ 1. 加载配置                                                  │
│    config/sectors.yaml → 板块关键词、阈值、抓取参数          │
└────────────────────────┬─────────────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. B 站搜索（按板块）                                        │
│    半导体: ["半导体", "芯片", "晶圆厂", ...]                  │
│    合并去重 → 热度过滤（min_play, min_comment）              │
└────────────────────────┬─────────────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. 采集每个视频                                              │
│    - 主页评论：取前 100 条                                    │
│    - 回复：按 like_count 排序，取前 10%                       │
│    - 总数上限 150 条/视频                                    │
└────────────────────────┬─────────────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. 入库 MySQL                                                │
│    videos 表: BV号、标题、播放、评论数、分区、发布时间        │
│    comments 表: rpid、bvid、user_mid、content、like_count、  │
│                parent_rpid、reply_count                      │
└────────────────────────┬─────────────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. 分析（同步或异步）                                        │
│    5.1 情感分析：投资词典增强 + SnowNLP 兜底                  │
│    5.2 关键词提取：jieba + 投资词典过滤                       │
│    5.3 简报生成：TemplateSummarizer.summarize(comments)      │
└────────────────────────┬─────────────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────────────┐
│ 6. 简报展示                                                  │
│    访问 /daily-brief → 看到情绪饼图、Top 视频、关键词汇总    │
└──────────────────────────────────────────────────────────────┘
```

---

## 5. 测试策略

### 5.1 反馈循环优先级

| 循环 | 时长 | 命令 |
|------|------|------|
| 端到端管道测试 | 5 秒 | `pytest tests/test_pipeline.py -v` |
| 单元测试 | 1 秒 | `pytest tests/unit/ -v` |
| 单视频采集 | 30 秒 | 见 §5.3 |
| 真实数据验证 | 1 天 | 见 §5.4 |

**任何改动都必须先过 5 秒循环**。

### 5.2 端到端测试

```python
# tests/test_pipeline.py
import json
from app.services.analysis.sentiment import analyze_sentiment
from app.services.analysis.keywords import extract_keywords
from app.services.summarizer.template import TemplateSummarizer

def test_daily_brief_pipeline():
    with open("tests/fixtures/sample_comments.json") as f:
        comments = json.load(f)

    sentiment = analyze_sentiment(comments)
    keywords = extract_keywords(comments, top_n=10)
    summary = TemplateSummarizer().summarize(comments)

    assert sentiment["positive"] + sentiment["negative"] + sentiment["neutral"] == 1.0
    assert len(keywords["keywords"]) > 0
    assert len(summary) > 50  # 至少 50 个字
```

### 5.3 单视频采集测试

```bash
python -c "
from app.services.crawler.bilibili import BilibiliAPI
api = BilibiliAPI(cookie='your_cookie')
comments = api.get_all_comments('BV1xx411c7mD', max_pages=1, page_size=100)
print(f'Got {len(comments)} comments')
print(comments[0])
"
```

### 5.4 真实数据验证

每周末人工对照：
- 取该周 3 天的简报
- 对照当天股市各板块涨跌幅
- 评估简报与实际情绪的吻合度
- 调优 `investment_dict.py`

---

## 6. 监控与运维

### 6.1 日常检查清单

```bash
# 1. 数据库连接
mysql -h localhost -u root -p ai_invest_sentiment -e "SELECT COUNT(*) FROM videos; SELECT COUNT(*) FROM comments;"

# 2. Celery 队列
python -c "from app.tasks import celery_app; print(celery_app.control.inspect().active())"

# 3. 今日采集状态
python -c "from app.database import SessionLocal; from app.models.video import Video; from datetime import datetime, timedelta; db=SessionLocal(); today=datetime.now().date(); n=db.query(Video).filter(Video.created_at >= today).count(); print(f'Today: {n} videos')"
```

### 6.2 常见问题

| 现象 | 原因 | 解决 |
|------|------|------|
| 采集返回 0 视频 | B 站反爬/Cookie 失效 | 更新 `.env` 里的 `BILIBILI_COOKIE` |
| 简报页面空白 | 数据库无今日数据 | 手动触发一次 `crawl_by_keyword` |
| 情感分析全为中性 | 词典没匹配上 | 在 `sample_comments.json` 验证词表覆盖 |
| Celery 任务不执行 | Redis 没启动 | `redis-cli ping` 应返回 PONG |

### 6.3 数据归档

每月初运行：
```sql
-- 归档 90 天前的评论
DELETE FROM comments WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY);
-- 视频保留（用于历史回溯）
```

---

## 7. 扩展点（已预留接口）

### 7.0 接口占位状态（截至 2026-05-31）

下列接口目录在当前代码中**仅有 README/骨架**，实际实现留待切片 5：

| 目录 | 状态 | 后续实现 |
|------|------|----------|
| `app/services/summarizer/base.py` | 占位 | `class Summarizer(ABC)` |
| `app/services/summarizer/template.py` | 占位 | 模板实现：基于情感占比 + Top 关键词拼接 |
| `app/services/market/base.py` | 占位 | `class MarketData(ABC)` |
| `app/services/market/mock.py` | 占位 | 返回固定 mock 数据 |

> 当前不要在生产代码中调用这些接口，避免引入未实现依赖。

### 7.0.1 评论 parent_rpid 字段

`Comment` 模型自 2026-05-31 起新增 `parent_rpid` 字段（`BigInteger, default=0, index=True`），
记录该评论的父评论 rpid。**核心用途**：

- 互动网络分析：通过 `parent_rpid` 直接定位父子评论关系，构建用户互动边
  （之前的版本用 `@昵称` 字符串模糊匹配，由于 `user_mid` 是哈希串，永远匹配不上）
- 折叠回复解析：折叠回复的 `parent_rpid` 自动指向顶级评论

**当前用户互动网络边公式**：
```
影响力 = 总点赞 × 1.0 + 收到回复 × 3.0 + 评论数 × 0.5 + 平均点赞 × 2.0
```

### 7.1 接入 LLM 摘要

替换 `TemplateSummarizer`：

```python
# app/services/summarizer/deepseek.py
from app.services.summarizer.base import Summarizer

class DeepSeekSummarizer(Summarizer):
    def summarize(self, comments: list[dict]) -> str:
        import httpx
        prompt = f"以下是今日 AI 投资相关 B 站评论，请总结 5 句话：\n\n{self._format(comments)}"
        resp = httpx.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        return resp.json()["choices"][0]["message"]["content"]
```

修改 `daily_brief.html` 注入方式：
```python
# app/web/routes.py
from app.services.summarizer.template import TemplateSummarizer
# 未来切换为：from app.services.summarizer.deepseek import DeepSeekSummarizer
summarizer = TemplateSummarizer()  # 改这一行即可
```

### 7.2 接入真实股价数据

替换 `MockMarketData`：

```python
# app/services/market/tushare.py
from app.services.market.base import MarketData

class TushareMarketData(MarketData):
    def get_sector_perf(self, date: str) -> dict:
        import tushare as ts
        pro = ts.pro_api(settings.tushare_token)
        df = pro.index_daily(trade_date=date)
        return dict(zip(df['name'], df['pct_chg']))
```

### 7.3 新增板块

修改 `config/sectors.yaml` 即可，无需改代码：
```yaml
sectors:
  - name: "新增板块名"
    keywords: ["关键词1", "关键词2"]
    hot_threshold: { min_play: 5000, min_comment: 30 }
```

### 7.4 新增分析维度

```python
# app/services/analysis/my_new_dimension.py
def analyze_my_new_dimension(comments: list[dict]) -> dict:
    ...
```

然后在 `app/api/analysis.py` 注册新端点。

---

## 8. 项目边界（明确不做）

为避免范围蔓延，明确以下**不做**的事项：

- ❌ 多用户系统 / 登录 / 权限
- ❌ 移动端 UI
- ❌ 实时推送（WebSocket）
- ❌ 数据导出 CSV/Excel（暂不需要）
- ❌ 弹幕抓取
- ❌ 互动网络分析
- ❌ 用户画像
- ❌ 图片评论 OCR
- ❌ 自动化部署（CI/CD）
- ❌ Docker 化

任何新需求，先问："这对我做 AI 投资决策有用吗？"——无用即不做。

---

## 9. 故障排查决策树

```
简报页面空白？
├─ 数据库有数据吗？
│  ├─ 没有 → 手动跑一次采集
│  └─ 有 → 检查 API 返回
│
采集失败？
├─ HTTP 412 / -352 风控？→ 更新 Cookie
├─ 搜索返回 0 结果？→ 关键词是否在 config/sectors.yaml
└─ Celery Worker 没启动？→ 启动 worker
```

---

## 10. 联系方式与变更记录

- **项目版本**：v2.0-investment-tool
- **创建日期**：2026-05-31
- **核心变更**：从通用舆情平台重构为 AI 投资领域聚合工具
- **保留内容**：B 站采集、MySQL、FastAPI、Jinja2 模板
- **删除内容**：数据治理、互动网络、用户画像、图片 OCR、治理页面、报告导出
- **新增内容**：投资词典、TemplateSummarizer、MockMarketData、daily_brief 单页
