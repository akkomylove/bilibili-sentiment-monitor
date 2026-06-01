"""
评论互动网络分析
分析评论之间的@提及和回复引用关系，构建用户互动网络
"""
import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.analysis import AnalysisResult
from app.models.comment import Comment

AT_PATTERN = re.compile(r"@(\S+?)(?:\s|$|，|。|！|？|,|\.|!|\?|\)|）)")
REPLY_PATTERN = re.compile(r"回复\s*@?(\S+?)(?:\s*:|：|\s|$)")


def _extract_mentions(content: str) -> list[str]:
    mentions: list[str] = []
    for match in AT_PATTERN.finditer(content):
        mention = match.group(1).strip()
        if len(mention) >= 2 and len(mention) <= 30:
            mentions.append(mention)
    if not mentions:
        for match in REPLY_PATTERN.finditer(content):
            mention = match.group(1).strip()
            if len(mention) >= 2 and len(mention) <= 30:
                mentions.append(mention)
    return mentions


def analyze_interaction_network(
    db: Session,
    video_bvid: str | None = None,
    top_n: int = 50,
) -> dict:
    query = db.query(Comment)
    if video_bvid:
        query = query.filter(Comment.video_bvid == video_bvid)
    comments = query.all()

    user_comments: dict[str, list[Comment]] = {}
    for c in comments:
        content = c.content or ""
        # 跳过回复评论（以[回复]开头的内容）
        if content.startswith("[回复"):
            continue
        mid = c.user_mid
        user_comments.setdefault(mid, []).append(c)

    user_stats: dict[str, dict] = {}
    for mid, user_cs in user_comments.items():
        total_likes = sum(c.like_count or 0 for c in user_cs)
        total_replies = sum(c.reply_count or 0 for c in user_cs)
        user_stats[mid] = {
            "mid": mid,
            "comment_count": len(user_cs),
            "total_likes": total_likes,
            "total_replies": total_replies,
            "influence_score": total_likes + total_replies * 2 + len(user_cs),
        }

    sorted_users = sorted(
        user_stats.values(),
        key=lambda x: x["influence_score"],
        reverse=True,
    )[:top_n]

    edges: list[dict] = []
    interaction_pairs: dict[tuple[str, str], int] = {}
    for comment in comments:
        mentions = _extract_mentions(comment.content or "")
        for target in mentions:
            for target_user in user_stats:
                if target in target_user or target_user in target:
                    pair = (comment.user_mid, target_user)
                    interaction_pairs[pair] = interaction_pairs.get(pair, 0) + 1
                    break

    for (source, target), weight in interaction_pairs.items():
        edges.append({
            "source": source,
            "target": target,
            "weight": weight,
        })

    nodes = [
        {
            "id": u["mid"],
            "comment_count": u["comment_count"],
            "influence_score": u["influence_score"],
            "symbolSize": min(60, max(10, u["influence_score"] / 5)),
        }
        for u in sorted_users
    ]

    total_users = len(user_stats)
    active_users = sum(1 for u in user_stats.values() if u["comment_count"] > 2)
    total_interactions = len(edges)

    result = {
        "total_users": total_users,
        "active_users": active_users,
        "total_interactions": total_interactions,
        "nodes": nodes,
        "edges": edges,
        "interaction_density": round(
            total_interactions / max(total_users * (total_users - 1) / 2, 1), 6
        ),
        "analyzed_at": datetime.now().isoformat(),
    }

    analysis_record = AnalysisResult(
        analysis_type="network",
        ref_type="video" if video_bvid else "global",
        ref_id=video_bvid or "global",
        result_data=result,
    )
    db.add(analysis_record)
    db.commit()
    return result
