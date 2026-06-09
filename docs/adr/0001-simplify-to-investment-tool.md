# ADR-0001: 砍掉通用舆情，重构为 AI 投资领域轻量级聚合工具

| 字段 | 值 |
| --- | --- |
| 状态 | 已采纳（Accepted） |
| 日期 | 2026-06-07 |
| 决策者 | 项目 owner + 模型 |
| 影响范围 | 整个项目架构 |

## 背景（Context）

项目最初定位为"通用 B 站舆情监控平台"，覆盖：

- **8 维分析**：情感 / 关键词 / 趋势 / 用户画像 / 图片 OCR / 弹幕密度 / 话题聚类 / 互动网络
- **4 层数据治理**：接入 / 清洗 / 脱敏 / 质量 + 血缘
- **5 个页面**：仪表盘 / 视频列表 / 视频详情 / 治理 / 报告导出
- **复杂接口**：话题聚类、用户活跃时段、互动网络、报告 CSV/JSON 导出

但用户实际场景是**做 AI 投资决策**（半导体/光通信/光芯片），日常需要追踪 B 站博主视频和评论。

### 核心问题

1. **没有"用户视角"**：设计出发点是"我能爬什么数据"，不是"用户做投资决策时需要看什么"
2. **过早工程化**：在没验证效果之前就堆了完整数据治理和 8 维分析
3. **反馈循环太长**：跑一天数据才能看一次效果，词云/聚类调优没有迭代节奏
4. **数据规模失控**：项目要"能用"，不是要做 SaaS 平台
5. **单人维护成本高**：投入产出比低

## 决策（Decision）

将项目从"通用舆情平台"重构为"AI 投资舆情聚合工具"：

### 砍掉（不再投入）

| 模块 | 原因 | 替代方案 |
| --- | --- | --- |
| 4 层数据治理（governance/） | 对个人工具过重 | 保留 AnalysisResult 表存结果，治理层不再做流水线 |
| 8 维分析中的 4 个 | 聚类效果不佳、互动网络 / 用户画像 / OCR 对个人决策无价值 | 保留情感 / 关键词 / 趋势（v1 已有，v2 简化） |
| 弹幕抓取与解析 | 用户核心需求是评论 | 直接删 |
| 治理页面 / 报告导出页面 / 报告 API | 不是核心需求 | 简报页面涵盖 |
| 话题聚类（topic_cluster） | 聚类效果不佳 | 简化为手工关键词 + 板块术语加权 |
| 互动网络（network） | 对个人决策无价值 | 保留代码以备扩展，前端不展示 |
| 用户画像（user_profile） | 对个人决策无价值 | 同上 |
| 图片 OCR（image_ocr） | 不是关注重点 | 删 |
| 全站热点话题（hot_search） | 与投资领域无关 | 删 |

### 保留 / 简化

- B 站采集（search + top comments + replies）
- 评论情感分析（SnowNLP + 投资词典增强）
- 关键词提取（jieba + 投资词典过滤 + Top 20）
- 视频/评论/关键词 CRUD 接口
- 监控关键词页面

### 新增（未来预留接口）

- `Summarizer` 抽象接口：先返回模板文本，未来接 DeepSeek / 通义千问
- `MarketData` 抽象接口：先返回 mock 数据，未来接 Tushare / AKShare
- 投资领域配置 `config/sectors.yaml`：板块 / 关键词 / 热度阈值
- 单页简报 `/daily-brief`：日期 + 板块选择 + 3 板块饼图 + Top 10 视频 + 关键词 + 涨跌幅

## 后果（Consequences）

### 正面

1. **开发效率提升**：单人可在 1-2 天内完成 v2 重构
2. **单人可维护**：核心代码量从 ~30 个文件缩到 ~15 个
3. **反馈循环缩短**：纯函数 pipeline + 端到端测试，5 秒内可验证
4. **未来扩展空间保留**：`Summarizer` / `MarketData` 抽象接口已留好，后续接 LLM/股价不需要重写

### 负面 / 风险

1. **v1 API 调用方会 404**：本次 v2 仅删代码，不删数据；AnalysisResult 表保留
2. **失去"通用性"**：未来若想做其他领域，需要重新加回治理/8 维
3. **Mock 数据失真**：`MockMarketData` 是确定性扰动，与真实市场有偏差，需人工对照调优

## 未来可恢复的扩展点

如果未来要恢复部分功能，已有清晰路径：

| 扩展方向 | 触发条件 | 实施位置 |
| --- | --- | --- |
| 接入 DeepSeek LLM | 模板摘要过于模板化 | 新增 `app/services/summarizer/deepseek.py` |
| 接入 Tushare | Mock 数据无法满足决策 | 新增 `app/services/market/tushare.py` |
| 真实弹幕抓取 | 视频内实时讨论有价值 | `BilibiliAPI.get_all_danmaku_proto` 已实现 |
| 互动网络 | 关注"意见领袖" | `app/services/analysis/network.py` 已重写为基于 parent_rpid |
| 用户画像 | 高活跃用户识别 | `app/services/analysis/user_profile.py` 已有 |

## 参考

- 设计稿：[`docs/superpowers/specs/2026-05-31-ai-investment-bilibili-sentiment-v2-design.md`](../superpowers/specs/2026-05-31-ai-investment-bilibili-sentiment-v2-design.md)
- 执行计划：[`docs/superpowers/plans/2026-05-31-ai-investment-bilibili-sentiment-execution-plan.md`](../superpowers/plans/2026-05-31-ai-investment-bilibili-sentiment-execution-plan.md)
- 当前 spec：[`.trae/specs/refactor-v2-investment-tool/spec.md`](../../.trae/specs/refactor-v2-investment-tool/spec.md)
