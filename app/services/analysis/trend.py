from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisResult
from app.models.comment import Comment


def analyze_trend(db: Session, keyword_id: int | None = None) -> dict:
    query = db.query(
        func.date(Comment.pub_time).label("date"),
        func.count(Comment.id).label("count"),
    )
    if keyword_id:
        from app.models.video import Video
        query = query.join(Video, Comment.video_bvid == Video.bvid).filter(
            Video.keyword_id == keyword_id,
            ~Comment.content.startswith("[回复")
        )
    else:
        query = query.filter(~Comment.content.startswith("[回复"))
    results = query.group_by(func.date(Comment.pub_time)).order_by("date").all()

    time_series = [{"date": str(r.date), "count": r.count} for r in results]

    peak_points: list[dict] = []
    if len(time_series) >= 3:
        for i in range(1, len(time_series) - 1):
            if (
                time_series[i]["count"] > time_series[i - 1]["count"]
                and time_series[i]["count"] > time_series[i + 1]["count"]
            ):
                peak_points.append(time_series[i])

    result = {
        "time_series": time_series,
        "peak_points": peak_points,
        "analyzed_at": datetime.now().isoformat(),
    }

    analysis_record = AnalysisResult(
        analysis_type="trend",
        ref_type="keyword",
        ref_id=str(keyword_id) if keyword_id else "global",
        result_data=result,
    )
    db.add(analysis_record)
    db.commit()
    return result
