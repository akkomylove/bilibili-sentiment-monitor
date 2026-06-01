"""
弹幕密度与高潮点检测
分析视频弹幕在时间轴上的分布，识别弹幕高潮片段
"""
from collections import defaultdict
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.analysis import AnalysisResult
from app.models.danmaku import Danmaku


def analyze_danmaku_density(
    db: Session,
    video_bvid: str | None = None,
    interval_seconds: float = 5.0,
) -> dict:
    query = db.query(Danmaku)
    if video_bvid:
        query = query.filter(Danmaku.video_bvid == video_bvid)
    danmakus = query.order_by(Danmaku.timeline.asc()).all()

    if not danmakus:
        result = {
            "total_danmaku": 0,
            "video_duration": 0,
            "density_curve": [],
            "peak_segments": [],
            "peak_count": 0,
            "avg_density": 0,
            "max_density": 0,
            "analyzed_at": datetime.now().isoformat(),
        }
        analysis_record = AnalysisResult(
            analysis_type="danmaku_density",
            ref_type="video" if video_bvid else "global",
            ref_id=video_bvid or "global",
            result_data=result,
        )
        db.add(analysis_record)
        db.commit()
        return result

    max_timeline = max(float(d.timeline) for d in danmakus)
    total_danmaku = len(danmakus)

    buckets: dict[int, int] = defaultdict(int)
    for d in danmakus:
        bucket_key = int(float(d.timeline) // interval_seconds)
        buckets[bucket_key] += 1

    density_curve: list[dict] = []
    for key in sorted(buckets.keys()):
        start_time = round(key * interval_seconds, 1)
        end_time = round((key + 1) * interval_seconds, 1)
        density_curve.append({
            "start": start_time,
            "end": end_time,
            "count": buckets[key],
        })

    densities = [d["count"] for d in density_curve]
    avg_density = round(sum(densities) / len(densities), 2) if densities else 0
    max_density = max(densities) if densities else 0

    threshold = avg_density * 1.5 if avg_density > 0 else 0
    peak_segments: list[dict] = []
    for d in density_curve:
        if d["count"] >= threshold and d["count"] > 0:
            peak_segments.append(d)

    peak_segments.sort(key=lambda x: x["count"], reverse=True)

    peak_keywords: list[dict] = []
    peak_timelines = {seg["start"] for seg in peak_segments[:5]}
    for seg_start in peak_timelines:
        seg_end = seg_start + interval_seconds
        seg_danmakus = [
            d for d in danmakus
            if seg_start <= float(d.timeline) < seg_end
        ]
        segment_text = " ".join(d.content for d in seg_danmakus[:50])
        from collections import Counter
        words = [w.strip() for w in segment_text.split() if len(w.strip()) >= 2]
        word_counts = Counter(words).most_common(10)
        peak_keywords.append({
            "time": round(seg_start, 1),
            "top_words": [{"word": w, "count": c} for w, c in word_counts],
        })

    result = {
        "total_danmaku": total_danmaku,
        "video_duration": round(max_timeline, 1),
        "density_curve": density_curve,
        "peak_segments": peak_segments[:10],
        "peak_keywords": peak_keywords,
        "peak_count": len(peak_segments),
        "avg_density": avg_density,
        "max_density": max_density,
        "analyzed_at": datetime.now().isoformat(),
    }

    analysis_record = AnalysisResult(
        analysis_type="danmaku_density",
        ref_type="video" if video_bvid else "global",
        ref_id=video_bvid or "global",
        result_data=result,
    )
    db.add(analysis_record)
    db.commit()
    return result
