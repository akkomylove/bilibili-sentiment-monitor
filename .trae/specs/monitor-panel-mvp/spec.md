# 监控面板 MVP 设计文档

## 目标
为用户提供一个配置式监控面板，让用户可以方便地添加/管理监控关键词，系统自动定时采集数据，用户随时查看采集进度和分析结果。

## 架构
- 后端：扩展现有 FastAPI + SQLAlchemy 模型，新增监控状态 API
- 前端：新增独立 `/monitor` 页面，包含关键词配置区 + 实时监控区 + 数据概览区
- 定时任务：复用现有 Celery Beat 配置（每 5 分钟自动采集）

## 文件变更清单

### 后端
- `app/models/monitor.py` — 增加 `last_crawled_at` 字段
- `app/schemas/monitor.py` — 增加响应字段
- `app/api/monitor.py` — 新增 `/status` 和 `/activities` 端点
- `app/tasks/crawl.py` — 更新 `crawl_by_keyword` 以记录 `last_crawled_at`
- `scripts/init_db.py` — 需要重新建表或添加迁移（MVP 直接重建）

### 前端
- `app/web/routes.py` — 新增 `/monitor` 路由
- `app/web/templates/monitor.html` — 新增监控面板页面
- `app/web/templates/base.html` — 导航栏增加"监控配置"入口
- `app/web/static/js/monitor.js` — 页面交互逻辑（可选，也可内联）

## API 设计

### GET /api/v1/monitor/status
返回所有关键词的采集状态汇总：
```json
{
  "keywords": [
    {
      "id": 1,
      "keyword": "Python教程",
      "is_active": true,
      "crawl_interval": 60,
      "last_crawled_at": "2026-05-31T12:00:00",
      "total_videos": 15,
      "total_comments": 320
    }
  ],
  "summary": {
    "active_count": 2,
    "total_videos": 25,
    "total_comments": 580
  }
}
```

### GET /api/v1/monitor/activities
返回最近采集活动日志（基于 videos.created_at 反推）：
```json
{
  "activities": [
    {
      "time": "2026-05-31T12:00:00",
      "keyword": "Python教程",
      "action": "crawl",
      "videos_added": 5,
      "comments_added": 120
    }
  ]
}
```

## 页面布局

```
+--------------------------------------------------+
|  监控配置中心                                      |
+--------------------------------------------------+
|  +------------------------+  +------------------+ |
|  | 关键词配置区            |  | 实时监控区        | |
|  | - 关键词列表            |  | - 任务状态看板    | |
|  | - 添加/编辑/删除        |  | - 最近采集动态    | |
|  | - 启用/停用             |  | - 快捷操作按钮    | |
|  +------------------------+  +------------------+ |
|  +------------------------------------------------+ |
|  | 数据概览区                                        | |
|  | - 各关键词视频数/评论数/情感分析结果               | |
|  +------------------------------------------------+ |
+--------------------------------------------------+
```

## 测试计划
- 测试新增 API 端点返回正确数据格式
- 测试页面能正常加载并显示关键词列表
- 测试添加/删除关键词后状态实时更新
