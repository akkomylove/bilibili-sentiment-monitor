# AI 投资 B 站舆情聚合工具 —— 执行文档

> 给开发用的任务清单。按"垂直切片"组织，每个切片都能独立跑通、看到效果。

> 归档日期：2026-05-31
> 状态：执行计划（部分待实施）

---

---

## 切片 0: 准备工作（0.5 天）

### 0.1 备份现状
```bash
git add -A && git commit -m "chore: v1 通用舆情平台快照（重构前备份）"
git tag v1.0-universal-platform
git checkout -b refactor/v2-investment-tool
```

### 0.2 创建新分支目录
```bash
mkdir -p config tests/fixtures docs/adr app/services/summarizer app/services/market
```

### 0.3 准备投资词典初始版本
由用户口述或文档化的关键词列表填充 `config/sectors.yaml`（见 harness 文档 §2.1）

> **环境差异说明（2026-05-31）**：
> - Windows 项目路径：`d:\bilibili-sentiment-monitor`（非 `/workspace`）
> - Python 3.13（非 3.10+）
> - 数据库端口：MySQL **3307**（非 3306），Redis **6380**（非 6379），已通过 Docker Compose 映射
> - FastAPI 端口：**8010**（`start.bat` 默认）
> - Celery 启动需加 `-P solo`（Windows 必需）
> - B 站接口需配置 Cookie + Wbi 签名

---

## 切片 1: 核心分析闭环（1-2 天）—— 最重要

> 目标：**5 分钟内不依赖 B 站也能看到一份简报长什么样**

### 1.1 准备测试样本
- [ ] 写 `tests/fixtures/sample_comments.json`（10-20 条 AI 投资相关评论）
  - 包含正面/负面/中性三类
  - 包含半导体/光通信/光芯片三类关键词
  - 包含 1-2 条"前排""来了"等噪声评论

### 1.2 写投资词典
- [ ] 创建 `app/services/analysis/investment_dict.py`
- [ ] 定义 `SENTIMENT_BULLISH` / `SENTIMENT_BEARISH` / `SECTOR_TERMS`
- [ ] 包含：晶圆、800G、CPO、EML、硅光 等术语

### 1.3 写简化的情感分析
- [ ] 重写 `app/services/analysis/sentiment.py`：
  - 输入：评论列表
  - 输出：`{positive: 0.4, neutral: 0.4, negative: 0.2}`
  - 逻辑：先查投资情感词典（强信号），再用 SnowNLP 兜底

### 1.4 写关键词提取
- [ ] 修改 `app/services/analysis/keywords.py`：
  - 用 jieba 分词
  - 用 `SECTOR_TERMS` 词典过滤
  - 输出 Top 20 而非 Top 50

### 1.5 写摘要器接口 + 模板实现
- [ ] 创建 `app/services/summarizer/base.py`（抽象类）
- [ ] 创建 `app/services/summarizer/template.py`（模板实现）
  - 模板：`"今日 {板块} 情绪偏{正面/负面}。热门关键词：{top5}。代表评论：{rpid}"`

### 1.6 写端到端测试
- [ ] 创建 `tests/test_pipeline.py`
  - 用样本数据 → 跑完整流程 → 验证输出格式
  - 5 秒内必须跑完

### 1.7 切片 1 验收
```bash
pytest tests/test_pipeline.py -v
# 期望：PASS，输出含情绪占比+关键词+摘要
```

---

## 切片 2: B 站采集精简版（1-2 天）

### 2.1 简化采集任务
- [ ] 重写 `app/tasks/crawl.py`：
  - 从 `config/sectors.yaml` 读取所有板块和关键词
  - 对每个关键词搜索 B 站，按 `hot_threshold` 过滤
  - 每个视频只取 `max_comments_per_video` 条评论（默认 100）
  - 不抓弹幕

### 2.2 限量评论逻辑
- [ ] 在 `crawl_by_keyword` 任务里：
  - 主页评论：取前 100 条
  - 回复：按 `like_count` 排序，取前 10%
  - 总数上限：150 条/视频

### 2.3 接入定时
- [ ] 配置 Celery Beat，每天 9:00 触发 `crawl_by_keyword`
- [ ] 或：APScheduler 轻量方案（如果 Celery Beat 太重）

### 2.4 切片 2 验收
```bash
python -c "from app.tasks.crawl import crawl_by_keyword; print(crawl_by_keyword.delay(1, '半导体').id)"
# 检查 Celery Worker 日志，确认任务执行成功
# 检查数据库：videos 表新增 5-10 条，comments 表新增 500-1000 条
```

---

## 切片 3: 单页简报（1 天）

### 3.1 写新页面
- [ ] 创建 `app/web/templates/daily_brief.html`：
  - 顶部：日期选择器 + 板块选择器
  - 中部：各板块情绪占比饼图（3 个）
  - 下部：今日 Top 10 视频列表（标题+摘要+情绪标签）
  - 底部：所有板块 Top 关键词合并展示

### 3.2 简化导航
- [ ] 重写 `app/web/templates/base.html`：
  - 只保留两个链接：首页（简报）/ 设置（关键词）
  - 删除：视频列表/治理/报告

### 3.3 简化 API
- [ ] 重写 `app/api/analysis.py`：
  - `GET /api/v1/analysis/daily-brief?date=2026-05-30` → 返回简报 JSON
  - `GET /api/v1/analysis/sentiment?date=...&sector=...` → 情绪数据
  - `GET /api/v1/analysis/keywords?date=...&sector=...` → 关键词数据

### 3.4 切片 3 验收
- 访问 `http://localhost:8000/daily-brief`
- 看到简报页面（即使无数据也有占位提示）
- 切换日期/板块，图表正常更新

---

## 切片 4: 真实数据验证（1 天）

### 4.1 复现五月底场景
- [ ] 用采集任务跑一次：取回 2026-05-30 当天的视频+评论
- [ ] 跑分析任务，生成当日简报

### 4.2 人工对照
- [ ] 简报中的"光通信情绪偏负面" vs 实际当天光模块板块跌幅
- [ ] Top 关键词中是否出现"800G""1.6T""砍单"等行业热词
- [ ] 标记词典需要补充的词

### 4.3 调优
- [ ] 根据 §4.2 调优 `investment_dict.py`
- [ ] 调整 `hot_threshold`（播放量/评论数阈值）
- [ ] 调整情感词典权重

### 4.4 切片 4 验收
- 跑 3 个不同日期的简报
- 人工判断 ≥ 70% 日期的简报与实际市场情绪相符

---

## 切片 5: 未来接口预留（0.5 天）

### 5.1 写股价联动接口
- [ ] 创建 `app/services/market/base.py`（抽象类）
- [ ] 创建 `app/services/market/mock.py`（返回固定 mock 数据）
- [ ] 在简报页面留一个"板块涨跌幅"区域（先用 mock 数据填充）

### 5.2 写 ADR
- [ ] 创建 `docs/adr/0001-simplify-to-investment-tool.md`
  - 状态：已采纳
  - 背景：原通用平台与真实需求脱节
  - 决策：砍掉治理/8 维/弹幕/治理页面/报告导出
  - 后果：开发效率提升、单人可维护、未来扩展空间保留

### 5.3 切片 5 验收
```python
from app.services.summarizer.base import Summarizer
from app.services.market.base import MarketData
# 确认有抽象类，且至少 1 个实现
```

---

## 切片 6: 清理（0.5 天）

### 6.1 删除废弃文件
```bash
rm -rf app/services/governance/
rm -f app/services/analysis/topic_cluster.py
rm -f app/services/analysis/network.py
rm -f app/services/analysis/user_profile.py
rm -f app/services/analysis/image_ocr.py
rm -f app/services/crawler/danmaku_proto.py
rm -f app/web/templates/governance.html
rm -f app/web/templates/report.html
rm -f app/api/governance.py
rm -f app/tasks/governance.py
```

### 6.2 更新数据库 schema
- [ ] 删除 `governance_rules` / `governance_logs` / `data_lineage` 三张表
- [ ] 在 `videos` 表加索引：`(pub_time, partition_tag)`

### 6.3 重写 README
- [ ] 标题：AI 投资 B 站舆情聚合工具
- [ ] 简介：服务 AI 领域投资者的轻量级舆情工具
- [ ] 快速开始：3 步（配置 → 启动 → 看简报）
- [ ] 数据流图：简化版

---

## 验收清单总览

| 切片 | 验证命令 | 通过标准 |
|------|----------|----------|
| 1 | `pytest tests/test_pipeline.py -v` | 5 秒内 PASS |
| 2 | 触发一次 `crawl_by_keyword` | 数据库新增 5-10 视频 |
| 3 | 访问 `/daily-brief` | 看到简报 UI |
| 4 | 跑 3 个历史日期 | 人工判断 ≥ 70% 准确 |
| 5 | `from app.services...` | 接口可导入 |
| 6 | 启动服务 | 无治理相关代码报错 |

---

## 风险检查点

- [ ] **切片 1 完成前不动 B 站采集** —— 避免引入网络依赖
- [ ] **切片 2 跑完后立刻检查数据库** —— 避免默默写坏数据
- [ ] **切片 4 不要跳过** —— 不验证就上线是最大的浪费
- [ ] **切片 5 不做"实际接入 LLM"** —— 那是另一个项目的范围
