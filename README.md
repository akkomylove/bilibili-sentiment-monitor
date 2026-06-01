# B站舆情监控与分析平台

基于 FastAPI + Celery + MySQL + Redis 构建的 Bilibili 舆情数据采集与多维分析系统，支持关键词监控、情感分析、话题聚类、数据治理与血缘追踪。

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI + SQLAlchemy + Pydantic |
| 任务队列 | Celery + Redis |
| 数据库 | MySQL 8.0 |
| 前端渲染 | Jinja2 + Bootstrap 5 + ECharts |
| 爬虫 | requests + Protobuf 弹幕解析 |
| 文本分析 | SnowNLP + jieba + scikit-learn |
| 容器化 | Docker Compose |

---

## 功能特性

### 数据采集
- 关键词视频搜索（支持综合/播放量/时间排序）
- 评论深度采集（前100条热评 + 10%回复）
- 弹幕全量采集（按视频时长智能分段）
- B站热搜榜定时采集

### 舆情分析（八维分析）
- 情感分析（基于点赞数的加权情感评分）
- 关键词提取（词频统计 + 停用词过滤）
- 趋势分析（时序情感走势 + 峰值检测）
- 话题聚类（K-Means + PCA 降维可视化）
- 用户画像（评论者活跃度分布）
- 互动网络（评论者关系图）
- 弹幕密度（时间轴密度分布）

### 数据治理
- 格式校验（空值/长度/类型检查）
- 去重处理（同一用户相同内容去重）
- 数据清洗（HTML标签过滤）
- 敏感脱敏（手机号/邮箱隐藏）
- 质量评分（完整率/去重率/时效性）
- 血缘追踪（数据流转链路可视化）

### 监控配置
- 关键词 CRUD 管理
- 启用/停用切换
- 单关键词采集/分析
- 全量采集/分析
- 自动定时采集（Celery Beat）

---

## 快速启动

### 环境要求
- Python 3.10+
- Docker Desktop

### 一键启动（Windows）
```bash
start.bat
```

### 手动启动
```bash
# 1. 启动 MySQL + Redis
docker compose up -d

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填写 B站 Cookie 和 Wbi 密钥

# 4. 初始化数据库
python scripts/init_db.py
python scripts/seed_data.py

# 5. 启动服务（三个终端）
uvicorn app.main:app --host 0.0.0.0 --port 8010
celery -A app.tasks worker --loglevel=info --concurrency=1 -P solo
celery -A app.tasks beat --loglevel=info
```

---

## 项目结构

```
app/
├── api/           # RESTful API 路由
├── models/        # SQLAlchemy 数据模型
├── schemas/       # Pydantic 数据校验
├── services/      # 业务逻辑层
│   ├── analysis/  # 八维分析引擎
│   ├── crawler/   # B站爬虫
│   ├── governance/# 数据治理引擎
│   └── report/    # 报告生成
├── tasks/         # Celery 异步任务
└── web/           # 前端模板与静态资源

scripts/           # 数据库初始化
tests/             # pytest 单元测试
docs/              # 设计文档
```

---

## 定时任务

| 任务 | 间隔 | 说明 |
|------|------|------|
| auto_crawl_keywords | 5分钟 | 自动采集启用状态的关键词 |
| run_full_analysis | 30分钟 | 自动运行全量分析 |
| crawl_hot_search | 60分钟 | 自动采集B站热搜榜 |

---

## 测试

```bash
pytest tests/ -v
```

26 个单元测试覆盖分析引擎、爬虫、数据治理核心模块。

---

## 访问地址

| 端点 | 地址 |
|------|------|
| 前端仪表盘 | http://localhost:8010/dashboard |
| 监控配置 | http://localhost:8010/monitor |
| 数据治理 | http://localhost:8010/governance |
| 热点话题 | http://localhost:8010/hot-search |
| API 文档 | http://localhost:8010/docs |

---

## 许可证

MIT
