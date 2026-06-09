# 文档目录

本目录存放项目的设计/规约/执行计划文档。

## 目录结构

```
docs/
├── adr/                        # 架构决策记录 (Architecture Decision Records)
│   └── 0001-simplify-to-investment-tool.md
└── superpowers/                # 完整设计/计划/规约
    ├── plans/                  # 实施计划
    │   ├── 2026-05-29-bilibili-sentiment-platform-plan.md   (v1.0 历史)
    │   └── 2026-05-31-ai-investment-bilibili-sentiment-execution-plan.md (当前)
    └── specs/                  # 设计与规约
        ├── 2026-05-29-bilibili-sentiment-platform-design.md  (v1.0 历史)
        ├── 2026-05-31-ai-investment-bilibili-sentiment-v2-design.md   (v2 概览)
        └── 2026-05-31-ai-investment-bilibili-sentiment-harness.md     (v2 操作手册)
```

## 阅读建议

| 角色 | 顺序 |
|---|---|
| 想了解项目做什么 | [README.md](../README.md) → [v2-design.md](superpowers/specs/2026-05-31-ai-investment-bilibili-sentiment-v2-design.md) |
| 想本地跑起来 | [harness.md](superpowers/specs/2026-05-31-ai-investment-bilibili-sentiment-harness.md) |
| 想知道执行节奏 | [execution-plan.md](superpowers/plans/2026-05-31-ai-investment-bilibili-sentiment-execution-plan.md) |
| 想知道 v1 → v2 演进动机 | [0001-simplify-to-investment-tool.md](adr/0001-simplify-to-investment-tool.md) |
| 想看 v1 历史 | [2026-05-29-*.md](superpowers/specs/) (v1 毕设阶段，已废弃) |

## 文档版本

| 文档 | 状态 |
|---|---|
| v1.0 设计与计划 (2026-05-29) | 历史归档，**仅供回溯参考** |
| v2.1 设计与规约 (2026-05-31+) | 当前主线 |
