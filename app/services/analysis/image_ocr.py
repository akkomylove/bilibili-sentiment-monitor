"""
图片评论OCR分析（已降级为占位实现）

原 easyocr 实现因 PyTorch 内存占用过大（~500MB+）已被移除。
图片OCR非平台核心功能，现返回空结果以保持API兼容。
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.analysis import AnalysisResult
from app.models.comment import Comment


HAS_OCR = False


def analyze_image_comments(db: Session, video_bvid: str | None = None) -> dict:
    query = db.query(Comment).filter(Comment.has_image)
    if video_bvid:
        query = query.filter(Comment.video_bvid == video_bvid)
    image_comments = query.all()

    total_comments = db.query(Comment)
    if video_bvid:
        total_comments = total_comments.filter(Comment.video_bvid == video_bvid)
    total_comments_count = total_comments.count()

    result = {
        "total_comments": total_comments_count,
        "image_comment_count": len(image_comments),
        "image_ratio": round(len(image_comments) / max(total_comments_count, 1), 4),
        "ocr_success_count": 0,
        "ocr_fail_count": 0,
        "ocr_top_words": [],
        "ocr_available": False,
        "ocr_disabled_reason": "图片OCR功能已禁用（PyTorch内存占用过大）",
        "analyzed_at": datetime.now().isoformat(),
    }

    analysis_record = AnalysisResult(
        analysis_type="image_ocr",
        ref_type="video" if video_bvid else "global",
        ref_id=video_bvid or "global",
        result_data=result,
    )
    db.add(analysis_record)
    db.commit()
    return result
