"""模板摘要器（v2.1 - AI 总结形式）

替代 v1 的"代表评论"单条展示，改为多视角分析：
1. 整体情绪（按 5 档判定）
2. 板块聚焦（按 SECTOR_TERMS 计数排序）
3. 关键观点（多视角：最赞正面 / 最赞负面 / 板块聚焦正面）
4. 行业术语热度（仅 SECTOR_TERMS，过滤"doge/总结"等噪声词）
"""

from __future__ import annotations

import re
from typing import Any

from app.services.analysis.investment_dict import (
    SECTOR_TERMS,
    detect_sector,
)
from app.services.analysis.keywords import extract_keywords_from_texts
from app.services.analysis.sentiment_v2 import analyze_sentiment_v2
from app.services.summarizer.base import Summarizer


def _get_content(c: Any) -> str:
    if isinstance(c, dict):
        return c.get("content", "") or ""
    return getattr(c, "content", "") or ""


def _get_like_count(c: Any) -> int:
    if isinstance(c, dict):
        v = c.get("like_count", 0)
    else:
        v = getattr(c, "like_count", 0)
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


# B 站表情包/水印/超链接等噪声模式
_NOISE_RE = re.compile(
    r"\[(doge|笑哭|OK|awsl|点赞|哈欠|疑惑|喝彩|比心|吃瓜|打call|歪嘴|滑稽|奋斗|叹气|惊喜|嘟嘴|亲亲|委屈|尴尬|调皮|酸了|生气|无语|裂开|晕了|迷惑|微笑|白眼|再见|好的)\]",
    re.IGNORECASE,
)
# 纯表情/纯符号的评论视为无价值
_LOW_VALUE_RE = re.compile(r"^[\s\W_]+$|^[?？！。，！,…\.\-~]+$")
# 太短的评论（≤3 字符）通常无信息量
_TOO_SHORT = 3


def _is_insightful(c: Any) -> bool:
    """判断评论是否有"洞察价值"（用于关键观点筛选）"""
    content = _get_content(c).strip()
    if len(content) <= _TOO_SHORT:
        return False
    if _LOW_VALUE_RE.match(content):
        return False
    # 去除表情包后还剩的内容过短
    cleaned = _NOISE_RE.sub("", content).strip()
    if len(cleaned) <= _TOO_SHORT:
        return False
    return True


def _insight_text(c: Any, max_len: int = 80) -> str:
    """截断评论用于展示"""
    text = _NOISE_RE.sub("", _get_content(c)).strip()
    if len(text) > max_len:
        text = text[:max_len] + "…"
    return text


def _build_editor_takeaway(
    total: int,
    mood: str,
    pos_pct: float,
    neg_pct: float,
    sector_focus: list[dict[str, Any]],
    hot_terms: list[dict[str, Any]],
    range_label: str,
) -> list[str]:
    """生成"编辑视角"总结（报告页结论页使用）。

    基于：整体情绪 + 最强板块 + 热议词 → 3-4 句模板化结论。
    不用 LLM，纯 deterministic，保证可重复、不超时。
    """
    lines: list[str] = []

    # 1) 整体态势
    if total <= 0:
        lines.append(f"{range_label}监控数据为空。")
        return lines

    sentiment_phrase = {
        "偏正面": f"看多情绪占主导，正面占比 {pos_pct:.0f}%；",
        "偏负面": f"看空情绪抬头，负面占比 {neg_pct:.0f}%；",
        "略偏正面": f"整体偏积极，正面 {pos_pct:.0f}% 略高于负面 {neg_pct:.0f}%；",
        "略偏负面": f"整体偏谨慎，负面 {neg_pct:.0f}% 略高于正面 {pos_pct:.0f}%；",
        "中性": "多空观点较为均衡；",
    }.get(mood, f"正负占比 {pos_pct:.0f}% / {neg_pct:.0f}%；")
    lines.append(f"{range_label}共采集 {total} 条评论，{sentiment_phrase}建议关注舆情结构性变化。")

    # 2) 最强板块
    if sector_focus:
        top = max(sector_focus, key=lambda s: s.get("mention_count", 0))
        top2 = sorted(sector_focus, key=lambda s: -s.get("mention_count", 0))[:2]
        if top.get("mention_count", 0) > 0:
            sector_names = "、".join(s["name"] for s in top2)
            lines.append(
                f"板块层面，{sector_names} 关注度最高，{top['name']}相关讨论占 {top.get('share_pct', 0):.1f}%；"
                f"该板块情绪 {top.get('mood', '中性')}，可作为后续调研切入点。"
            )

    # 3) 风险/机会信号
    if hot_terms:
        top_terms = [t["word"] for t in hot_terms[:3] if t.get("word")]
        if top_terms:
            lines.append(f"热议词集中在 { ' / '.join(top_terms) } 等概念，建议结合实时行情交叉验证。")

    # 4) 数据量小的情况给个兜底
    if total < 30:
        lines.append(
            f"备注：{range_label}样本量较少（{total} 条），结论置信度有限，"
            f"建议结合更长窗口或人工复核。"
        )

    return lines[:4]


def _mood_5(pos: float, neg: float) -> str:
    """5 档情绪判定（与 daily_brief._mood_label 一致）"""
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


class TemplateSummarizer(Summarizer):
    """v2.1 多视角 AI 风格摘要器。

    输出结构（dict 而非纯文本，便于前端灵活渲染）：
    {
        "mood": "略偏正面",
        "headline": "今日 AI 投资评论 1153 条，情绪略偏正面（54.5%/10.5%/35.0%）。",
        "sector_focus": [
            {"name": "半导体", "mention_count": 312, "mood": "偏正面", "share_pct": 27.1},
            ...
        ],
        "key_insights": [
            {"side": "正方", "text": "中芯国际这次真突破...", "likes": 258, "rpid": 12345},
            {"side": "反方", "text": "...", "likes": 188, "rpid": 67890},
            ...
        ],
        "hot_terms": [{"word": "中芯国际", "count": 87, "weight": 174.0}, ...],  # 仅板块术语
    }
    """

    def __init__(self, top_terms: int = 8, top_insights: int = 4) -> None:
        self.top_terms = top_terms
        self.top_insights = top_insights

    def summarize(self, comments: list[dict[str, Any]], range_label: str = "本期") -> dict[str, Any]:
        if not comments:
            return {
                "mood": "中性",
                "headline": f"{range_label}暂无评论数据。",
                "sector_focus": [],
                "key_insights": [],
                "hot_terms": [],
                "editor_takeaway": [f"{range_label}监控数据为空，建议先执行采集任务。"],
            }

        # 1) 整体情感
        sentiment = analyze_sentiment_v2(comments)
        pos_pct = sentiment["positive_ratio"] * 100
        neu_pct = sentiment["neutral_ratio"] * 100
        neg_pct = sentiment["negative_ratio"] * 100
        mood = _mood_5(pos_pct, neg_pct)
        total = sentiment["total_samples"]

        headline = (
            f"{range_label} AI 投资领域共 {total} 条评论，整体情绪{mood}。"
            f"正面 {pos_pct:.1f}%，中性 {neu_pct:.1f}%，负面 {neg_pct:.1f}%。"
        )

        # 2) 板块聚焦（按板块术语命中评论数排序）
        sector_focus: list[dict[str, Any]] = []
        for sec_name, sec_terms in SECTOR_TERMS.items():
            sec_comments = [
                c for c in comments
                if any(t in _get_content(c) for t in sec_terms)
            ]
            if not sec_comments:
                continue
            sec_sent = analyze_sentiment_v2(sec_comments)
            sp = sec_sent["positive_ratio"] * 100
            sn = sec_sent["negative_ratio"] * 100
            sector_focus.append({
                "name": sec_name,
                "mention_count": len(sec_comments),
                "share_pct": round(len(sec_comments) / max(total, 1) * 100, 1),
                "mood": _mood_5(sp, sn),
                "positive_ratio": round(sp, 1),
                "negative_ratio": round(sn, 1),
            })
        sector_focus.sort(key=lambda x: x["mention_count"], reverse=True)

        # 3) 关键观点（按"有洞察价值 + 点赞数"双重排序）
        candidates = [c for c in comments if _is_insightful(c)]
        if candidates:
            # 分正面/负面两组
            pos_candidates = []
            neg_candidates = []
            for c in candidates:
                c_sent = analyze_sentiment_v2([c])
                cp = c_sent["positive_ratio"] * 100
                cn = c_sent["negative_ratio"] * 100
                if cp > cn and cp >= 30:
                    pos_candidates.append((c, cp))
                elif cn > cp and cn >= 30:
                    neg_candidates.append((c, cn))
            pos_candidates.sort(key=lambda x: (_get_like_count(x[0]), x[1]), reverse=True)
            neg_candidates.sort(key=lambda x: (_get_like_count(x[0]), x[1]), reverse=True)

            # 多视角组合：2 正面 + 1 负面 + 1 板块聚焦
            insights = []
            for c, _ in pos_candidates[:2]:
                insights.append({
                    "side": "正方",
                    "text": _insight_text(c),
                    "likes": _get_like_count(c),
                })
            for c, _ in neg_candidates[:1]:
                insights.append({
                    "side": "反方",
                    "text": _insight_text(c),
                    "likes": _get_like_count(c),
                })
        else:
            insights = []
        insights = insights[: self.top_insights]

        # 4) 行业术语热度（仅 SECTOR_TERMS，过滤 doge/总结 等噪声）
        texts = [_get_content(c) for c in comments]
        kw_result = extract_keywords_from_texts(
            texts, top_n=self.top_terms, sector_only=True
        )
        hot_terms = [
            {"word": k["word"], "count": k["count"], "weight": k["weight"]}
            for k in kw_result["keywords"][: self.top_terms]
        ]

        return {
            "mood": mood,
            "headline": headline,
            "sector_focus": sector_focus,
            "key_insights": insights,
            "hot_terms": hot_terms,
            "editor_takeaway": _build_editor_takeaway(
                total=total,
                mood=mood,
                pos_pct=pos_pct,
                neg_pct=neg_pct,
                sector_focus=sector_focus,
                hot_terms=hot_terms,
                range_label=range_label,
            ),
        }
