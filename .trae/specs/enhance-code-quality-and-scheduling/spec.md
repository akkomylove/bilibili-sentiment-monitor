# B站舆情监控平台 — 代码质量提升与定时采集 Spec

## Why

当前项目功能完整但缺乏工程规范：无 requirements.txt、无测试、无类型检查、无代码风格统一。同时系统仅支持手动触发采集，缺少自动定时监控能力。本次升级旨在将项目从"功能可用"提升到"工程规范、可维护、可展示"的简历级项目水平。

## What Changes

- 新增/完善工程规范文件：requirements.txt、pyproject.toml（ruff/mypy配置）、pytest测试框架
- 添加核心模块的单元测试（爬虫、治理引擎、分析服务）
- 接入 Celery Beat 实现定时自动采集
- 修复已知代码问题（如 `run_full_analysis` 同步调用异步任务的问题）
- **BREAKING**: 无破坏性变更，所有修改向后兼容

## Impact

- 受影响代码：全部 Python 模块（主要新增测试和配置文件）
- 新增文件：requirements.txt、pyproject.toml、tests/ 目录、celery beat 调度配置
- 修改文件：app/tasks/analysis.py（修复 run_full_analysis）、app/tasks/__init__.py（添加 beat schedule）

## ADDED Requirements

### Requirement: 工程规范体系
The system SHALL 提供完整的 Python 工程规范文件，使项目可直接通过 `pip install -r requirements.txt` 安装并运行。

#### Scenario: 依赖安装
- **WHEN** 用户在新环境中克隆项目
- **THEN** 执行 `pip install -r requirements.txt` 可安装所有依赖

#### Scenario: 代码风格检查
- **WHEN** 开发者运行 `ruff check app/`
- **THEN** 无严重风格问题（允许合理例外）

#### Scenario: 类型检查
- **WHEN** 开发者运行 `mypy app/`
- **THEN** 核心模块无类型错误

### Requirement: 单元测试覆盖
The system SHALL 为核心业务模块提供单元测试，覆盖爬虫、治理引擎、分析服务的关键路径。

#### Scenario: 运行测试
- **WHEN** 执行 `pytest tests/ -v`
- **THEN** 所有测试通过，核心模块覆盖率 > 60%

### Requirement: Celery Beat 定时采集
The system SHALL 支持通过 Celery Beat 自动定时执行关键词监控采集任务。

#### Scenario: 自动采集启动
- **WHEN** 启动 Celery Beat (`celery -A app.tasks beat`)
- **THEN** 系统按配置的采集间隔自动触发关键词采集

#### Scenario: 定时分析
- **WHEN** 配置定时分析任务
- **THEN** 系统按设定周期自动执行全量分析

## MODIFIED Requirements

### Requirement: 修复 run_full_analysis 任务
**原问题**: `run_full_analysis` 直接同步调用其他 Celery 任务函数，导致任务在 Worker 进程内同步执行而非异步分发。
**修改后**: 使用 `celery.group` 或链式调用正确分发子任务，或改为串行调用各分析函数（非 Celery 任务版本）。

## REMOVED Requirements

无移除需求。
