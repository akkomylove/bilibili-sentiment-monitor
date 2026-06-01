# Tasks

## Phase 1: 工程规范基础建设

- [ ] Task 1.1: 创建 requirements.txt
  - [ ] Step 1.1.1: 梳理项目所有依赖并生成 requirements.txt
  - [ ] Step 1.1.2: 验证 requirements.txt 可正常安装

- [ ] Task 1.2: 创建 pyproject.toml（ruff + mypy 配置）
  - [ ] Step 1.2.1: 编写 pyproject.toml，配置 ruff 代码风格规则和 mypy 类型检查
  - [ ] Step 1.2.2: 运行 ruff check app/，修复可自动修复的问题
  - [ ] Step 1.2.3: 运行 mypy app/，修复核心类型错误

- [ ] Task 1.3: 创建测试框架结构
  - [ ] Step 1.3.1: 创建 tests/ 目录结构和 conftest.py
  - [ ] Step 1.3.2: 配置 pytest 和测试数据库（SQLite in-memory）
  - [ ] Step 1.3.3: 验证 pytest 可正常运行

## Phase 2: 核心模块单元测试

- [ ] Task 2.1: 爬虫服务测试
  - [ ] Step 2.1.1: 测试 BilibiliAPI 数据解析（mock HTTP 响应）
  - [ ] Step 2.1.2: 测试 Protobuf 弹幕解析器

- [ ] Task 2.2: 治理引擎测试
  - [ ] Step 2.2.1: 测试数据去重逻辑
  - [ ] Step 2.2.2: 测试数据清洗逻辑
  - [ ] Step 2.2.3: 测试数据脱敏逻辑
  - [ ] Step 2.2.4: 测试质量评分计算

- [ ] Task 2.3: 分析服务测试
  - [ ] Step 2.3.1: 测试情感分析（mock SnowNLP）
  - [ ] Step 2.3.2: 测试关键词提取
  - [ ] Step 2.3.3: 测试趋势分析峰值检测

## Phase 3: 修复已知代码问题

- [ ] Task 3.1: 修复 run_full_analysis 同步调用问题
  - [ ] Step 3.1.1: 分析当前 run_full_analysis 的实现问题
  - [ ] Step 3.1.2: 改为串行调用各分析函数（非 Celery 任务版本）
  - [ ] Step 3.1.3: 验证修复后任务可正常执行

## Phase 4: Celery Beat 定时采集

- [ ] Task 4.1: 添加 Celery Beat 调度配置
  - [ ] Step 4.1.1: 在 app/tasks/__init__.py 中配置 beat_schedule
  - [ ] Step 4.1.2: 创建定时采集任务（扫描所有活跃关键词并触发采集）
  - [ ] Step 4.1.3: 创建定时分析任务

- [ ] Task 4.2: 添加定时任务管理 API
  - [ ] Step 4.2.1: 添加查看定时任务状态的接口
  - [ ] Step 4.2.2: 在仪表盘页面展示定时任务状态

## Phase 5: 验证与文档

- [ ] Task 5.1: 运行全部测试并确保通过
  - [ ] Step 5.1.1: pytest tests/ -v
  - [ ] Step 5.1.2: ruff check app/ tests/
  - [ ] Step 5.1.3: mypy app/

- [ ] Task 5.2: 更新 README.md
  - [ ] Step 5.2.1: 添加测试运行说明
  - [ ] Step 5.2.2: 添加 Celery Beat 启动说明
  - [ ] Step 5.2.3: 添加代码规范检查说明

# Task Dependencies

- Task 2.x 依赖 Task 1.3（测试框架）
- Task 3.1 依赖 Task 2.3（分析服务测试，确保修复不破坏功能）
- Task 4.x 依赖 Task 3.1（修复完成后添加定时调度）
- Task 5.x 依赖所有前置任务完成
