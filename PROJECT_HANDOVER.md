# B站舆情监控与分析平台 —— 项目对接文档

> 本文档用于向新接手该项目的开发者/团队说明项目背景、已完成工作、待办事项及技术架构，确保交接过程顺畅。

---

## 一、项目由来

### 1.1 背景

B站（哔哩哔哩）作为中国最大的年轻人文化社区和视频平台，拥有海量的用户评论、弹幕和互动数据。这些数据蕴含着丰富的舆情信息，对于内容创作者、品牌方、研究者以及平台运营方而言，及时掌握视频内容的舆论走向、用户情感倾向和热点话题至关重要。

### 1.2 项目目标

本项目旨在构建一套**覆盖数据采集、数据治理、智能分析、API服务、可视化展示**的完整舆情监控与分析系统，具体目标包括：

- **数据采集**：基于B站公开API，自动采集视频元数据、评论、弹幕等多维度数据
- **数据治理**：建立数据质量保障体系，包括去重、清洗、脱敏、格式校验等
- **智能分析**：运用NLP和机器学习技术，实现情感分析、关键词提取、话题聚类、弹幕密度分析、用户画像、互动网络分析等
- **可视化展示**：通过Web仪表盘直观展示分析结果，支持交互式操作
- **报告导出**：支持CSV、JSON等多种格式的数据导出

### 1.3 技术选型理由

| 技术栈 | 选型 | 理由 |
|--------|------|------|
| Web框架 | FastAPI | 高性能异步框架，自动生成OpenAPI文档，类型安全 |
| 数据库 | MySQL + SQLAlchemy | 关系型数据存储，ORM简化操作 |
| 缓存/队列 | Redis + Celery | 异步任务调度，支持定时采集和批量分析 |
| 前端 | Jinja2 + Bootstrap5 + ECharts | 服务端渲染，快速开发，图表丰富 |
| NLP | SnowNLP + jieba + scikit-learn | 中文情感分析、分词、TF-IDF聚类 |
| 爬虫 | httpx | 异步HTTP客户端，支持Cookie认证和Wbi签名 |

---

## 二、项目架构

### 2.1 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        用户层                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ 仪表盘   │  │ 视频列表 │  │ 数据治理 │  │ 报告导出 │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
└───────┼─────────────┼─────────────┼─────────────┼─────────┘
        │             │             │             │
        └─────────────┴──────┬──────┴─────────────┘
                             │
┌────────────────────────────▼──────────────────────────────┐
│                      API 服务层 (FastAPI)                  │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ │
│  │ Monitor│ │ Videos │ │Comments│ │Analysis│ │Govern. │ │
│  │ 监控   │ │ 视频   │ │ 评论   │ │ 分析   │ │ 治理   │ │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ │
└────────────────────────────┬──────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐  ┌────────▼────────┐  ┌──────▼──────┐
│   同步处理      │  │  异步任务队列    │  │   数据存储   │
│  (直接查询DB)   │  │  (Celery+Redis) │  │  (MySQL)    │
│                 │  │                 │  │             │
│  - 列表查询     │  │  - 视频采集      │  │ - videos    │
│  - 详情查看     │  │  - 评论采集      │  │ - comments  │
│  - 质量报告     │  │  - 弹幕采集      │  │ - danmakus  │
│  - 规则管理     │  │  - 数据分析      │  │ - analysis  │
│                 │  │  - 治理流水线    │  │ - governance│
│                 │  │                 │  │ - monitor   │
└─────────────────┘  └─────────────────┘  └─────────────┘
                             │
                    ┌────────▼────────┐
                    │   B站API层      │
                    │  - 搜索API      │
                    │  - 视频详情API  │
                    │  - 评论API      │
                    │  - 弹幕XML API  │
                    │  - 弹幕Protobuf │
                    └─────────────────┘
```

### 2.2 目录结构

```
app/
├── main.py                 # FastAPI 应用入口
├── config.py               # 配置管理（环境变量驱动）
├── database.py             # SQLAlchemy 数据库连接
├── dependencies.py         # FastAPI 依赖注入
├── api/                    # RESTful API 路由层
│   ├── __init__.py         # 路由聚合（prefix=/api/v1）
│   ├── monitor.py          # 监控关键词 CRUD + 触发采集
│   ├── videos.py           # 视频列表/详情 + 触发采集/分析
│   ├── comments.py         # 评论列表/详情
│   ├── analysis.py         # 8种分析结果查询接口
│   ├── governance.py       # 治理规则/日志/血缘/质量报告
│   └── export.py           # CSV/JSON/摘要导出
├── models/                 # SQLAlchemy ORM 模型
│   ├── base.py             # 基础Base和TimestampMixin
│   ├── monitor.py          # 监控关键词表
│   ├── video.py            # 视频表
│   ├── comment.py          # 评论表
│   ├── danmaku.py          # 弹幕表
│   ├── analysis.py         # 分析结果表
│   └── governance.py       # 治理规则/日志/血缘表
├── schemas/                # Pydantic 数据校验模型
├── services/               # 业务服务层
│   ├── crawler/            # B站爬虫服务
│   │   ├── bilibili.py     # API封装（搜索/视频/评论/弹幕）
│   │   └── danmaku_proto.py # Protobuf弹幕解析器
│   ├── analysis/           # 分析算法服务
│   │   ├── sentiment.py    # SnowNLP情感分析
│   │   ├── keywords.py     # jieba关键词提取
│   │   ├── trend.py        # 时间趋势分析
│   │   ├── topic_cluster.py # TF-IDF + K-Means聚类
│   │   ├── danmaku_density.py # 弹幕密度与高潮检测
│   │   ├── network.py      # 评论互动网络分析
│   │   ├── user_profile.py # 用户画像分析
│   │   └── image_ocr.py    # 图片评论OCR分析
│   └── governance/         # 数据治理引擎
│       └── engine.py       # 治理流水线（去重/清洗/脱敏/校验）
├── tasks/                  # Celery 异步任务
│   ├── __init__.py         # Celery应用配置
│   ├── crawl.py            # 采集任务（关键词/评论/弹幕）
│   ├── analysis.py         # 分析任务（8种维度）
│   └── governance.py       # 治理任务
└── web/                    # 前端页面
    ├── routes.py           # 页面路由
    ├── static/css/         # 样式文件
    └── templates/          # Jinja2模板
        ├── base.html       # 基础布局
        ├── dashboard.html  # 仪表盘（图表+关键词管理）
        ├── videos.html     # 视频列表
        ├── video_detail.html # 视频详情+分析
        ├── governance.html # 数据治理面板
        └── report.html     # 报告导出页面

scripts/
└── init_db.py              # 数据库建表脚本
```

---

## 三、已完成的工作

### 3.1 数据采集模块

| 功能 | 状态 | 说明 |
|------|------|------|
| 视频搜索采集 | ✅ 完成 | 基于B站搜索API，支持Wbi签名认证 |
| 视频详情获取 | ✅ 完成 | 获取播放量、评论数、弹幕数、CID等 |
| 评论采集 | ✅ 完成 | 支持分页采集，单视频最多50页（约1000条） |
| 弹幕XML采集 | ✅ 完成 | 传统XML格式弹幕解析 |
| **弹幕Protobuf采集** | ✅ 完成 | 新增Protobuf二进制解析，字段更丰富 |
| 深度评论采集 | ✅ 完成 | Celery异步任务，批量采集 |
| Cookie认证 | ✅ 完成 | 支持SESSDATA等Cookie配置 |

**弹幕API技术细节**：
- B站提供两种弹幕接口：XML接口（简单）和Protobuf接口（字段完整）
- Protobuf接口返回二进制数据，包含 `mid_hash`（发送者哈希）、`ctime`（发送时间戳）、`weight`（权重）、`pool`（弹幕池）、`color`、`fontsize`、`mode` 等字段
- 项目已自研Protobuf解析器（`danmaku_proto.py`），无需额外依赖

### 3.2 数据治理模块

| 功能 | 状态 | 说明 |
|------|------|------|
| 格式校验 | ✅ 完成 | 评论长度截断（>2000字符） |
| 数据去重 | ✅ 完成 | 基于内容+用户+时间的重复检测 |
| 数据清洗 | ✅ 完成 | HTML标签过滤、Emoji过滤 |
| 数据脱敏 | ✅ 完成 | 手机号、身份证、邮箱正则替换 |
| 质量评分 | ✅ 完成 | 完整率/去重率/异常率/时效性综合评分 |
| 数据血缘 | ✅ 完成 | 记录数据从源到目标的转换链路 |
| 治理日志 | ✅ 完成 | 记录每次治理操作的详细日志 |
| 规则管理UI | ✅ 完成 | 前端支持增删改查治理规则 |

### 3.3 智能分析模块

| 分析维度 | 状态 | 算法 |
|----------|------|------|
| 情感分析 | ✅ 完成 | SnowNLP 情感打分，分正面/中性/负面 |
| 关键词提取 | ✅ 完成 | jieba 分词 + 停用词过滤 + 词频统计 |
| 趋势分析 | ✅ 完成 | 按日期聚合评论数，识别峰值点 |
| 话题聚类 | ✅ 完成 | TF-IDF向量化 + K-Means聚类 + PCA降维可视化 |
| 弹幕密度 | ✅ 完成 | 时间轴分桶统计，识别弹幕高潮片段 |
| 互动网络 | ✅ 完成 | @提及/回复关系提取，构建用户互动图 |
| 用户画像 | ✅ 完成 | 用户评论统计、影响力评分 |
| 图片OCR | ✅ 完成 | 图片评论检测与OCR文字提取 |

### 3.4 API服务模块

| 接口 | 状态 | 功能 |
|------|------|------|
| 监控关键词CRUD | ✅ 完成 | 增删改查监控关键词配置 |
| 视频数据查询 | ✅ 完成 | 列表/详情/分页/关键词筛选 |
| 评论数据查询 | ✅ 完成 | 列表/详情/按视频筛选 |
| 分析结果查询 | ✅ 完成 | 8种分析维度结果查询 |
| 治理规则管理 | ✅ 完成 | 规则CRUD + 启停切换 |
| 数据导出 | ✅ 完成 | CSV/JSON/Excel摘要三种格式 |
| 任务触发接口 | ✅ 完成 | 采集/分析/治理任务异步触发 |

### 3.5 前端可视化模块

| 页面 | 状态 | 功能 |
|------|------|------|
| 仪表盘 | ✅ 完成 | 统计卡片 + 4个ECharts图表 + 关键词管理面板 |
| 视频列表 | ✅ 完成 | 分页表格 + 搜索 + 采集操作按钮 |
| 视频详情 | ✅ 完成 | 信息卡片 + 3个图表 + 评论列表 + 操作按钮 |
| 数据治理 | ✅ 完成 | 质量指标 + 雷达图 + 规则管理 + 血缘图 + 日志 |
| 报告导出 | ✅ 完成 | 导出面板 + 分析状态总览 + 历史记录 |

**前端交互增强**：
- 所有操作按钮均可用，点击后通过Toast提示反馈结果
- 支持关键词的增删改查和触发采集
- 支持视频级别的评论/弹幕/分析触发
- 支持治理规则的增删改查和流水线执行
- 所有API调用均有错误处理和友好提示

### 3.6 基础设施

| 组件 | 状态 | 说明 |
|------|------|------|
| 数据库连接池 | ✅ 完成 | SQLAlchemy + 连接池配置 |
| 异步任务队列 | ✅ 完成 | Celery + Redis |
| 环境变量配置 | ✅ 完成 | pydantic-settings + .env文件 |
| CORS中间件 | ✅ 完成 | 支持跨域访问 |
| 静态文件服务 | ✅ 完成 | CSS/JS静态资源托管 |
| 自动API文档 | ✅ 完成 | FastAPI原生Swagger/ReDoc |

---

## 四、待完成的工作（建议优化方向）

### 4.1 高优先级

1. **用户认证与权限管理**
   - 当前系统无登录机制，建议增加JWT认证
   - 区分管理员/普通用户权限

2. **定时任务调度**
   - 当前仅支持手动触发采集
   - 建议增加APScheduler或Celery Beat实现定时采集

3. **数据看板实时刷新**
   - 当前页面数据为静态加载
   - 建议增加WebSocket或轮询机制实现实时更新

4. **弹幕Protobuf接口全面替换**
   - 当前为XML优先、Protobuf回退策略
   - 建议全面切换至Protobuf接口以获取更完整数据

### 4.2 中优先级

5. **分析算法优化**
   - 情感分析：SnowNLP准确率有限，建议接入更专业的中文情感模型（如BERT-based）
   - 话题聚类：当前K-Means需要预设聚类数，建议尝试LDA主题模型
   - 关键词提取：建议引入TF-IDF权重替代简单词频

6. **数据存储优化**
   - 当前所有数据存MySQL，弹幕/评论数据量大时性能下降
   - 建议弹幕数据存入MongoDB或ClickHouse

7. **前端框架升级**
   - 当前为服务端渲染（Jinja2），交互体验有限
   - 建议前端迁移至Vue3/React + 独立API调用

8. **监控告警**
   - 增加异常监控（采集失败、分析失败告警）
   - 增加数据量阈值告警（评论激增/情感突变）

### 4.3 低优先级

9. **移动端适配**
   - 当前页面为桌面端设计，移动端体验不佳

10. **多平台扩展**
    - 当前仅支持B站，可扩展至抖音、微博等平台

11. **数据可视化增强**
    - 增加更多图表类型（热力图、桑基图、时间轴等）
    - 支持图表下钻和联动

---

## 五、环境配置说明

### 5.1 环境变量（.env）

```ini
# MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=bilibili_sentiment

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# App
APP_DEBUG=true
APP_SECRET_KEY=change-me-in-production
APP_HOST=0.0.0.0
APP_PORT=8000

# B站Cookie（可选，用于需要登录的接口）
BILIBILI_COOKIE=SESSDATA=xxx; bili_jct=xxx
# B站Wbi密钥（可选，用于搜索API签名）
BILIBILI_WBI_IMG_URL=https://i0.hdslb.com/bfs/wbi/xxx.png
BILIBILI_WBI_SUB_URL=https://i0.hdslb.com/bfs/wbi/xxx.png
```

### 5.2 启动命令

```bash
# 1. 初始化数据库
python scripts/init_db.py

# 2. 启动Web服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 3. 启动Celery Worker（另开终端）
python -m celery -A app.tasks worker --loglevel=info --concurrency=2
```

### 5.3 依赖列表

```
fastapi>=0.100.0
uvicorn[standard]
sqlalchemy>=2.0.0
pymysql
redis
celery
httpx
pydantic>=2.0.0
pydantic-settings
jieba
snownlp
scikit-learn
numpy
matplotlib
```

---

## 六、关键代码文件索引

| 功能 | 文件路径 |
|------|----------|
| 应用入口 | [app/main.py](file:///workspace/app/main.py) |
| 配置管理 | [app/config.py](file:///workspace/app/config.py) |
| 数据库模型 | [app/models/](file:///workspace/app/models/) |
| API路由 | [app/api/](file:///workspace/app/api/) |
| B站爬虫 | [app/services/crawler/bilibili.py](file:///workspace/app/services/crawler/bilibili.py) |
| Protobuf解析 | [app/services/crawler/danmaku_proto.py](file:///workspace/app/services/crawler/danmaku_proto.py) |
| 情感分析 | [app/services/analysis/sentiment.py](file:///workspace/app/services/analysis/sentiment.py) |
| 话题聚类 | [app/services/analysis/topic_cluster.py](file:///workspace/app/services/analysis/topic_cluster.py) |
| 治理引擎 | [app/services/governance/engine.py](file:///workspace/app/services/governance/engine.py) |
| 采集任务 | [app/tasks/crawl.py](file:///workspace/app/tasks/crawl.py) |
| 分析任务 | [app/tasks/analysis.py](file:///workspace/app/tasks/analysis.py) |
| 仪表盘页面 | [app/web/templates/dashboard.html](file:///workspace/app/web/templates/dashboard.html) |
| 基础模板 | [app/web/templates/base.html](file:///workspace/app/web/templates/base.html) |

---

## 七、常见问题

### Q1: 弹幕Protobuf API如何获取？

B站弹幕Protobuf接口地址为：
```
GET https://api.bilibili.com/x/v2/dm/web/seg.so?oid={cid}&segment_index=1
```

- `oid` 为视频CID（通过视频详情接口获取）
- `segment_index` 为分片索引，每6分钟一个分片
- 返回数据为Protobuf二进制格式，解析代码见 [danmaku_proto.py](file:///workspace/app/services/crawler/danmaku_proto.py)

### Q2: 为什么需要Cookie？

部分B站接口（如搜索API）在频繁调用时会要求登录态。配置 `BILIBILI_COOKIE` 中的 `SESSDATA` 可绕过部分限制。Cookie可从浏览器开发者工具中获取。

### Q3: Celery任务没有执行？

检查以下几点：
1. Redis是否正常运行：`redis-cli ping` 应返回 `PONG`
2. Celery Worker是否已启动
3. 检查Worker日志是否有任务接收记录

### Q4: 数据库表如何创建？

运行初始化脚本：
```bash
python scripts/init_db.py
```

该脚本会基于SQLAlchemy模型自动创建所有表。

---

## 八、联系方式与交接记录

- **项目创建日期**：2026年5月
- **当前版本**：v1.0.0
- **交接日期**：2026年5月31日
- **交接内容**：完整代码包 + 本文档
- **已知问题**：无严重Bug，所有功能经测试可用

---

> 本文档随代码同步更新，如有疑问请参考代码注释或API文档（`/docs`）。
