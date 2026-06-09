"""每日简报聚合（daily_brief.py - v2.1）

为 daily_brief.html 提供统一的 JSON 输出（专注大方向分析）：
- 4 个核心统计卡（监控视频/评论/正面占比/整体情绪）
- 整体情感 + 5 档情绪标签
- 各板块情感饼图
- AI 风格多视角摘要（板块聚焦 + 关键观点 + 行业术语热度）

v2.1 移除：Top 10 视频（用户反馈热门排行不准确）、关键词云、Mock 涨跌幅
v2.2 新增（报告页使用）：市场行情对比、评论时间分布、风险/机会词信号
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.video import Video
from app.services.analysis.investment_dict import (
    SECTOR_TERMS,
    SENTIMENT_BEARISH,
    SENTIMENT_BULLISH,
)
from app.services.analysis.sentiment_v2 import analyze_sentiment_v2
from app.services.market import get_market_data
from app.services.summarizer.template import TemplateSummarizer


def _mood_label(pos: float, neg: float) -> str:
    """根据正面/负面占比给出整体情绪标签

    输入为 0-100 范围的百分比（不是 0-1 比例），与 build_daily_brief 中的 pos/neg 变量保持一致。
    """
    diff = pos - neg
    if pos >= 55 and diff >= 5:
        return "偏正面"
    if neg >= 40 and diff <= -5:
        return "偏负面"
    if abs(diff) < 5:
        return "中性"
    if pos > neg:
        return "略偏正面"
    return "略偏负面"


def _filter_videos_by_date(
    db: Session,
    date_str: str,
    sector: str | None = None,
) -> list[Video]:
    """按单日筛选视频（v2 兼容接口）

    内部调用 _filter_videos_by_range，保持逻辑统一。
    """
    return _filter_videos_by_range(db, start_str=date_str, end_str=date_str, sector=sector)


def _filter_videos_by_range(
    db: Session,
    start_str: str | None = None,
    end_str: str | None = None,
    sector: str | None = None,
) -> tuple[list[Video], bool]:
    """按发布日期区间筛选视频（v2.1 时间段分析）

    Returns:
        (videos, did_fallback) 元组；did_fallback=True 表示单日 0 数据走了 7 天回退

    规则：
    1. 只显示来自"当前活跃"监控关键词的视频（is_active=1）
    2. start/end 解析为 [start 00:00, end+1 00:00) 半开区间
    3. start/end 同时为 None：不按日期过滤，返回所有监控视频
    4. start 为 None / end 有值：从最早到 end+1
    5. end 为 None / start 有值：从 start 到最新
    6. 仅当 start==end（单日）且 0 视频时，回退到最近 7 天（保留旧行为）
    7. 区间模式不做回退，0 视频就 0 视频
    """
    from app.models.monitor import MonitorKeyword
    q = (
        db.query(Video)
        .join(MonitorKeyword, Video.keyword_id == MonitorKeyword.id)
        .filter(MonitorKeyword.is_active == 1)
    )

    start_day: datetime | None = None
    end_day: datetime | None = None
    did_fallback = False

    if start_str:
        try:
            start_day = datetime.strptime(start_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            start_day = None
    if end_str:
        try:
            end_day = datetime.strptime(end_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            end_day = None

    # 单日：start == end
    if start_day and end_day and start_day == end_day:
        start = start_day.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        day_q = q.filter(and_(Video.pub_time >= start, Video.pub_time < end))
        if day_q.count() > 0:
            q = day_q
        else:
            # 单日 0 数据时回退到最近 7 天（旧行为）
            seven_days_ago = datetime.now() - timedelta(days=7)
            q = q.filter(Video.pub_time >= seven_days_ago)
            did_fallback = True
    elif start_day or end_day:
        # 区间模式
        if start_day:
            start_dt = start_day.replace(hour=0, minute=0, second=0, microsecond=0)
            q = q.filter(Video.pub_time >= start_dt)
        if end_day:
            end_dt = end_day.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            q = q.filter(Video.pub_time < end_dt)
    # else: start/end 都为 None → 不过滤日期

    videos = q.order_by(Video.play_count.desc()).all()

    if sector:
        # 板块过滤：视频关键词属于该板块，或 partition_tag 包含板块名
        videos = [
            v for v in videos
            if v.partition_tag == sector
            or sector in (v.title or "")
            or any(kw in (v.title or "") for kw in SECTOR_TERMS.get(sector, []))
        ]
    return videos, did_fallback


def _comments_for_videos(db: Session, videos: list[Video]) -> list[dict[str, Any]]:
    """获取这些视频下的所有评论（仅顶级评论）"""
    if not videos:
        return []
    bvids = [v.bvid for v in videos]
    comments = (
        db.query(Comment)
        .filter(Comment.video_bvid.in_(bvids))
        .filter(Comment.parent_rpid == 0)  # 只取顶级评论
        .all()
    )
    return [
        {
            "rpid": c.rpid,
            "content": c.content or "",
            "like_count": c.like_count or 0,
            "video_bvid": c.video_bvid,
            "pub_time": c.pub_time.isoformat() if c.pub_time else None,
        }
        for c in comments
    ]


# === v2.2 新增：报告页专用维度 ===

# 监控 3 大板块对应的重点公司清单
# (板块, 公司名, 股票代码) — 股票代码用于 akshare 实时拉取
_FOCUS_COMPANIES = [
    # (板块, 公司名, 股票代码)
    ("光通信", "中际旭创", "300308"),
    ("光通信", "新易盛", "300502"),
    ("光通信", "天孚通信", "300394"),
    ("半导体", "中芯国际", "688981"),
    ("光芯片", "长光华芯", "688048"),
    ("光芯片", "源杰科技", "688498"),
]


def _market_snapshot(date_str: str) -> dict[str, Any]:
    """获取指定日期的市场行情快照（板块 + 重点公司）

    数据源优先级：AKShare 实时 + 本地缓存 → 不命中则 Mock 兜底

    Args:
        date_str: YYYY-MM-DD

    Returns:
        {
            "market_date": "2026-06-09",
            "sector_perf": { "半导体": -2.3, "光通信": +1.5, ... },
            "company_quotes": [
                {"sector": "光通信", "name": "中际旭创", "code": "300308",
                 "open": 142.5, "close": 148.6, "high": 150.2, "low": 140.3,
                 "pct_chg": +4.28, "price": 148.6, "prev_close": 142.5},
                ...
            ],
            "is_mock": False,  # True = 全部 Mock 兜底；False = 至少部分是真实数据
        }
    """
    from app.services.market import AKShareMarketData, MockMarketData

    real = AKShareMarketData()
    mock = MockMarketData()

    sector_perf_real = real.get_sector_perf(date_str)
    sector_perf = sector_perf_real if sector_perf_real else mock.get_sector_perf(date_str)

    quotes: list[dict[str, Any]] = []
    any_real = bool(sector_perf_real)
    for sec, name, code in _FOCUS_COMPANIES:
        q = real.get_company_quote(code, date_str)
        if not q:
            q = mock.get_company_quote(name, date_str)
        if q:
            q["sector"] = sec
            q["name"] = name
            q["code"] = code
            quotes.append(q)
            # 真数据有 prev_close + timestamp，mock 没有
            if q.get("timestamp"):
                any_real = True
    return {
        "market_date": date_str,
        "sector_perf": sector_perf,
        "company_quotes": quotes,
        "is_mock": not any_real,
    }


def _comment_time_distribution(
    comments: list[dict[str, Any]],
    start_str: str | None,
    end_str: str | None,
) -> dict[str, Any]:
    """评论时间分布：按小时（≤2天）或按天聚合

    Returns:
        {
            "granularity": "hour" | "day",
            "buckets": [
                {"label": "00" 或 "2026-06-09", "count": 50,
                 "positive": 30, "neutral": 15, "negative": 5,
                 "positive_pct": 60.0, "negative_pct": 10.0},
                ...
            ],
            "peak_bucket": "18" 或 "2026-06-09",
            "total": 500,
        }
    """
    # 决定粒度
    use_hour = False
    if start_str and end_str and start_str == end_str:
        use_hour = True
    elif start_str and end_str:
        try:
            s = datetime.strptime(start_str, "%Y-%m-%d")
            e = datetime.strptime(end_str, "%Y-%m-%d")
            if (e - s).days <= 2:
                use_hour = True
        except ValueError:
            pass

    # 按桶聚合
    bucket_data: dict[str, dict[str, int]] = defaultdict(
        lambda: {"count": 0, "positive": 0, "neutral": 0, "negative": 0}
    )

    def _classify(text: str) -> str:
        for w in SENTIMENT_BULLISH:
            if w in text:
                return "positive"
        for w in SENTIMENT_BEARISH:
            if w in text:
                return "negative"
        return "neutral"

    # 30 天上限：如果评论时间跨度 > 30 天，截到最近 30 天，避免 8 年跨度
    # （前端已默认 7 天，30 天是保险；带 start_date 的请求不受影响）
    parsed_times: list[datetime] = []
    for c in comments:
        pt = c.get("pub_time")
        if not pt:
            continue
        try:
            parsed_times.append(datetime.fromisoformat(str(pt).replace("Z", "")))
        except (ValueError, TypeError):
            continue
    cutoff: datetime | None = None
    if parsed_times and not use_hour:
        max_dt = max(parsed_times)
        min_dt = min(parsed_times)
        if (max_dt - min_dt).days > 30:
            cutoff = max_dt - timedelta(days=30)

    for c in comments:
        pt = c.get("pub_time")
        if not pt:
            continue
        try:
            dt = datetime.fromisoformat(str(pt).replace("Z", ""))
        except (ValueError, TypeError):
            continue
        if cutoff is not None and dt < cutoff:
            continue
        if use_hour:
            label = f"{dt.hour:02d}"
        else:
            label = dt.strftime("%Y-%m-%d")
        text = (c.get("content") or "").strip()
        if not text:
            continue
        bucket = bucket_data[label]
        bucket["count"] += 1
        bucket[_classify(text)] += 1

    # 排序并构造输出
    if use_hour:
        ordered_labels = [f"{h:02d}" for h in range(24)]
    else:
        ordered_labels = sorted(bucket_data.keys())

    buckets: list[dict[str, Any]] = []
    peak_bucket = None
    peak_count = 0
    for lbl in ordered_labels:
        b = bucket_data.get(lbl, {"count": 0, "positive": 0, "neutral": 0, "negative": 0})
        total = b["count"]
        buckets.append({
            "label": lbl,
            "count": total,
            "positive": b["positive"],
            "neutral": b["neutral"],
            "negative": b["negative"],
            "positive_pct": round(b["positive"] / total * 100, 1) if total else 0,
            "negative_pct": round(b["negative"] / total * 100, 1) if total else 0,
        })
        if total > peak_count:
            peak_count = total
            peak_bucket = lbl

    return {
        "granularity": "hour" if use_hour else "day",
        "buckets": buckets,
        "peak_bucket": peak_bucket,
        "total": sum(b["count"] for b in buckets),
    }


def _risk_opportunity_signals(
    comments: list[dict[str, Any]],
    top_n: int = 5,
    sample_per_word: int = 2,
) -> dict[str, Any]:
    """从评论中提取风险/机会词信号

    Returns:
        {
            "opportunity": [
                {"word": "看好", "count": 12,
                 "samples": ["强烈看好中际旭创...", "长线看好..."]},
                ...
            ],
            "risk": [
                {"word": "减仓", "count": 7,
                 "samples": ["该减仓了..."]},
                ...
            ],
            "opportunity_total": 50,  # 总命中数
            "risk_total": 30,
        }
    """
    opp_counter: Counter = Counter()
    risk_counter: Counter = Counter()
    opp_samples: dict[str, list[str]] = defaultdict(list)
    risk_samples: dict[str, list[str]] = defaultdict(list)

    for c in comments:
        text = (c.get("content") or "").strip()
        if not text or len(text) < 4:
            continue
        # 长文本切片（避免一个超长评论被多词命中重复计入）
        snippet = text[:200]
        for w in SENTIMENT_BULLISH:
            if w in text and opp_counter[w] < 1000:  # 上限防爆
                opp_counter[w] += 1
                if len(opp_samples[w]) < sample_per_word and w in snippet:
                    opp_samples[w].append(snippet)
        for w in SENTIMENT_BEARISH:
            if w in text and risk_counter[w] < 1000:
                risk_counter[w] += 1
                if len(risk_samples[w]) < sample_per_word and w in snippet:
                    risk_samples[w].append(snippet)

    def _pack(counter: Counter, samples: dict[str, list[str]]) -> list[dict[str, Any]]:
        out = []
        for word, cnt in counter.most_common(top_n):
            out.append({
                "word": word,
                "count": cnt,
                "samples": samples.get(word, []),
            })
        return out

    return {
        "opportunity": _pack(opp_counter, opp_samples),
        "risk": _pack(risk_counter, risk_samples),
        "opportunity_total": sum(opp_counter.values()),
        "risk_total": sum(risk_counter.values()),
    }


def build_report_data(
    db: Session,
    date_str: str | None = None,
    sector: str | None = None,
    start_str: str | None = None,
    end_str: str | None = None,
) -> dict[str, Any]:
    """v2.2 报告页数据聚合：包含 7 个分析维度

    - 核心简报（来自 build_daily_brief）
    - 市场行情对比（板块涨跌幅 + 重点公司）
    - 评论时间分布（小时/天桶 + 情绪走势）
    - 风险/机会词信号
    - 舆情 vs 行情 对齐（每个板块的情绪正/负 vs 当日板块涨跌幅）
    """
    brief = build_daily_brief(
        db,
        date_str=date_str,
        sector=sector,
        start_str=start_str,
        end_str=end_str,
    )

    # 决定市场日期：取区间内某日（end > start 取 end；同日/单日取 date；空取今日）
    market_date = (
        brief.get("end_date")
        or brief.get("start_date")
        or brief.get("date")
        or datetime.now().strftime("%Y-%m-%d")
    )

    market = _market_snapshot(market_date)
    comments = _comments_for_videos(
        db,
        _filter_videos_by_range(
            db, start_str=brief.get("start_date"), end_str=brief.get("end_date"),
            sector=sector,
        )[0],
    )
    time_dist = _comment_time_distribution(comments, brief.get("start_date"), brief.get("end_date"))
    signals = _risk_opportunity_signals(comments)

    # 舆情 vs 行情 对齐：每个板块 [情绪差(正-负)%, 当日涨跌幅%]
    sector_compare: list[dict[str, Any]] = []
    for sec_name in SECTOR_TERMS.keys():
        sec_pie = brief.get("sector_pies", {}).get(sec_name, {})
        sent_gap = round(
            (sec_pie.get("positive_ratio", 0) or 0)
            - (sec_pie.get("negative_ratio", 0) or 0),
            1,
        )
        market_pct = market["sector_perf"].get(sec_name)
        sector_compare.append({
            "sector": sec_name,
            "sentiment_gap": sent_gap,
            "sector_pct_chg": market_pct,
            "comment_total": sec_pie.get("total", 0),
        })

    return {
        **brief,
        "market": market,
        "time_distribution": time_dist,
        "signals": signals,
        "sector_compare": sector_compare,
    }


def build_daily_brief(
    db: Session,
    date_str: str | None = None,
    sector: str | None = None,
    start_str: str | None = None,
    end_str: str | None = None,
) -> dict[str, Any]:
    """构造每日简报 / 时间段简报 JSON（v2.1）

    Args:
        db: 数据库 session
        date_str: 兼容旧接口 YYYY-MM-DD；等价于 start_str=end_str=date_str
        sector: 可选板块过滤（半导体/光通信/光芯片）
        start_str: 区间起始日期 YYYY-MM-DD（v2.1 新增）
        end_str: 区间结束日期 YYYY-MM-DD（v2.1 新增）

    优先级：start_str/end_str 优先；date_str 兜底；都为 None → 不过滤日期

    Returns:
        {
            "date": "2026-06-09" | None,
            "start_date": "2026-06-01" | None,
            "end_date": "2026-06-09" | None,
            "range_label": "2026-06-09" | "2026-06-01 ~ 2026-06-09" | "全部" | "最近 7 天（回退）",
            "sector": None,
            "total_videos": 1153,
            "total_comments": 2917,
            "is_fallback": False,  # 是否走了单日→7天回退
            "sentiment": {positive_ratio, neutral_ratio, negative_ratio, mood},
            "sector_pies": { "半导体": {...}, ... },
            "summary": {  # AI 总结形式（v2.1）
                "mood": "略偏正面",
                "headline": "...",
                "sector_focus": [...],
                "key_insights": [...],
                "hot_terms": [...],
            },
        }
    """
    # 兼容旧接口：date_str 等价于 start=end=date_str
    if date_str and not (start_str or end_str):
        start_str = date_str
        end_str = date_str

    videos, is_fallback = _filter_videos_by_range(db, start_str=start_str, end_str=end_str, sector=sector)
    bvids = [v.bvid for v in videos]
    comments = _comments_for_videos(db, videos)

    # 0) 元信息：range_label
    if is_fallback:
        range_label = "最近 7 天（回退）"
    elif start_str and end_str and start_str == end_str:
        range_label = start_str
    elif start_str and end_str:
        range_label = f"{start_str} ~ {end_str}"
    elif start_str:
        range_label = f"{start_str} 起"
    elif end_str:
        range_label = f"至 {end_str}"
    else:
        range_label = "全部"

    # 1) 整体情感
    overall_sent = analyze_sentiment_v2(comments) if comments else {
        "positive_ratio": 0, "neutral_ratio": 0, "negative_ratio": 0,
        "total_samples": 0, "dict_hit_rate": 0,
    }
    pos = overall_sent["positive_ratio"] * 100
    neu = overall_sent["neutral_ratio"] * 100
    neg = overall_sent["negative_ratio"] * 100

    sentiment = {
        "positive_ratio": round(pos, 1),
        "neutral_ratio": round(neu, 1),
        "negative_ratio": round(neg, 1),
        "mood": _mood_label(pos, neg),
    }

    # 2) 各板块饼图（分别统计每个板块评论的情感）
    sector_pies: dict[str, Any] = {}
    for sec_name, sec_terms in SECTOR_TERMS.items():
        sec_comments = [
            c for c in comments
            if any(kw in (c["content"] or "") for kw in sec_terms)
        ]
        if sec_comments:
            sec_sent = analyze_sentiment_v2(sec_comments)
            sector_pies[sec_name] = {
                "positive_ratio": round(sec_sent["positive_ratio"] * 100, 1),
                "neutral_ratio": round(sec_sent["neutral_ratio"] * 100, 1),
                "negative_ratio": round(sec_sent["negative_ratio"] * 100, 1),
                "total": sec_sent["total_samples"],
            }
        else:
            sector_pies[sec_name] = {
                "positive_ratio": 0, "neutral_ratio": 0, "negative_ratio": 0, "total": 0,
            }

    # 3) AI 总结（v2.1 多视角摘要器）
    if comments:
        summarizer = TemplateSummarizer(top_terms=8, top_insights=4)
        summary = summarizer.summarize(comments, range_label=range_label)
    else:
        summary = {
            "mood": "中性",
            "headline": "今日暂无评论数据。",
            "sector_focus": [],
            "key_insights": [],
            "hot_terms": [],
        }

    return {
        "date": start_str if (start_str and start_str == end_str) else (start_str or end_str),
        "start_date": start_str,
        "end_date": end_str,
        "range_label": range_label,
        "is_fallback": is_fallback,
        "sector": sector,
        "total_videos": len(videos),
        "total_comments": len(comments),
        "sentiment": sentiment,
        "sector_pies": sector_pies,
        "summary": summary,
    }
