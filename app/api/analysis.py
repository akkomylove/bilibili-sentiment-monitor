from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.analysis import AnalysisResult
from app.services.daily_brief import build_daily_brief, build_report_data

router = APIRouter(prefix="/analysis", tags=["分析结果"])


def _get_latest_analysis(
    db: Session,
    analysis_type: str,
    ref_type: str | None = None,
    ref_id: str | None = None,
):
    """查询最新的分析结果，支持 keyword_ids 多选"""
    query = db.query(AnalysisResult).filter(AnalysisResult.analysis_type == analysis_type)
    if ref_type and ref_id:
        query = query.filter(
            AnalysisResult.ref_type == ref_type,
            AnalysisResult.ref_id == ref_id,
        )
    elif ref_type:
        query = query.filter(AnalysisResult.ref_type == ref_type)
    return query.order_by(AnalysisResult.analyzed_at.desc()).first()


@router.get("/sentiment", summary="情感分析结果")
def get_sentiment(
    video_bvid: str | None = Query(None),
    keyword_id: int | None = Query(None),
    keyword_ids: str | None = Query(None),
    db: Session = Depends(get_db),
):
    if video_bvid:
        result = _get_latest_analysis(db, "sentiment", ref_type="video", ref_id=video_bvid)
    elif keyword_ids:
        ids = [s.strip() for s in keyword_ids.split(",") if s.strip()]
        result = (
            db.query(AnalysisResult)
            .filter(
                AnalysisResult.analysis_type == "sentiment",
                AnalysisResult.ref_type == "keyword",
                AnalysisResult.ref_id.in_(ids),
            )
            .order_by(AnalysisResult.analyzed_at.desc())
            .first()
        )
    elif keyword_id:
        result = _get_latest_analysis(db, "sentiment", ref_type="keyword", ref_id=str(keyword_id))
    else:
        result = _get_latest_analysis(db, "sentiment", ref_type="global")
    if not result:
        return {"status": "no_data", "message": "暂无分析结果"}
    return result.result_data


@router.get("/keywords", summary="关键词提取结果")
def get_keywords(
    video_bvid: str | None = Query(None),
    keyword_id: int | None = Query(None),
    keyword_ids: str | None = Query(None),
    db: Session = Depends(get_db),
):
    if video_bvid:
        result = _get_latest_analysis(db, "keywords", ref_type="video", ref_id=video_bvid)
    elif keyword_ids:
        ids = [s.strip() for s in keyword_ids.split(",") if s.strip()]
        result = (
            db.query(AnalysisResult)
            .filter(
                AnalysisResult.analysis_type == "keywords",
                AnalysisResult.ref_type == "keyword",
                AnalysisResult.ref_id.in_(ids),
            )
            .order_by(AnalysisResult.analyzed_at.desc())
            .first()
        )
    elif keyword_id:
        result = _get_latest_analysis(db, "keywords", ref_type="keyword", ref_id=str(keyword_id))
    else:
        result = _get_latest_analysis(db, "keywords", ref_type="global")
    if not result:
        return {"status": "no_data", "message": "暂无分析结果"}
    return result.result_data


@router.get("/trend", summary="趋势分析数据")
def get_trend(
    keyword_id: int | None = Query(None),
    keyword_ids: str | None = Query(None),
    db: Session = Depends(get_db),
):
    if keyword_ids:
        ids = [s.strip() for s in keyword_ids.split(",") if s.strip()]
        result = (
            db.query(AnalysisResult)
            .filter(
                AnalysisResult.analysis_type == "trend",
                AnalysisResult.ref_type == "keyword",
                AnalysisResult.ref_id.in_(ids),
            )
            .order_by(AnalysisResult.analyzed_at.desc())
            .first()
        )
    elif keyword_id:
        result = _get_latest_analysis(db, "trend", ref_type="keyword", ref_id=str(keyword_id))
    else:
        result = _get_latest_analysis(db, "trend", ref_type="global")
    if not result:
        return {"status": "no_data", "message": "暂无分析结果"}
    return result.result_data


# === v2: 单页简报相关端点 ===

@router.get("/brief", summary="v2 简报文本（3-5 句中文）")
def get_brief(
    video_bvid: str | None = Query(None, description="可选：单视频简报"),
    keyword_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    """生成 3-5 句中文简报文本（基于 TemplateSummarizer）"""
    from app.services.summarizer.template import TemplateSummarizer

    from app.models.comment import Comment

    q = db.query(Comment)
    if video_bvid:
        q = q.filter(Comment.video_bvid == video_bvid)
    elif keyword_id:
        from app.models.video import Video
        q = q.join(Video, Comment.video_bvid == Video.bvid).filter(Video.keyword_id == keyword_id)
    comments = [
        {"rpid": c.rpid, "content": c.content or "", "like_count": c.like_count or 0}
        for c in q.all()
    ]
    summarizer = TemplateSummarizer(top_terms=8, top_insights=4)
    return {"summary": summarizer.summarize(comments)}


@router.get("/daily-brief", summary="v2 单页简报 JSON（前端 daily-brief.html 使用）")
def get_daily_brief(
    date: str | None = Query(None, description="兼容旧接口：单日 YYYY-MM-DD；等价于 start_date=end_date=date"),
    sector: str | None = Query(None, description="板块过滤：半导体/光通信/光芯片"),
    start_date: str | None = Query(None, description="区间起始日期 YYYY-MM-DD；与 date 互斥，date 优先"),
    end_date: str | None = Query(None, description="区间结束日期 YYYY-MM-DD；不传则到最新"),
    db: Session = Depends(get_db),
):
    """返回单页简报所需的完整 JSON（支持单日 / 时间段 / 全部）

    v2.1 时间段分析：
    - date=2026-06-09 → 单日（v2 旧行为）
    - start_date=2026-06-01&end_date=2026-06-09 → 区间
    - 仅 start_date → start_date 至最新
    - 仅 end_date → 最早至 end_date
    - 全不传 → 不过滤日期，返回所有监控视频

    单日模式下若当天无视频数据，回退到最近 7 天（保留 v2 旧行为）。
    """
    return build_daily_brief(
        db,
        date_str=date,
        start_str=start_date,
        end_str=end_date,
        sector=sector,
    )


@router.get("/report-daily", summary="v2.2 报告页数据：7 维度聚合（PPT 翻页 HTML 使用）")
def get_report_daily(
    date: str | None = Query(None, description="兼容旧接口：单日 YYYY-MM-DD"),
    sector: str | None = Query(None, description="板块过滤：半导体/光通信/光芯片"),
    start_date: str | None = Query(None, description="区间起始日期 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="区间结束日期 YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """返回 7 维度报告数据：
    - 核心简报（视频/评论/情感/板块）
    - 市场行情对比（板块涨跌幅 + 重点公司）
    - 评论时间分布（小时/天桶）
    - 风险/机会词信号
    - 舆情 vs 行情 对齐
    """
    return build_report_data(
        db,
        date_str=date,
        sector=sector,
        start_str=start_date,
        end_str=end_date,
    )
