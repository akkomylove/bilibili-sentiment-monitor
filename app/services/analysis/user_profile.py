from collections import Counter
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.analysis import AnalysisResult
from app.models.comment import Comment


def analyze_user_profile(db: Session, video_bvid: str | None = None) -> dict:
    query = db.query(Comment)
    if video_bvid:
        query = query.filter(Comment.video_bvid == video_bvid)
    comments = query.all()

    hour_counter: Counter[int] = Counter()
    user_activity: dict[str, dict] = {}

    for comment in comments:
        content = comment.content or ""
        # 跳过回复评论（以[回复]开头的内容）
        if content.startswith("[回复"):
            continue
        if comment.pub_time:
            try:
                hour = int(str(comment.pub_time).split(" ")[1].split(":")[0])
                hour_counter[hour] += 1
            except (ValueError, IndexError):
                pass

        mid = comment.user_mid
        if mid not in user_activity:
            user_activity[mid] = {"comment_count": 0, "total_likes": 0}
        user_activity[mid]["comment_count"] += 1
        user_activity[mid]["total_likes"] += comment.like_count or 0

    active_hours = [{"hour": h, "count": c} for h, c in sorted(hour_counter.items())]

    result = {
        "active_hours": active_hours,
        "total_users": len(user_activity),
        "top_active_users_count": sum(
            1 for u in user_activity.values() if u["comment_count"] > 5
        ),
        "analyzed_at": datetime.now().isoformat(),
    }

    analysis_record = AnalysisResult(
        analysis_type="user_profile",
        ref_type="video" if video_bvid else "global",
        ref_id=video_bvid or "global",
        result_data=result,
    )
    db.add(analysis_record)
    db.commit()
    return result
