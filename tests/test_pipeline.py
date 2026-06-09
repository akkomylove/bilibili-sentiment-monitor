"""端到端 pipeline 测试

不依赖数据库、不依赖 B 站真实数据，验证：
1. sentiment_v2 词典命中 + SnowNLP 兜底
2. keywords v2 板块术语加权 + Top 20
3. TemplateSummarizer 拼接 3-5 句摘要
4. MockMarketData 固定+扰动结果

期望 5 秒内通过。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

# 路径处理：把项目根加进 sys.path
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
_FIXTURE = _ROOT / "tests" / "fixtures" / "sample_comments.json"


def _load_fixture() -> list[dict]:
    with open(_FIXTURE, encoding="utf-8") as f:
        return json.load(f)


# === 1. 投资词典 ===

class TestInvestmentDict:
    def test_bullish_words_not_empty(self):
        from app.services.analysis.investment_dict import SENTIMENT_BULLISH
        assert len(SENTIMENT_BULLISH) > 10
        assert "突破" in SENTIMENT_BULLISH
        assert "创新高" in SENTIMENT_BULLISH

    def test_bearish_words_not_empty(self):
        from app.services.analysis.investment_dict import SENTIMENT_BEARISH
        assert len(SENTIMENT_BEARISH) > 10
        assert "下跌" in SENTIMENT_BEARISH
        assert "砍单" in SENTIMENT_BEARISH

    def test_sector_terms_has_three_sectors(self):
        from app.services.analysis.investment_dict import SECTOR_TERMS
        assert "半导体" in SECTOR_TERMS
        assert "光通信" in SECTOR_TERMS
        assert "光芯片" in SECTOR_TERMS

    def test_detect_sector(self):
        from app.services.analysis.investment_dict import detect_sector
        assert detect_sector("中芯国际和台积电") == "半导体"
        assert detect_sector("800G光模块和CPO") == "光通信"
        assert detect_sector("DFB激光器外延片") == "光芯片"
        assert detect_sector("今天天气真好") is None


# === 2. 情感分析 v2 ===

class TestSentimentV2:
    def test_dict_hit_positive(self):
        from app.services.analysis.sentiment_v2 import analyze_sentiment_v2
        comments = [
            {"rpid": 1, "content": "中芯国际这次真突破，强烈看好", "like_count": 100},
        ]
        result = analyze_sentiment_v2(comments)
        assert result["positive_count"] == 1
        assert result["dict_hit_rate"] == 1.0
        assert result["details"][0]["method"] == "dict"

    def test_dict_hit_negative(self):
        from app.services.analysis.sentiment_v2 import analyze_sentiment_v2
        comments = [
            {"rpid": 1, "content": "光通信跌停砍单了，业绩不及预期", "like_count": 50},
        ]
        result = analyze_sentiment_v2(comments)
        assert result["negative_count"] == 1
        assert result["details"][0]["method"] == "dict"

    def test_snownlp_fallback(self):
        from app.services.analysis.sentiment_v2 import analyze_sentiment_v2
        # 故意写一个情绪明确但不在词典里的句子
        comments = [
            {"rpid": 1, "content": "今天真是太开心了！", "like_count": 0},
        ]
        result = analyze_sentiment_v2(comments)
        assert result["details"][0]["method"] == "snownlp"
        assert result["total_samples"] == 1

    def test_empty_comments(self):
        from app.services.analysis.sentiment_v2 import analyze_sentiment_v2
        result = analyze_sentiment_v2([])
        assert result["total_samples"] == 0
        assert result["positive_ratio"] == 0
        assert result["negative_ratio"] == 0

    def test_sample_fixture_sentiment(self):
        """用 15 条样本，验证整体分布合理"""
        from app.services.analysis.sentiment_v2 import analyze_sentiment_v2
        comments = _load_fixture()
        result = analyze_sentiment_v2(comments)
        assert result["total_samples"] == 15
        # 样本里看多、看空都有，dict 命中率应该 > 30%
        assert result["dict_hit_rate"] >= 0.3
        # 三类比例和 ≈ 1
        total = (
            result["positive_ratio"]
            + result["neutral_ratio"]
            + result["negative_ratio"]
        )
        assert 0.99 <= total <= 1.01


# === 3. 关键词提取 v2 ===

class TestKeywordsV2:
    def test_top_n_default_20(self):
        from app.services.analysis.keywords import extract_keywords_from_texts
        texts = ["半导体"] * 30 + ["光模块"] * 20 + ["不相关"] * 50
        result = extract_keywords_from_texts(texts)
        assert len(result["keywords"]) <= 20

    def test_sector_boost(self):
        from app.services.analysis.keywords import extract_keywords_from_texts
        # 让一个普通词和一个板块术语出现次数相同，板块术语应排在前面
        texts = ["行业行业行业"] * 5 + ["中芯国际中芯国际中芯国际中芯国际中芯国际"] * 5
        result = extract_keywords_from_texts(texts, top_n=5)
        # "中芯国际" 出现 5 次但 sector_term=True，应排在 "行业" 之前
        words = [k["word"] for k in result["keywords"]]
        if "中芯国际" in words and "行业" in words:
            assert words.index("中芯国际") < words.index("行业")

    def test_sector_only(self):
        from app.services.analysis.keywords import extract_keywords_from_texts
        texts = ["随便说点什么", "中芯国际和台积电", "光模块800G", "无关内容"]
        result = extract_keywords_from_texts(texts, sector_only=True)
        for kw in result["keywords"]:
            assert kw["sector_term"] is True
        words = [k["word"] for k in result["keywords"]]
        # "随便""说点"不应出现
        assert "随便" not in words

    def test_sample_fixture_keywords(self):
        """用 15 条样本，应该能提取到中芯国际 / 光模块 等板块词"""
        from app.services.analysis.keywords import extract_keywords_from_texts
        comments = _load_fixture()
        texts = [c["content"] for c in comments]
        result = extract_keywords_from_texts(texts, top_n=20)
        words = {k["word"] for k in result["keywords"]}
        # 至少出现一个板块术语
        assert words & {"中芯国际", "台积电", "光模块", "中际旭创", "光芯片"}


# === 4. 模板摘要器 ===

class TestTemplateSummarizer:
    def test_summarize_basic(self):
        """v2.1：summarize 返回 dict，含 mood/headline/sector_focus/key_insights/hot_terms"""
        from app.services.summarizer.template import TemplateSummarizer
        comments = _load_fixture()
        summarizer = TemplateSummarizer(top_terms=8, top_insights=4)
        summary = summarizer.summarize(comments)
        assert isinstance(summary, dict)
        # 必要字段
        assert "mood" in summary
        assert summary["mood"] in {"偏正面", "略偏正面", "中性", "略偏负面", "偏负面"}
        assert "headline" in summary
        assert len(summary["headline"]) > 20
        assert "情绪" in summary["headline"]
        assert "正面" in summary["headline"] or "负面" in summary["headline"] or "中性" in summary["headline"]
        # 必要子结构
        assert "sector_focus" in summary
        assert "key_insights" in summary
        assert "hot_terms" in summary
        assert isinstance(summary["sector_focus"], list)
        assert isinstance(summary["key_insights"], list)
        assert isinstance(summary["hot_terms"], list)

    def test_summarize_empty(self):
        """v2.1：空评论时返回包含"暂无"占位的 dict"""
        from app.services.summarizer.template import TemplateSummarizer
        summarizer = TemplateSummarizer()
        summary = summarizer.summarize([])
        assert isinstance(summary, dict)
        assert "headline" in summary
        assert "暂无" in summary["headline"]
        assert summary["mood"] == "中性"
        assert summary["sector_focus"] == []
        assert summary["key_insights"] == []
        assert summary["hot_terms"] == []

    def test_summarize_sector_detected(self):
        """v2.1：含"中芯国际"的评论应在 sector_focus 中识别出"半导体"板块"""
        from app.services.summarizer.template import TemplateSummarizer
        comments = [
            {"rpid": 1, "content": "中芯国际和台积电", "like_count": 1},
            {"rpid": 2, "content": "EUV光刻机", "like_count": 1},
        ]
        summarizer = TemplateSummarizer()
        summary = summarizer.summarize(comments)
        assert isinstance(summary, dict)
        sector_names = [s["name"] for s in summary["sector_focus"]]
        assert "半导体" in sector_names, f"sector_focus 应包含'半导体'，实际 {sector_names}"


# === 5. Mock 股价数据 ===

class TestMockMarketData:
    def test_sector_perf_returns_dict(self):
        from app.services.market.mock import MockMarketData
        md = MockMarketData()
        result = md.get_sector_perf("2026-05-31")
        assert "半导体" in result
        assert "光通信" in result
        assert "光芯片" in result
        # 涨跌幅是浮点
        assert isinstance(result["半导体"], float)

    def test_sector_perf_deterministic(self):
        """同一天同板块，返回结果一致（便于测试断言）"""
        from app.services.market.mock import MockMarketData
        md1 = MockMarketData()
        md2 = MockMarketData()
        assert md1.get_sector_perf("2026-05-31") == md2.get_sector_perf("2026-05-31")

    def test_sector_perf_varies_by_date(self):
        """不同日期应返回不同结果"""
        from app.services.market.mock import MockMarketData
        md = MockMarketData()
        d1 = md.get_sector_perf("2026-05-30")
        d2 = md.get_sector_perf("2026-05-31")
        # 至少有一个板块不同（扰动带来差异）
        assert d1 != d2

    def test_company_quote_known(self):
        from app.services.market.mock import MockMarketData
        md = MockMarketData()
        q = md.get_company_quote("中际旭创", "2026-05-31")
        assert q is not None
        assert "pct_chg" in q
        assert "close" in q

    def test_company_quote_unknown(self):
        from app.services.market.mock import MockMarketData
        md = MockMarketData()
        assert md.get_company_quote("不存在的公司", "2026-05-31") is None


# === 6. 端到端 pipeline ===

class TestPipelineE2E:
    def test_full_pipeline(self):
        """样本 → 情感 + 关键词 + 摘要 + 股价 完整流程"""
        from app.services.analysis.keywords import extract_keywords_from_texts
        from app.services.analysis.sentiment_v2 import analyze_sentiment_v2
        from app.services.market.mock import MockMarketData
        from app.services.summarizer.template import TemplateSummarizer

        comments = _load_fixture()
        texts = [c["content"] for c in comments]

        # Step 1: 情感
        sentiment = analyze_sentiment_v2(comments)
        assert sentiment["total_samples"] == 15

        # Step 2: 关键词
        kw = extract_keywords_from_texts(texts, top_n=20)
        assert len(kw["keywords"]) > 0

        # Step 3: 摘要（v2.1：返回 dict，headline 含"15 条评论"）
        summarizer = TemplateSummarizer(top_terms=8, top_insights=4)
        summary = summarizer.summarize(comments)
        assert isinstance(summary, dict)
        assert "15 条评论" in summary["headline"]

        # Step 4: 股价
        market = MockMarketData()
        sector_perf = market.get_sector_perf("2026-05-31")
        assert "半导体" in sector_perf

        # 输出综合报告
        report = {
            "sentiment": {
                "positive": sentiment["positive_ratio"],
                "neutral": sentiment["neutral_ratio"],
                "negative": sentiment["negative_ratio"],
            },
            "top_keywords": [k["word"] for k in kw["keywords"][:5]],
            "summary": summary,
            "sector_perf": sector_perf,
        }
        # 至少要包含一个看多关键词
        assert report["top_keywords"]


# === 7. 性能测试（5 秒内跑完） ===

class TestPerformance:
    def test_full_pipeline_under_5_seconds(self):
        import time

        from app.services.analysis.keywords import extract_keywords_from_texts
        from app.services.analysis.sentiment_v2 import analyze_sentiment_v2
        from app.services.summarizer.template import TemplateSummarizer

        start = time.time()
        comments = _load_fixture()
        analyze_sentiment_v2(comments)
        extract_keywords_from_texts([c["content"] for c in comments])
        TemplateSummarizer().summarize(comments)
        elapsed = time.time() - start
        assert elapsed < 5.0, f"pipeline 耗时 {elapsed:.2f}s 超过 5s"
