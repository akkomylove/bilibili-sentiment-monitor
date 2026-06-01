# 毕设规格文档：B站舆情监控与分析平台

> 创建日期：2026-05-29
> 状态：待实现

---

## 一、项目概述

基于 Python 全栈的通用舆情监控与分析平台，以 B站（哔哩哔哩）为数据源，覆盖**数据采集 → 数据治理 → 数据分析 → API 服务 → 可视化展示**的数据全生命周期。

### 核心目标

| 要求 | 体现方式 |
|------|----------|
| **数据分析** | 情感分析、关键词提取、趋势分析、用户画像、图片OCR、弹幕密度、话题聚类、互动网络（共8维） |
| **数据治理** | 四层治理体系（接入校验 → 清洗去重 → 安全脱敏 → 质量监控+血缘追踪） |
| **API** | FastAPI RESTful 接口 + Swagger 自动文档，覆盖采集/查询/分析/治理/导出全部能力 |

---

## 二、技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 语言 | Python 3.10+ | 全栈统一语言 |
| Web框架 | FastAPI | API 服务 + 后端路由 |
| 异步任务 | Celery + Redis | 爬虫调度、定时分析、治理任务 |
| 数据库 | MySQL 8.0 | 业务数据存储 |
| 缓存/队列 | Redis | Celery Broker + 热数据缓存 |
| 爬虫 | Scrapy / httpx | B站数据采集 |
| 分词/NLP | Jieba + SnowNLP | 中文分词、情感分析 |
| 聚类 | scikit-learn (K-Means / LDA) | 话题聚类 |
| OCR | PaddleOCR / EasyOCR | 图片评论文字识别 |
| 去重 | SimHash | 相似评论去重 |
| 可视化 | ECharts + Matplotlib + WordCloud | 图表 + 词云 |
| 前端 | Jinja2 + Bootstrap 5 | 模板渲染，轻量仪表盘 |

---

## 三、数据模型

### ER 关系

```
monitor_keywords ──→ videos ──→ comments
                         │
                         └──→ danmakus

governance_rules ──→ governance_logs

data_lineage ──────→ (追踪全链路)
```

### 表结构

#### videos（视频基础信息）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 自增主键 |
| bvid | VARCHAR(20) UNIQUE | B站视频标识 |
| title | VARCHAR(500) | 视频标题 |
| description | TEXT | 视频描述 |
| play_count | INT | 播放量 |
| danmaku_count | INT | 弹幕总数 |
| comment_count | INT | 评论总数 |
| pub_time | DATETIME | 发布时间 |
| partition_tag | VARCHAR(100) | 分区标签 |
| keyword_id | INT FK | 关联监控关键词 |
| created_at | DATETIME | 入库时间 |

#### comments（评论数据）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 自增主键 |
| rpid | BIGINT UNIQUE | B站评论ID |
| video_bvid | VARCHAR(20) FK | 所属视频 |
| user_mid | VARCHAR(100) | 用户mid（脱敏后） |
| content | TEXT | 评论内容 |
| like_count | INT | 点赞数 |
| reply_count | INT | 回复数 |
| has_image | TINYINT(1) | 是否含图片 |
| image_urls | JSON | 图片链接列表 |
| pub_time | DATETIME | 发布时间 |
| created_at | DATETIME | 入库时间 |

#### danmakus（弹幕数据）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 自增主键 |
| video_bvid | VARCHAR(20) FK | 所属视频 |
| content | VARCHAR(500) | 弹幕内容 |
| timeline | DECIMAL(10,3) | 出现时间点（秒） |
| send_time | DATETIME | 发送时间 |
| created_at | DATETIME | 入库时间 |

#### monitor_keywords（监控配置）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 自增主键 |
| keyword | VARCHAR(200) | 监控关键词 |
| partition_filter | VARCHAR(200) | 分区过滤（逗号分隔） |
| crawl_interval | INT | 采集频率（分钟） |
| is_active | TINYINT(1) | 启用状态 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

#### governance_rules（治理规则）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 自增主键 |
| rule_name | VARCHAR(200) | 规则名称 |
| rule_type | VARCHAR(50) | 规则类型 |
| rule_config | JSON | 规则配置 |
| phase | VARCHAR(50) | 所属治理阶段 |
| is_active | TINYINT(1) | 启用状态 |
| created_at | DATETIME | 创建时间 |

> 规则类型枚举：`format_check` / `dedup` / `desensitize` / `clean` / `quality`

#### governance_logs（治理日志）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 自增主键 |
| target_type | VARCHAR(50) | 数据表名 |
| target_id | INT | 数据记录ID |
| rule_id | INT FK | 关联规则 |
| action | VARCHAR(100) | 执行动作 |
| before_value | JSON | 处理前值 |
| after_value | JSON | 处理后值 |
| executed_at | DATETIME | 执行时间 |

#### data_lineage（数据血缘）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 自增主键 |
| source_type | VARCHAR(50) | 源数据类型 |
| source_id | VARCHAR(100) | 源数据标识 |
| target_type | VARCHAR(50) | 目标数据类型 |
| target_id | VARCHAR(100) | 目标数据标识 |
| transform_step | VARCHAR(200) | 转换步骤 |
| executed_at | DATETIME | 时间戳 |

#### analysis_results（分析结果）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK | 自增主键 |
| analysis_type | VARCHAR(50) | 分析类型 |
| ref_type | VARCHAR(50) | 关联数据类型 |
| ref_id | VARCHAR(100) | 关联数据标识 |
| result_data | JSON | 分析结果 |
| analyzed_at | DATETIME | 分析时间 |

---

## 四、数据治理模块（四层体系）

### 第一层：数据接入治理
- 格式校验：Pydantic 模型验证，检查字段完整性、数据类型
- 空值处理：填充默认值 / 标记 / 丢弃，根据字段重要性分级策略
- 长度截断：超长文本截取 + 记录日志
- 编码统一：UTF-8 标准化

### 第二层：数据清洗治理
- 精确去重：以 `(content + user_mid + pub_time)` 三要素联合去重
- 相似去重：SimHash 海明距离 < 3 视为重复（过滤复读机评论）
- 敏感词过滤：广告/违规内容标记，不删除仅标记
- HTML/Emoji 清洗：保留纯文本供后续分析

### 第三层：数据安全治理
- 用户 mid 脱敏：SHA256 + 固定盐值，不可逆
- 评论内容敏感信息识别：正则匹配手机号/身份证/邮箱，标记并脱敏
- IP 属地信息脱敏：仅保留省份

### 第四层：数据质量监控 + 血缘追踪
- 质量指标：完整率、去重率、异常率、时效性
- 血缘链路：原始数据(comments) → 清洗后 → 脱敏后 → 分析结果(analysis_results)
- 定时生成数据质量报告（评分 + 趋势图）
- 可视化为 DAG 血缘图

---

## 五、数据分析模块（8 维）

| # | 维度 | 技术 | 输出 |
|---|------|------|------|
| ① | 情感分析 | SnowNLP 打分 → [正面/中性/负面] | 情感趋势折线图、占比饼图、按关键词/分区分组 |
| ② | 关键词提取 | Jieba 分词 → 去停用词 → TF-IDF | 词云图、关键词热度排行、共现关系网络 |
| ③ | 趋势分析 | 时间窗口聚合 + 异常检测 | 时间序列折线图、峰值时段分布、异常标注 |
| ④ | 用户画像 | 活跃时段 + 情感倾向 + 互动行为 | 活跃时段热力图、群体情感分布（全脱敏） |
| ⑤ | 图片评论OCR | PaddleOCR/EasyOCR 识别图片文字 | 图片评论占比、图片文字词云、图文结合情感 |
| ⑥ | 弹幕密度 | 秒级密度统计 + 峰值检测 | 弹幕密度曲线、高潮片段排名、弹幕词随时间变化 |
| ⑦ | 话题聚类 | TF-IDF向量化 → K-Means / LDA | 评论话题自动分组、代表评论、话题热度排行 |
| ⑧ | 互动网络 | @提及 / 回复关系图 | 用户互动网络图、关键传播节点、讨论子群发现 |

---

## 六、API 模块

### 接口总览

```
/api/v1
├── /monitor                    # 监控配置 CRUD
│   ├── GET    /keywords
│   ├── POST   /keywords
│   ├── PUT    /keywords/{id}
│   ├── DELETE /keywords/{id}
│   └── POST   /keywords/{id}/trigger
│
├── /videos                     # 视频数据查询
│   ├── GET    /
│   └── GET    /{bvid}
│
├── /comments                   # 评论数据查询
│   ├── GET    /
│   └── GET    /{rpid}
│
├── /analysis                   # 分析结果查询
│   ├── GET    /sentiment
│   ├── GET    /keywords
│   ├── GET    /trend
│   ├── GET    /user-profile
│   ├── GET    /image-ocr
│   ├── GET    /danmaku-density
│   ├── GET    /topic-cluster
│   └── GET    /network
│
├── /governance                 # 数据治理
│   ├── GET    /quality-report
│   ├── GET    /lineage
│   ├── GET    /logs
│   ├── GET    /rules
│   └── POST   /rules
│
└── /export                     # 数据导出
    ├── GET    /report/csv
    └── GET    /report/json
```

### 技术细节
- FastAPI 自动生成 Swagger (OpenAPI) 文档，访问 `/docs` 即可
- 所有请求体/响应体使用 Pydantic 模型定义
- 分页参数统一：`page` + `page_size`
- 错误响应统一格式：`{"error": "...", "detail": "..."}`

---

## 七、前端展示模块

### 页面结构

| 页面 | 路由 | 内容 |
|------|------|------|
| 仪表盘首页 | `/` | 概览卡片 + 情感趋势 + 词云 + 话题聚类散点图 + 弹幕密度 + 互动网络 |
| 视频列表 | `/videos` | 视频表格（筛选/分页）→ 点击进入视频详情 |
| 视频详情 | `/videos/{bvid}` | 该视频全维度分析图表 |
| 数据治理 | `/governance` | 规则配置表单 + 质量趋势图 + 血缘 DAG 图 |
| 报告导出 | `/report` | 选择时间范围 + 维度 → 生成下载链接 |

### 技术选型
- **Jinja2**：服务端模板渲染，无需前后端分离
- **ECharts**：折线图、饼图、散点图、热力图、关系图、词云
- **Bootstrap 5**：响应式布局，快速出风格统一的 UI

---

## 八、项目目录结构

```
bilibili-sentiment-platform/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── config.py               # 配置管理
│   ├── api/                    # API 路由
│   │   ├── __init__.py
│   │   ├── monitor.py
│   │   ├── videos.py
│   │   ├── comments.py
│   │   ├── analysis.py
│   │   ├── governance.py
│   │   └── export.py
│   ├── models/                 # SQLAlchemy 数据模型
│   │   ├── __init__.py
│   │   ├── video.py
│   │   ├── comment.py
│   │   ├── danmaku.py
│   │   ├── monitor.py
│   │   ├── governance.py
│   │   └── analysis.py
│   ├── schemas/                # Pydantic 请求/响应模型
│   │   └── ...
│   ├── services/               # 业务逻辑层
│   │   ├── crawler/            # 爬虫服务
│   │   ├── governance/         # 治理引擎
│   │   ├── analysis/           # 分析引擎
│   │   └── report/             # 报告生成
│   ├── tasks/                  # Celery 异步任务
│   │   ├── crawl.py
│   │   ├── governance.py
│   │   └── analysis.py
│   └── web/                    # 前端页面
│       ├── templates/
│       │   ├── base.html
│       │   ├── dashboard.html
│       │   ├── videos.html
│       │   ├── video_detail.html
│       │   ├── governance.html
│       │   └── report.html
│       └── static/
│           ├── css/
│           └── js/
├── tests/
│   ├── test_api/
│   ├── test_services/
│   └── test_governance/
├── scripts/
│   ├── init_db.py              # 数据库初始化
│   └── seed_data.py            # 演示数据填充
├── requirements.txt
├── .env.example
└── README.md
```

---

## 九、答辩话术要点

### 数据治理线（专业核心）
> "本系统建立了四层数据治理体系，覆盖数据从采集到分析的全生命周期。第一层接入治理确保数据符合标准规范，第二层清洗治理通过精确去重和 SimHash 相似去重保证数据唯一性，第三层安全治理对用户标识和敏感信息进行脱敏处理，第四层通过血缘追踪和质量报告实现数据可追溯、可量化。"

### 数据分析线（广度展示）
> "系统从八个维度对舆情数据进行分析：基础的情感分析、关键词提取、趋势分析反映舆论基本面，进阶的话题聚类和互动网络挖掘深层次关系，特色的弹幕密度分析发挥B站平台数据优势，差异化的图片评论OCR填补了纯文本分析的盲区。"

### API 线（工程能力）
> "系统对外提供标准的 RESTful API，基于 FastAPI 框架自动生成 OpenAPI 文档，覆盖监控配置、数据查询、分析查询、治理管理和报告导出全部功能，第三方系统可直接集成调用。"

---

## 十、开发顺序建议

| 阶段 | 内容 | 预计优先级 |
|------|------|------------|
| Phase 1 | 项目骨架：FastAPI 启动 + MySQL 模型 + 配置管理 | ⭐⭐⭐ |
| Phase 2 | 爬虫 + 数据入库：B站采集 → Celery 调度 → 写入原始表 | ⭐⭐⭐ |
| Phase 3 | 治理引擎：四层治理规则 + 日志记录 | ⭐⭐⭐ |
| Phase 4 | 分析引擎 ①-④：情感/关键词/趋势/用户画像 | ⭐⭐⭐ |
| Phase 5 | API + Swagger：所有接口 + 文档 | ⭐⭐⭐ |
| Phase 6 | 前端仪表盘：Jinja2 + ECharts | ⭐⭐ |
| Phase 7 | 分析引擎 ⑤-⑧：OCR/弹幕密度/聚类/网络 | ⭐⭐ |
| Phase 8 | 数据血缘可视化 + 质量报告仪表盘 | ⭐ |
| Phase 9 | 导出功能 + 完善测试 + 演示数据 | ⭐ |