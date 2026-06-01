import re

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.governance import DataLineage, GovernanceLog, GovernanceRule

SALT = "bilibili_sentiment_salt_2026"

SENSITIVE_PATTERNS = {
    "phone": re.compile(r"1[3-9]\d{9}"),
    "id_card": re.compile(r"\d{17}[\dXx]"),
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
}


def run_format_check(db: Session, rules: list[GovernanceRule], video_bvid: str | None = None) -> int:
    count = 0
    query = db.query(Comment).filter(Comment.content.isnot(None))
    if video_bvid:
        query = query.filter(Comment.video_bvid == video_bvid)
    comments = query.all()
    for comment in comments:
        content = comment.content or ""
        if len(content) > 2000:
            comment.content = content[:2000]
            db.add(GovernanceLog(
                target_type="comments",
                target_id=comment.id,
                action="truncate",
                before_value={"content": content},
                after_value={"content": comment.content},
            ))
            count += 1
    db.commit()
    return count


def run_dedup(db: Session, rules: list[GovernanceRule], video_bvid: str | None = None) -> int:
    count = 0
    base_query = db.query(Comment)
    if video_bvid:
        base_query = base_query.filter(Comment.video_bvid == video_bvid)
    query = (
        base_query.with_entities(
            Comment.content,
            Comment.user_mid,
            func.count(Comment.id).label("cnt"),
        )
        .group_by(Comment.content, Comment.user_mid)
        .having(func.count(Comment.id) > 1)
    )
    duplicates = query.all()
    for dup in duplicates:
        records_query = (
            db.query(Comment)
            .filter(
                Comment.content == dup.content,
                Comment.user_mid == dup.user_mid,
            )
            .order_by(Comment.id.asc())
        )
        if video_bvid:
            records_query = records_query.filter(Comment.video_bvid == video_bvid)
        records = records_query.all()
        keep = records[0]
        for record in records[1:]:
            db.add(GovernanceLog(
                target_type="comments",
                target_id=record.id,
                action="dedup_remove",
                before_value={"rpid": record.rpid},
                after_value={"kept_rpid": keep.rpid},
            ))
            db.delete(record)
            count += 1
    db.commit()
    return count


def run_desensitize(db: Session, rules: list[GovernanceRule], video_bvid: str | None = None) -> int:
    count = 0
    query = db.query(Comment)
    if video_bvid:
        query = query.filter(Comment.video_bvid == video_bvid)
    comments = query.all()
    for comment in comments:
        before_content = comment.content
        new_content = before_content
        for name, pattern in SENSITIVE_PATTERNS.items():
            new_content = pattern.sub(f"[{name}]", new_content)
        if new_content != before_content:
            db.add(GovernanceLog(
                target_type="comments",
                target_id=comment.id,
                action="desensitize",
                before_value={"content": before_content},
                after_value={"content": new_content},
            ))
            comment.content = new_content
            count += 1
    db.commit()
    return count


def run_data_cleaning(db: Session, rules: list[GovernanceRule], video_bvid: str | None = None) -> int:
    count = 0
    html_pattern = re.compile(r"<[^>]+>")
    query = db.query(Comment)
    if video_bvid:
        query = query.filter(Comment.video_bvid == video_bvid)
    comments = query.all()
    for comment in comments:
        before = comment.content
        cleaned = html_pattern.sub("", before)
        cleaned = cleaned.strip()
        if cleaned != before:
            db.add(GovernanceLog(
                target_type="comments",
                target_id=comment.id,
                action="clean",
                before_value={"content": before},
                after_value={"content": cleaned},
            ))
            comment.content = cleaned
            count += 1
    db.commit()
    return count


def record_lineage(
    db: Session,
    source_type: str,
    source_id: str,
    target_type: str,
    target_id: str,
    step: str,
):
    lineage = DataLineage(
        source_type=source_type,
        source_id=source_id,
        target_type=target_type,
        target_id=target_id,
        transform_step=step,
    )
    db.add(lineage)
    db.commit()


def compute_quality_report(db: Session) -> dict:
    total = db.query(Comment).count()
    if total == 0:
        return {
            "total_records": 0,
            "completeness_rate": 0.0,
            "dedup_rate": 0.0,
            "anomaly_rate": 0.0,
            "timeliness_score": 0.0,
            "overall_score": 0.0,
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

    timeliness = 95.0
    overall = round((completeness * 0.4 + (100 - dedup_rate) * 0.3 + timeliness * 0.3), 2)

    return {
        "total_records": total,
        "completeness_rate": completeness,
        "dedup_rate": dedup_rate,
        "anomaly_rate": anomaly_rate,
        "timeliness_score": timeliness,
        "overall_score": overall,
    }


PHASE_HANDLERS = {
    "format_check": run_format_check,
    "dedup": run_dedup,
    "desensitize": run_desensitize,
    "clean": run_data_cleaning,
}

PHASE_LABELS = {
    "format_check": "接入校验",
    "dedup": "去重处理",
    "clean": "数据清洗",
    "desensitize": "敏感信息脱敏",
}


def execute_governance_pipeline(db: Session, video_bvid: str | None = None) -> dict:
    """执行治理流水线

    Args:
        video_bvid: 指定要治理的视频BVID，为 None 时治理所有评论

    Returns:
        dict: 包含各阶段处理数量和扫描总数的详细结果
    """
    active_rules = db.query(GovernanceRule).filter(GovernanceRule.is_active).all()
    results: dict[str, any] = {"scanned_total": 0, "phases": {}}
    previous_phase = "raw_comments"

    # 统计扫描总数
    scan_query = db.query(Comment)
    if video_bvid:
        scan_query = scan_query.filter(Comment.video_bvid == video_bvid)
    results["scanned_total"] = scan_query.count()

    record_lineage(
        db,
        source_type="comments",
        source_id="bilibili_api",
        target_type="comments",
        target_id=previous_phase,
        step="评论数据采集",
    )

    for phase in ["format_check", "dedup", "clean", "desensitize"]:
        phase_rules = [r for r in active_rules if r.phase == phase]
        handler = PHASE_HANDLERS.get(phase)
        if handler and phase_rules:
            count = handler(db, phase_rules, video_bvid=video_bvid)
            results["phases"][phase] = {
                "processed": count,
                "label": PHASE_LABELS.get(phase, phase),
                "status": "executed",
            }

            record_lineage(
                db,
                source_type="comments",
                source_id=previous_phase,
                target_type="comments",
                target_id=phase,
                step=PHASE_LABELS.get(phase, phase) + f" ({count}条)",
            )
            previous_phase = phase
        else:
            results["phases"][phase] = {
                "processed": 0,
                "label": PHASE_LABELS.get(phase, phase),
                "status": "skipped",
            }
            record_lineage(
                db,
                source_type="comments",
                source_id=previous_phase,
                target_type="comments",
                target_id=phase,
                step=PHASE_LABELS.get(phase, phase) + "(无规则/跳过)",
            )
            previous_phase = phase

    total_processed = sum(p["processed"] for p in results["phases"].values())
    results["total_processed"] = total_processed

    record_lineage(
        db,
        source_type="comments",
        source_id=previous_phase,
        target_type="analysis",
        target_id="ready",
        step=f"数据就绪 (共处理{total_processed}条)",
    )

    return results
