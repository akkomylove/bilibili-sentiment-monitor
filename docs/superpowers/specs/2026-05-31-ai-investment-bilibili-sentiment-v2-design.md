# AI 投资领域 B 站舆情聚合工具 —— 重新设计计划

> 目标：把"通用舆情监控平台"重构为"面向 AI 投资决策的轻量级舆情聚合工具"，砍掉无关功能，专注核心场景。
> 创建日期：2026-05-31
> 归档日期：2026-05-31
> 状态：设计稿（待实现）

---

## 代码状态对齐说明

本文档是面向**未来重构**的设计稿，与当前代码状态存在差异，实施前请关注以下差异点：

| 文档内容 | 当前实际状态 | 差异 |
|---------|------------|------|
| 端口 8000 | `start.bat` 已固定为 8010 | 实施时端口需统一为 8010 |
| 评论采集："前 100 热评 + 10% 回复" | `crawl_by_keyword` 已切换为 `get_top_comments_with_replies(max_top=100, reply_ratio=0.1)` | ✅ 与文档目标一致 |
| `Comment` 模型 | 已新增 `parent_rpid` 字段（v1 互动网络分析用） | 实施时可继续保留 |
| `app/services/summarizer/` | 尚未创建 | 切片 5 创建 |
| `app/services/market/` | 尚未创建 | 切片 5 创建 |
| `app/services/analysis/investment_dict.py` | 尚未创建 | 切片 1 创建 |
| `app/services/analysis/sentiment_v2.py` | 尚未创建 | 切片 1 创建 |
| `daily_brief.html` 单页 | 当前仍是 5 个页面 | 切片 3 改造 |
| `governance` 模块 | 已实现但文档建议删除 | 待评估 |
| `8 维分析` | 已实现但文档建议砍掉多个 | 待评估 |

---

## Summary

用户做 AI 领域投资（半导体/光通信/光芯片），日常需要在 B 站追踪大量博主视频和评论。当前项目是一个覆盖 8 维分析、4 层治理、5 个页面的通用型平台，**功能过度、实现不彻底、与真实需求脱节**。

本次重构的核心转向：
- **从"通用舆情平台" → "AI 投资舆情聚合工具"**
- **从"功能堆砌" → "解决一个具体问题"**
- **从"数据库存储 + 异步分析" → "轻量级 RSS 订阅 + 摘要展示"**
- **未来要预留大模型 API 和股价联动接口**，但本轮只搭骨架

---

## Current State Analysis

### 现状摸查（基于探索）

| 维度 | 现状 | 问题 |
|------|------|------|
| 信源 | 关键词搜索 + 任意视频 | 用户实际只关心 AI 投资相关博主/视频 |
| 数据规模 | 抓全部评论 + 全部弹幕 | 用户已经定义取舍：只取热门视频前 100 条评论 + 前 10% 回复 |
| 分析维度 | 8 维（情感/关键词/趋势/用户画像/OCR/弹幕密度/聚类/网络） | 用户实测：词云和聚类效果不佳，表格不清晰 |
| 数据治理 | 4 层流水线（接入/清洗/脱敏/质量+血缘） | 投入产出比低，对个人工具来说过重 |
| 前端 | 5 个页面（仪表盘/视频列表/视频详情/治理/报告） | 后续要删掉全站热点、治理页面 |
| 测试 | 一次性跑过一天数据，发现效果偏差 | 需要缩短反馈循环，建立回归验证 |
| 接口扩展性 | 任务触发、CSV/JSON 导出 | 后续要加 LLM 总结、股价联动 |

### 核心问题诊断

1. **没有"用户视角"**：现在的设计是"我能爬什么数据"，不是"用户做投资决策时需要看什么"
2. **过早工程化**：在没验证效果之前就堆了完整数据治理和 8 维分析
3. **反馈循环太长**：跑一天数据才能看一次效果，词云/聚类调优没有迭代节奏
4. **数据规模失控**：项目要"能用"，不是要做 SaaS 平台

---

## Proposed Changes

### 总体重构策略

**砍**：数据治理 4 层、8 维分析、互动网络、用户画像、图片 OCR、治理页面、报告导出页面、Protobuf 弹幕解析、全站热点、复杂血缘图

**留/简化**：B 站采集（简化版）、情感分析（简化为标签）、关键词提取、话题聚类（简化为手工关键词）、ECharts 可视化

**加（未来预留接口）**：
- `Summarizer` 抽象接口：先返回固定模板文本，未来接 DeepSeek/通义千问
- `MarketData` 抽象接口：先返回 mock 数据，未来接 Tushare/AKShare

### 新数据流（简化版）

```
关键词配置 (config/sectors.yaml)
        │
        ▼
[每日 9:00 定时]
   B站搜索 "光模块" "半导体" "CPO" 等
        │
        ▼
   去重 + 热度过滤（播放>1万 或 评论>50）
        │
        ▼
   对每个视频：取前 100 条评论 + 按 like_count 取前 10% 回复
        │
        ▼
   入库 (videos / comments)
        │
        ▼
[同步处理]
   评论情感打分 (SnowNLP / 后续 LLM)
        │
        ▼
   关键词聚合 (jieba + 投资领域词典)
        │
        ▼
   简报生成 (Summarizer 接口)
        │
        ▼
[Web 单页展示]
   当日 AI 投资舆情简报
```

---

### 文件级改动清单

#### 删除（不再需要）

| 路径 | 原因 |
|------|------|
| `app/services/governance/` | 4 层治理对本场景过重 |
| `app/services/analysis/topic_cluster.py` | 聚类效果不佳，简化为手工关键词 |
| `app/services/analysis/network.py` | 互动网络对个人决策无价值 |
| `app/services/analysis/user_profile.py` | 用户画像对个人决策无价值 |
| `app/services/analysis/image_ocr.py` | 图片评论不是关注重点 |
| `app/services/crawler/danmaku_proto.py` | 弹幕数据本次不抓取 |
| `app/web/templates/governance.html` | 治理页面删除 |
| `app/web/templates/report.html` | 报告导出页面删除 |
| `app/api/governance.py` | 治理 API 删除 |
| `app/api/export.py` | 导出 API 简化为下载按钮 |
| `app/models/governance.py` | 治理相关表删除 |
| `app/tasks/governance.py` | 治理任务删除 |

#### 新增

| 路径 | 用途 | 优先级 |
|------|------|--------|
| `config/sectors.yaml` | 投资领域关键词配置（半导体/光通信/光芯片 + 重点博主清单） | P0 |
| `app/services/summarizer/base.py` | 摘要器抽象接口（`Summarizer.summarize(comments) -> str`） | P0 |
| `app/services/summarizer/template.py` | 模板实现（先实现，未来接 LLM） | P0 |
| `app/services/market/base.py` | 股价数据抽象接口（`MarketData.get_sector_perf(date) -> dict`） | P1 |
| `app/services/market/mock.py` | Mock 实现 | P1 |
| `app/services/analysis/investment_dict.py` | AI 投资领域专业词典（半导体/光通信/光芯片术语） | P0 |
| `app/services/analysis/sentiment_v2.py` | 简化版情感分析：正/中/负 + 投资情绪专用词典 | P0 |
| `app/services/analysis/keyword_filter.py` | 关键词提取 + 投资词典过滤，输出 Top 20 行业关键词 | P0 |
| `app/web/templates/daily_brief.html` | 单页当日简报（替代 dashboard + report） | P0 |
| `tests/fixtures/sample_comments.json` | 测试用评论样本（用于快速验证，不依赖真实 B 站） | P0 |
| `tests/test_pipeline.py` | 端到端测试：样本 → 简报 | P0 |
| `docs/adr/0001-simplify-to-investment-tool.md` | 架构决策记录：为什么砍掉通用舆情 | P0 |

#### 修改

| 路径 | 改动内容 |
|------|----------|
| `app/tasks/crawl.py` | 改为：按关键词搜索 → 热度过滤 → 只取前 100 评论 + 前 10% 回复。删除弹幕抓取。 |
| `app/services/analysis/sentiment.py` | 简化为只输出三类标签 + 投资领域情感词增强 |
| `app/services/analysis/keywords.py` | 引入投资词典过滤，输出 Top 20 而非 Top 50 |
| `app/services/analysis/trend.py` | 简化为按日聚合（近 30 天情绪趋势） |
| `app/web/templates/base.html` | 简化为单页导航：首页（简报）+ 设置（关键词/博主） |
| `app/web/templates/dashboard.html` | 重命名为 `daily_brief.html`，聚焦当日舆情简报 |
| `app/web/templates/videos.html` | 简化为"今日视频列表 + 简评按钮" |
| `app/api/videos.py` | 简化为列表 + 详情，新增 `/videos/{bvid}/summary` 端点 |
| `app/api/analysis.py` | 简化为 3 个端点：`/sentiment` `/keywords` `/brief` |
| `app/main.py` | 路由精简 + 启动时加载 `config/sectors.yaml` |
| `app/config.py` | 新增 `sectors_config_path` 字段 |
| `app/database.py` | 索引优化：videos 表按 `pub_time` + `partition_tag` 建索引 |
| `README.md` | 重写：从"通用舆情平台"改为"AI 投资舆情聚合工具" |

---

### 关键模块设计

#### 1. 投资领域配置 (`config/sectors.yaml`)

```yaml
sectors:
  - name: "半导体"
    keywords: ["半导体", "芯片", "晶圆厂", "ASML", "中芯国际", "台积电"]
    hot_threshold:
      min_play: 10000
      min_comment: 50
  - name: "光通信"
    keywords: ["光模块", "光通信", "CPO", "800G", "1.6T"]
    hot_threshold:
      min_play: 5000
      min_comment: 30
  - name: "光芯片"
    keywords: ["光芯片", "激光器", "DFB", "EML", "硅光"]
    hot_threshold:
      min_play: 5000
      min_comment: 30

crawl:
  max_videos_per_keyword: 10
  max_comments_per_video: 100
  reply_top_percent: 10
  schedule: "0 9 * * *"   # 每天 9:00 抓取
```

#### 2. 摘要器接口（为未来 LLM 预留）

```python
# app/services/summarizer/base.py
from abc import ABC, abstractmethod

class Summarizer(ABC):
    @abstractmethod
    def summarize(self, comments: list[dict]) -> str:
        """输入评论列表，输出 3-5 句中文摘要"""
        pass

# app/services/summarizer/template.py
class TemplateSummarizer(Summarizer):
    def summarize(self, comments: list[dict]) -> str:
        # 模板实现：统计正负面比例 + 提取 Top 5 关键词 + 选 1 条代表性评论
        ...
        return summary_text

# 未来扩展：app/services/summarizer/deepseek.py
# class DeepSeekSummarizer(Summarizer):
#     def summarize(self, comments: list[dict]) -> str:
#         # 调用 DeepSeek API
#         ...
```

#### 3. 股价联动接口（为未来扩展预留）

```python
# app/services/market/base.py
from abc import ABC, abstractmethod

class MarketData(ABC):
    @abstractmethod
    def get_sector_perf(self, date: str) -> dict:
        """获取某日板块涨跌幅"""
        pass

# app/services/market/mock.py
class MockMarketData(MarketData):
    def get_sector_perf(self, date: str) -> dict:
        return {"半导体": -2.3, "光通信": +1.5, "光芯片": -0.8}

# 未来扩展：app/services/market/tushare.py
# class TushareMarketData(MarketData):
#     ...
```

#### 4. 投资词典

```python
# app/services/analysis/investment_dict.py
SENTIMENT_BULLISH = ["突破", "创新高", "订单饱满", "供不应求", "扩产", "涨价", "看好", "加仓", "翻倍"]
SENTIMENT_BEARISH = ["下跌", "破位", "砍单", "库存高企", "产能过剩", "看空", "减仓", "腰斩"]
SECTOR_TERMS = {
    "半导体": ["晶圆", "制程", "光刻机", "EUV", "DUV", "良率", "封测", "Fab"],
    "光通信": ["光模块", "800G", "1.6T", "CPO", "LPO", "硅光", "EML", "DSP"],
    "光芯片": ["DFB", "EML", "VCSEL", "激光器", "探测器", "外延片"],
}
```

---

### 实施顺序（垂直切片）

按"端到端最小可用 → 增量完善"原则：

#### 切片 1: 核心闭环（1-2天）
- [ ] 写 `tests/fixtures/sample_comments.json`（10 条 AI 投资相关评论）
- [ ] 实现 `TemplateSummarizer` + `investment_dict`
- [ ] 写 `test_pipeline.py`：样本 → 情感打分 → 关键词 → 摘要
- [ ] 验证：**不看真实 B 站，5 分钟内能看到一份简报长什么样**

#### 切片 2: B 站采集（1-2天）
- [ ] 改 `tasks/crawl.py`：按 YAML 配置抓取 + 热度过滤 + 限量评论
- [ ] 接入定时任务（Celery Beat 或 APScheduler）
- [ ] 验证：跑一次真实采集，看入库数据是否符合预期

#### 切片 3: 简报页面（1天）
- [ ] 写 `daily_brief.html`：单页展示当日视频列表 + 各板块情绪占比 + Top 关键词 + 摘要
- [ ] 删除 dashboard / governance / report 页面
- [ ] 验证：UI 丑没关系，能用即可

#### 切片 4: 真实数据验证（1天）
- [ ] 重跑五月底那次大跌数据
- [ ] 对比简报输出与实际市场情绪
- [ ] 调优词典和阈值

#### 切片 5: 未来接口预留（0.5天）
- [ ] 写 `Summarizer` 和 `MarketData` 抽象类
- [ ] 写 ADR-0001 解释设计取舍
- [ ] 不实现 LLM 和股价具体调用，留 TODO

---

## Assumptions & Decisions

| 决策 | 选择 | 理由 |
|------|------|------|
| 数据存储 | 保留 MySQL | 已有数据可复用，未来扩展需要事务支持 |
| 任务调度 | 保留 Celery | 已有代码可复用，未来支持多任务 |
| Web 框架 | 保留 FastAPI | 已有代码可复用，异步性能好 |
| 前端渲染 | 保留 Jinja2 + ECharts | 用户要求 UI 不重要，能跑即可 |
| 情感分析 | 保留 SnowNLP + 加投资词典 | 短期够用，LLM 接口已预留 |
| 数据治理 | **全部删除** | 投入产出比低，对个人工具过重 |
| 弹幕抓取 | **删除** | 用户核心需求是评论 |
| 摘要器 | 新增 `TemplateSummarizer` | 即刻可用，LLM 接口已预留 |
| 股价联动 | 新增 `MockMarketData` | 本轮不实现具体调用，接口预留 |
| 调度频率 | 每天 9:00 抓取一次 | 用户使用场景是日级投资决策 |
| 配置方式 | YAML 文件 | 比硬编码灵活，比数据库简单 |

### 重要假设（需要你确认）

- **假设 1**：每天 9:00 抓一次足够。早盘前看到当日舆情简报。
- **假设 2**：只关注"近 30 天情绪趋势"和"当日摘要"，历史数据保留但分析只看近期。
- **假设 3**：投资词典的关键词列表，由你提供初始版本，我用代码加载即可。

---

## Verification

### 切片 1 验证（最重要）
```bash
pytest tests/test_pipeline.py -v
```
期望：10 条样本评论 → 输出包含"半导体/光通信/光芯片情绪占比 + Top 5 关键词 + 5 句摘要"的文本。

### 切片 2 验证
```bash
python scripts/run_crawl.py --dry-run
```
期望：按 YAML 配置搜索关键词，返回的 BV 号列表与人工搜索结果对比 ≥ 80% 重合。

### 切片 3 验证
访问 `http://localhost:8000/daily-brief`，能看到当日简报（即使没数据也有占位）。

### 切片 4 验证
跑一次真实数据，对比：
- 简报中"负面情绪占比"是否与当天股市实际跌幅相关
- Top 关键词是否能反映当日热点话题

### 切片 5 验证
```python
# 验证接口预留
from app.services.summarizer.base import Summarizer
from app.services.market.base import MarketData
# 确认有抽象类，且有至少 1 个实现
```

---

## Out of Scope（本轮不做）

- ❌ 接入 LLM API（接口预留，实现 TODO）
- ❌ 接入真实股价数据（接口预留，实现 TODO）
- ❌ 移动端适配
- ❌ 多用户/权限系统
- ❌ Docker 化部署
- ❌ 单元测试覆盖率提升（只做核心管道测试）
- ❌ 性能优化

---

## 风险与缓解

| 风险 | 缓解策略 |
|------|----------|
| B 站反爬升级导致采集失败 | Cookie 池 + 限速；接受偶发失败 |
| SnowNLP 对投资类黑话识别差 | 投资词典兜底；预留 LLM 接口 |
| 单人项目维护成本高 | 严格控制功能范围，遵循 YAGNI |
| 数据量增长导致查询慢 | videos 表索引 + 历史数据归档策略 |
