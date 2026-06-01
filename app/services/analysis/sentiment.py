import math
from datetime import datetime

from snownlp import SnowNLP
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisResult
from app.models.comment import Comment


def _calc_weight(like_count: int) -> float:
    """根据点赞数计算评论权重

    权重公式: 1 + ln(like_count + 1)
    - 0赞: 权重 1.0
    - 10赞: 权重 3.4
    - 100赞: 权重 5.6
    - 1000赞: 权重 7.9
    使用对数压缩避免极端高赞评论主导结果
    """
    return 1.0 + math.log1p(like_count)


def analyze_sentiment(db: Session, video_bvid: str | None = None, keyword_id: int | None = None, keyword_ids: list[int] | None = None) -> dict:
    query = db.query(Comment)
    if video_bvid:
        query = query.filter(Comment.video_bvid == video_bvid)
    elif keyword_ids:
        from app.models.video import Video
        query = query.join(Video, Comment.video_bvid == Video.bvid).filter(
            Video.keyword_id.in_(keyword_ids)
        )
    elif keyword_id:
        from app.models.video import Video
        query = query.join(Video, Comment.video_bvid == Video.bvid).filter(Video.keyword_id == keyword_id)
    comments = query.all()

    positive_weight = 0.0
    neutral_weight = 0.0
    negative_weight = 0.0
    total_weight = 0.0
    trend_data: list[dict] = []

    for comment in comments:
        content = comment.content or ""
        # 跳过回复评论（以[回复]开头的内容）
        if content.startswith("[回复"):
            continue
        if not content.strip():
            weight = _calc_weight(comment.like_count or 0)
            neutral_weight += weight
            total_weight += weight
            continue
        try:
            score = SnowNLP(content).sentiments
        except Exception:
            score = 0.5

        weight = _calc_weight(comment.like_count or 0)
        total_weight += weight

        label = "positive" if score > 0.6 else ("negative" if score < 0.4 else "neutral")
        if label == "positive":
            positive_weight += weight
        elif label == "negative":
            negative_weight += weight
        else:
            neutral_weight += weight

        if comment.pub_time:
            trend_data.append({
                "time": str(comment.pub_time)[:10],
                "sentiment": score,
                "label": label,
                "weight": round(weight, 2),
            })

    result = {
        "positive_ratio": round(positive_weight / max(total_weight, 1.0), 4),
        "neutral_ratio": round(neutral_weight / max(total_weight, 1.0), 4),
        "negative_ratio": round(negative_weight / max(total_weight, 1.0), 4),
        "total_samples": len(comments),
        "total_weight": round(total_weight, 2),
        "trend_data": trend_data,
        "analyzed_at": datetime.now().isoformat(),
    }

    ref_type = "video" if video_bvid else ("keyword" if keyword_id or keyword_ids else "global")
    ref_id = video_bvid or (str(keyword_id) if keyword_id else ("multi" if keyword_ids else "global"))
    analysis_record = AnalysisResult(
        analysis_type="sentiment",
        ref_type=ref_type,
        ref_id=ref_id,
        result_data=result,
    )
    db.add(analysis_record)
    db.commit()
    return result
