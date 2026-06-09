from collections import Counter
from datetime import datetime
from typing import Any, Iterable

import logging
import jieba

# 抑制 jieba 启动时的 "Building prefix dict..." / "Loading model..." 输出
jieba.setLogLevel(logging.ERROR)
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisResult
from app.models.comment import Comment
from app.services.analysis.investment_dict import STOP_TERMS, all_sector_terms

STOP_WORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
    "没有", "看", "好", "自己", "这", "那", "他", "她", "它", "们",
    "什么", "怎么", "为什么", "可以", "这个", "那个", "还是", "只是",
    "但是", "如果", "因为", "所以", "而且", "然后", "虽然", "不过",
} | STOP_TERMS  # 合并投资领域停用词

# 投资领域专业术语集合（用于加权或过滤）
SECTOR_TERM_SET: set[str] = set(all_sector_terms())

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


# === v2: 投资领域关键词提取（用于 daily_brief pipeline） ===

# 板块术语加权系数
_SECTOR_TERM_BOOST = 2.0


def _tokenize(text: str) -> list[str]:
    """分词 + 通用过滤（停用词、噪声、长度）"""
    if not text:
        return []
    if text.startswith("[回复"):
        return []
    words = jieba.lcut(text)
    out: list[str] = []
    for w in words:
        w = w.strip()
        if len(w) < 2 or w in STOP_WORDS:
            continue
        if any(p.match(w) for p in _NOISE_PATTERNS):
            continue
        out.append(w)
    return out


def extract_keywords_from_texts(
    texts: Iterable[str],
    top_n: int = 20,
    sector_only: bool = False,
    boost_sector: float = _SECTOR_TERM_BOOST,
) -> dict[str, Any]:
    """纯函数版关键词提取，用于 daily_brief pipeline / 端到端测试。

    Args:
        texts: 文本列表（评论 content 即可）。
        top_n: 返回 Top N 关键词。
        sector_only: 是否只保留 SECTOR_TERMS 中的术语。
        boost_sector: 板块术语在排序时的权重倍率，1.0=不加权。

    Returns:
        {
            "keywords": [{"word": str, "count": int, "sector_term": bool, "weight": float}, ...],
            "total_terms": int,
            "sector_term_count": int,
            "analyzed_at": str,
        }
    """
    counter: Counter = Counter()
    sector_counter: Counter = Counter()
    for text in texts:
        for w in _tokenize(text or ""):
            counter[w] += 1
            if w in SECTOR_TERM_SET:
                sector_counter[w] += 1

    if sector_only:
        ranked = sorted(
            sector_counter.items(),
            key=lambda kv: (kv[1] * boost_sector, kv[1]),
            reverse=True,
        )[:top_n]
        keywords = [
            {"word": w, "count": c, "sector_term": True, "weight": round(c * boost_sector, 2)}
            for w, c in ranked
        ]
        total_terms = sum(sector_counter.values())
        sector_term_count = len(sector_counter)
    else:
        # 加权排序：sector_term 出现 count 次时权重 = count * boost_sector
        weighted = []
        for w, c in counter.items():
            weight = c * (boost_sector if w in SECTOR_TERM_SET else 1.0)
            weighted.append((w, c, weight))
        weighted.sort(key=lambda x: (x[2], x[1]), reverse=True)
        keywords = [
            {"word": w, "count": c, "sector_term": w in SECTOR_TERM_SET, "weight": round(weight, 2)}
            for w, c, weight in weighted[:top_n]
        ]
        total_terms = sum(counter.values())
        sector_term_count = len(sector_counter)

    return {
        "keywords": keywords,
        "total_terms": total_terms,
        "sector_term_count": sector_term_count,
        "analyzed_at": datetime.now().isoformat(),
    }


def extract_keywords_v2(
    db: Session,
    video_bvid: str | None = None,
    keyword_id: int | None = None,
    keyword_ids: list[int] | None = None,
    top_n: int = 20,
    sector_only: bool = False,
) -> dict[str, Any]:
    """v2 关键词提取：增加 SECTOR_TERMS 加权与过滤，默认 Top 20。

    与 v1 (extract_keywords) 行为差异：
    - 默认 top_n 由 50 → 20
    - SECTOR_TERMS 命中项获得 boost_sector 加权
    - 支持 sector_only 仅返回板块术语
    """
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
    texts = [c.content or "" for c in comments]
    result = extract_keywords_from_texts(texts, top_n=top_n, sector_only=sector_only)

    ref_type = "video" if video_bvid else ("keyword" if keyword_id or keyword_ids else "global")
    ref_id = video_bvid or (str(keyword_id) if keyword_id else ("multi" if keyword_ids else "global"))
    analysis_record = AnalysisResult(
        analysis_type="keywords_v2",
        ref_type=ref_type,
        ref_id=ref_id,
        result_data=result,
    )
    db.add(analysis_record)
    db.commit()
    return result
