import csv
import io
import json
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.analysis import AnalysisResult
from app.models.comment import Comment
from app.models.video import Video

router = APIRouter(prefix="/export", tags=["数据导出"])


@router.get("/report/csv", summary="导出评论CSV报告")
def export_comments_csv(
    video_bvid: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Comment)
    if video_bvid:
        query = query.filter(Comment.video_bvid == video_bvid)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["rpid", "video_bvid", "user_mid", "content", "like_count", "reply_count", "has_image", "pub_time"])
    for c in query.order_by(Comment.created_at.desc()).limit(10000).all():
        writer.writerow([
            c.rpid, c.video_bvid, c.user_mid,
            (c.content or "")[:500].replace("\n", " "),
            c.like_count, c.reply_count, c.has_image,
            str(c.pub_time) if c.pub_time else "",
        ])

    output.seek(0)
    filename = f"comments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        output,
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/report/json", summary="导出综合分析JSON报告")
def export_report_json(
    video_bvid: str | None = Query(None),
    db: Session = Depends(get_db),
):
    video_info = None
    if video_bvid:
        video_info = db.query(Video).filter(Video.bvid == video_bvid).first()

    analysis_results = {}
    for analysis_type in ["sentiment", "keywords", "trend", "user_profile", "topic_cluster", "network"]:
        query = db.query(AnalysisResult).filter(AnalysisResult.analysis_type == analysis_type)
        if video_bvid:
            query = query.filter(AnalysisResult.ref_id == video_bvid)
        result = query.order_by(AnalysisResult.analyzed_at.desc()).first()
        if result and result.result_data:
            analysis_results[analysis_type] = result.result_data

    comment_count = db.query(Comment).count()
    if video_bvid:
        comment_count = db.query(Comment).filter(Comment.video_bvid == video_bvid).count()

    report = {
        "report_title": "舆情分析报告",
        "generated_at": datetime.now().isoformat(),
        "target": video_bvid or "全局",
        "video_info": {
            "bvid": video_info.bvid if video_info else None,
            "title": video_info.title if video_info else None,
            "play_count": video_info.play_count if video_info else None,
            "comment_count": video_info.comment_count if video_info else comment_count,
        },
        "analysis": analysis_results,
        "summary": {
            "total_comments": comment_count,
            "analysis_dimensions_completed": len(analysis_results),
        },
    }

    filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    return StreamingResponse(
        io.StringIO(json.dumps(report, ensure_ascii=False, indent=2)),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/report/excel-summary", summary="导出Excel风格摘要CSV")
def export_excel_summary(
    video_bvid: str | None = Query(None),
    db: Session = Depends(get_db),
):
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["=== 舆情分析摘要报告 ==="])
    writer.writerow(["生成时间", datetime.now().isoformat()])
    writer.writerow(["分析目标", video_bvid or "全局"])
    writer.writerow([])

    query = db.query(Comment)
    if video_bvid:
        query = query.filter(Comment.video_bvid == video_bvid)
    total = query.count()
    writer.writerow(["总评论数", total])
    writer.writerow([])

    writer.writerow(["分析维度", "状态"])
    for analysis_type in ["sentiment", "keywords", "trend", "user_profile", "topic_cluster", "network"]:
        aq = db.query(AnalysisResult).filter(AnalysisResult.analysis_type == analysis_type)
        if video_bvid:
            aq = aq.filter(AnalysisResult.ref_id == video_bvid)
        result = aq.first()
        writer.writerow([analysis_type, "已完成" if result else "未完成"])

    output.seek(0)
    filename = f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        output,
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
