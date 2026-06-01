from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.governance import GovernanceLog

router = APIRouter(prefix="/governance", tags=["数据治理"])


@router.get("/quality-report", summary="数据质量报告")
@router.get("/stats", summary="数据质量报告（兼容旧路径）")
def get_quality_report(db: Session = Depends(get_db)):
    from datetime import datetime

    from sqlalchemy import func

    from app.models.comment import Comment

    total = db.query(Comment).count()
    if total == 0:
        return {
            "total_records": 0,
            "completeness_rate": 0.0,
            "dedup_rate": 0.0,
            "anomaly_rate": 0.0,
            "timeliness_score": 0.0,
            "overall_score": 0.0,
            "generated_at": datetime.now().isoformat(),
        }

    null_count = db.query(Comment).filter(
        func.coalesce(Comment.content, "") == ""
    ).count()
    completeness = round((1 - null_count / total) * 100, 2)

    dedup_actions = db.query(GovernanceLog).filter(
        GovernanceLog.action == "dedup_remove"
    ).count()
    dedup_rate = round(min(dedup_actions / max(total, 1) * 100, 100), 2)

    truncate_actions = db.query(GovernanceLog).filter(
        GovernanceLog.action == "truncate"
    ).count()
    anomaly_rate = round(truncate_actions / max(total, 1) * 100, 2)

    overall = round((completeness * 0.4 + (100 - dedup_rate) * 0.3 + 95 * 0.3), 2)

    return {
        "total_records": total,
        "completeness_rate": completeness,
        "dedup_rate": dedup_rate,
        "anomaly_rate": anomaly_rate,
        "timeliness_score": 95.0,
        "overall_score": overall,
        "generated_at": datetime.now().isoformat(),
    }


@router.get("/lineage", summary="数据血缘查询")
def get_lineage(
    source_type: str | None = Query(None),
    source_id: str | None = Query(None),
    db: Session = Depends(get_db),
):
    from app.models.governance import DataLineage

    query = db.query(DataLineage)
    if source_type:
        query = query.filter(DataLineage.source_type == source_type)
    if source_id:
        query = query.filter(DataLineage.source_id == source_id)
    items = query.order_by(DataLineage.executed_at.desc()).limit(100).all()
    return [
        {
            "id": item.id,
            "source_type": item.source_type,
            "source_id": item.source_id,
            "target_type": item.target_type,
            "target_id": item.target_id,
            "transform_step": item.transform_step,
            "executed_at": str(item.executed_at) if item.executed_at else "",
        }
        for item in items
    ]


@router.get("/logs", summary="治理操作日志")
def get_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items = (
        db.query(GovernanceLog)
        .order_by(GovernanceLog.executed_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return [
        {
            "id": item.id,
            "target_type": item.target_type,
            "target_id": item.target_id,
            "rule_id": item.rule_id,
            "action": item.action,
            "before_value": item.before_value,
            "after_value": item.after_value,
            "executed_at": str(item.executed_at) if item.executed_at else "",
        }
        for item in items
    ]


@router.get("/rules", summary="治理规则列表")
def list_rules(db: Session = Depends(get_db)):
    from app.models.governance import GovernanceRule

    items = db.query(GovernanceRule).order_by(GovernanceRule.created_at.desc()).all()
    return [
        {
            "id": item.id,
            "rule_name": item.rule_name,
            "rule_type": item.rule_type,
            "rule_config": item.rule_config,
            "phase": item.phase,
            "is_active": item.is_active,
            "created_at": str(item.created_at) if item.created_at else "",
        }
        for item in items
    ]


@router.post("/rules", status_code=201, summary="新增治理规则")
def create_rule(
    rule_name: str = Query(...),
    rule_type: str = Query(...),
    phase: str = Query(...),
    rule_config: str | None = Query(None),
    db: Session = Depends(get_db),
):
    import json

    from app.models.governance import GovernanceRule

    config_data = None
    if rule_config:
        try:
            config_data = json.loads(rule_config)
        except json.JSONDecodeError:
            config_data = {"raw": rule_config}

    rule = GovernanceRule(
        rule_name=rule_name,
        rule_type=rule_type,
        rule_config=config_data,
        phase=phase,
        is_active=True,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {
        "id": rule.id,
        "rule_name": rule.rule_name,
        "rule_type": rule.rule_type,
        "phase": rule.phase,
        "is_active": rule.is_active,
        "created_at": str(rule.created_at) if rule.created_at else "",
    }


@router.delete("/rules/{rule_id}", status_code=204, summary="删除治理规则")
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    from app.models.governance import GovernanceRule
    rule = db.query(GovernanceRule).filter(GovernanceRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    db.delete(rule)
    db.commit()


@router.put("/rules/{rule_id}/toggle", summary="切换规则启用状态")
def toggle_rule(rule_id: int, db: Session = Depends(get_db)):
    from app.models.governance import GovernanceRule
    rule = db.query(GovernanceRule).filter(GovernanceRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    rule.is_active = not rule.is_active
    db.commit()
    return {"id": rule.id, "is_active": rule.is_active}


@router.post("/trigger", summary="触发治理流水线")
def trigger_governance(
    video_bvid: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    from app.services.governance.engine import execute_governance_pipeline
    result = execute_governance_pipeline(db, video_bvid=video_bvid)
    return {
        "status": "completed",
        "results": result["phases"],
        "scanned_total": result["scanned_total"],
        "total_processed": result["total_processed"],
    }
