from collections import Counter
from datetime import datetime

import jieba
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisResult
from app.models.comment import Comment

STOP_WORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
    "没有", "看", "好", "自己", "这", "那", "他", "她", "它", "们",
    "什么", "怎么", "为什么", "可以", "这个", "那个", "还是", "只是",
    "但是", "如果", "因为", "所以", "而且", "然后", "虽然", "不过",
}

# 过滤纯数字、AV/BV号、纯符号等无意义词
import re as _re
_NOISE_PATTERNS = [
    _re.compile(r"^\d+$"),           # 纯数字
    _re.compile(r"^AV\d+$", _re.I),  # AV号
    _re.compile(r"^BV[0-9A-Za-z]+$"), # BV号
    _re.compile(r"^[^\u4e00-\u9fa5a-zA-Z0-9]+$"), # 纯符号
    _re.compile(r"^\d+[秒分小时天年月]$"), # 时间单位
]


def extract_keywords(db: Session, video_bvid: str | None = None, keyword_id: int | None = None, keyword_ids: list[int] | None = None, top_n: int = 50) -> dict:
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

    all_words: list[str] = []
    for comment in comments:
        content = comment.content or ""
        # 跳过回复评论（以[回复]开头的内容）
        if content.startswith("[回复"):
            continue
        words = jieba.lcut(content)
        for w in words:
            w = w.strip()
            if len(w) < 2 or w in STOP_WORDS:
                continue
            if any(p.match(w) for p in _NOISE_PATTERNS):
                continue
            all_words.append(w)

    counter = Counter(all_words)
    top_keywords = counter.most_common(top_n)
    keywords = [{"word": w, "count": c} for w, c in top_keywords]

    result = {
        "keywords": keywords,
        "total_terms": len(all_words),
        "analyzed_at": datetime.now().isoformat(),
    }

    ref_type = "video" if video_bvid else ("keyword" if keyword_id or keyword_ids else "global")
    ref_id = video_bvid or (str(keyword_id) if keyword_id else ("multi" if keyword_ids else "global"))
    analysis_record = AnalysisResult(
        analysis_type="keywords",
        ref_type=ref_type,
        ref_id=ref_id,
        result_data=result,
    )
    db.add(analysis_record)
    db.commit()
    return result
