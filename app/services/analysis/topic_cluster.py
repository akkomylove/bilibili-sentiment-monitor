"""
话题聚类分析
使用 TF-IDF + K-Means 对评论进行话题聚类
"""
from datetime import datetime

import jieba
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import TfidfVectorizer
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisResult
from app.models.comment import Comment

STOP_WORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
    "没有", "看", "好", "自己", "这", "那", "他", "她", "它", "们",
    "什么", "怎么", "为什么", "可以", "这个", "那个", "还是", "只是",
    "但是", "如果", "因为", "所以", "而且", "然后", "虽然", "不过",
    "已经", "不是", "就是", "真的", "觉得", "知道", "应该", "可能",
    "有点", "一点", "非常", "特别", "比较", "这么", "那么", "吧", "啊", "呢", "吗", "哦", "嗯", "哈", "呀", "嘛", "啦",
    "回复", "评论", "弹幕", "视频", "up", "up主", "作者", "大家", "感觉", "一下", "东西", "时候", "现在", "今天", "问题",
}

import re as _re
_NOISE_PATTERNS = [
    _re.compile(r"^\d+$"),
    _re.compile(r"^AV\d+$", _re.I),
    _re.compile(r"^BV[0-9A-Za-z]+$"),
    _re.compile(r"^[^\u4e00-\u9fa5a-zA-Z0-9]+$"),
    _re.compile(r"^\d+[秒分小时天年月]$"),
    _re.compile(r"^https?://.*"),
    _re.compile(r"^[a-zA-Z0-9]+\.(com|cn|net|org|io|tv)$"),
    _re.compile(r"^www\..*"),
    _re.compile(r"^[a-z]{1,4}$"),
    _re.compile(r"^\d+\.\d+$"),
    _re.compile(r"^b23\..*"),
    _re.compile(r"^[a-z]+_[a-z0-9]+$"),
    _re.compile(r"^\d+[gmk]b?$", _re.I),
    _re.compile(r"^[_\-].*"),
    _re.compile(r"^\d+_\d+$"),
    _re.compile(r"^[a-z]+[0-9]+[a-z]*$"),
]

_ENGLISH_STOP_WORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was", "one", "our", "out", "day", "get", "has", "him", "his", "how", "its", "may", "new", "now", "old", "see", "two", "who", "boy", "did", "she", "use", "her", "way", "many", "oil", "sit", "set", "run", "eat", "far", "sea", "eye", "ago", "off", "too", "any", "say", "man", "try", "ask", "end", "why", "let", "put", "say", "she", "try", "way", "own", "say", "too", "old", "tell", "very", "when", "much", "would", "there", "their", "what", "said", "each", "which", "will", "about", "could", "other", "after", "first", "never", "these", "think", "where", "being", "every", "great", "might", "shall", "still", "those", "while", "this", "that", "with", "have", "from", "they", "know", "want", "been", "good", "much", "some", "time", "very", "when", "come", "here", "just", "like", "long", "make", "many", "over", "such", "take", "than", "them", "well", "were",
}


def _tokenize(text: str) -> str:
    words = jieba.lcut(text)
    filtered = []
    for w in words:
        w = w.strip().lower()
        if len(w) < 2 or w in STOP_WORDS or w in _ENGLISH_STOP_WORDS:
            continue
        if any(p.match(w) for p in _NOISE_PATTERNS):
            continue
        filtered.append(w)
    return " ".join(filtered)


def _extract_topic_keywords(texts: list[str], labels: list[int], n_topics: int) -> list[dict]:
    from collections import Counter as _Counter
    topic_texts: dict[int, list[str]] = {i: [] for i in range(n_topics)}
    for text, label in zip(texts, labels, strict=True):
        topic_texts[label].append(text)

    topic_info: list[dict] = []
    for topic_id, t_texts in topic_texts.items():
        if not t_texts:
            topic_info.append({"topic_id": topic_id, "size": 0, "keywords": [], "sample_comments": []})
            continue

        # 使用词频统计提取关键词，优先中文词
        all_words: list[str] = []
        for text in t_texts:
            words = jieba.lcut(text)
            for w in words:
                w = w.strip().lower()
                if len(w) < 2 or w in STOP_WORDS or w in _ENGLISH_STOP_WORDS:
                    continue
                if any(p.match(w) for p in _NOISE_PATTERNS):
                    continue
                all_words.append(w)

        # 统计词频，优先保留中文词
        counter = _Counter(all_words)
        filtered_keywords: list[str] = []
        for word, count in counter.most_common(30):
            if len(filtered_keywords) >= 8:
                break
            # 优先中文词（至少包含一个中文字符）
            has_chinese = any("\u4e00" <= ch <= "\u9fff" for ch in word)
            if has_chinese or count >= 3:
                filtered_keywords.append(word)

        # 如果中文词不足，补充高频英文词
        if len(filtered_keywords) < 3:
            for word, count in counter.most_common(50):
                if word not in filtered_keywords:
                    filtered_keywords.append(word)
                if len(filtered_keywords) >= 5:
                    break

        sample_size = min(3, len(t_texts))
        samples = [t[:80] for t in t_texts[:sample_size]]

        topic_info.append({
            "topic_id": topic_id,
            "size": len(t_texts),
            "keywords": filtered_keywords,
            "sample_comments": samples,
        })

    topic_info.sort(key=lambda x: x["size"], reverse=True)
    return topic_info


def analyze_topic_cluster(
    db: Session,
    video_bvid: str | None = None,
    keyword_id: int | None = None,
    keyword_ids: list[int] | None = None,
    n_clusters: int | None = None,
) -> dict:
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

    ref_type = "video" if video_bvid else ("keyword" if keyword_id or keyword_ids else "global")
    ref_id = video_bvid or (str(keyword_id) if keyword_id else ("multi" if keyword_ids else "global"))

    if len(comments) < 10:
        result = {
            "total_comments": len(comments),
            "n_clusters": 0,
            "topics": [],
            "scatter_data": [],
            "insufficient_data": True,
            "analyzed_at": datetime.now().isoformat(),
        }
        analysis_record = AnalysisResult(
            analysis_type="topic_cluster",
            ref_type=ref_type,
            ref_id=ref_id,
            result_data=result,
        )
        db.add(analysis_record)
        db.commit()
        return result

    texts = []
    raw_texts = []
    for c in comments:
        content = c.content or ""
        # 跳过回复评论（以[回复]开头的内容）
        if content.startswith("[回复"):
            continue
        tokenized = _tokenize(content)
        if len(tokenized) > 3:
            texts.append(tokenized)
            raw_texts.append(content)

    if len(texts) < 10:
        result = {
            "total_comments": len(comments),
            "n_clusters": 0,
            "topics": [],
            "scatter_data": [],
            "insufficient_data": True,
            "analyzed_at": datetime.now().isoformat(),
        }
        analysis_record = AnalysisResult(
            analysis_type="topic_cluster",
            ref_type=ref_type,
            ref_id=ref_id,
            result_data=result,
        )
        db.add(analysis_record)
        db.commit()
        return result

    try:
        vectorizer = TfidfVectorizer(max_features=500)
        tfidf_matrix = vectorizer.fit_transform(texts)
    except Exception:
        result = {
            "total_comments": len(comments),
            "n_clusters": 0,
            "topics": [],
            "scatter_data": [],
            "insufficient_data": True,
            "analyzed_at": datetime.now().isoformat(),
        }
        analysis_record = AnalysisResult(
            analysis_type="topic_cluster",
            ref_type=ref_type,
            ref_id=ref_id,
            result_data=result,
        )
        db.add(analysis_record)
        db.commit()
        return result

    if n_clusters is None:
        n_clusters = min(max(3, len(texts) // 30), 10)

    try:
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
        labels = kmeans.fit_predict(tfidf_matrix)
    except Exception:
        result = {
            "total_comments": len(comments),
            "n_clusters": n_clusters,
            "topics": [],
            "scatter_data": [],
            "analyzed_at": datetime.now().isoformat(),
        }
        analysis_record = AnalysisResult(
            analysis_type="topic_cluster",
            ref_type=ref_type,
            ref_id=ref_id,
            result_data=result,
        )
        db.add(analysis_record)
        db.commit()
        return result

    topics = _extract_topic_keywords(raw_texts, labels.tolist(), n_clusters)

    scatter_data: list[dict] = []
    try:
        if tfidf_matrix.shape[0] >= 2 and tfidf_matrix.shape[1] >= 2:
            pca = PCA(n_components=2, random_state=42)
            coords = pca.fit_transform(tfidf_matrix.toarray())
            for i, (x, y) in enumerate(coords):
                scatter_data.append({
                    "x": round(float(x), 4),
                    "y": round(float(y), 4),
                    "topic": int(labels[i]),
                    "text": raw_texts[i][:30],
                })
    except Exception:
        pass

    result = {
        "total_comments": len(comments),
        "n_clusters": n_clusters,
        "topics": topics,
        "scatter_data": scatter_data,
        "insufficient_data": False,
        "analyzed_at": datetime.now().isoformat(),
    }

    analysis_record = AnalysisResult(
        analysis_type="topic_cluster",
        ref_type=ref_type,
        ref_id=ref_id,
        result_data=result,
    )
    db.add(analysis_record)
    db.commit()
    return result
