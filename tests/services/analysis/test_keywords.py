from unittest.mock import MagicMock, patch

from app.services.analysis.keywords import extract_keywords


class TestExtractKeywords:
    """测试关键词提取"""

    def test_extract_keywords(self):
        """测试关键词提取函数"""
        mock_db = MagicMock()
        mock_comment = MagicMock()
        mock_comment.content = "Python编程学习教程"
        mock_db.query.return_value.all.return_value = [mock_comment]

        with patch("app.services.analysis.keywords.jieba.lcut") as mock_lcut:
            mock_lcut.return_value = ["Python", "编程", "学习", "教程"]

            result = extract_keywords(mock_db, video_bvid="BV1xx411c7mD", top_n=10)

            assert "keywords" in result
            assert "total_terms" in result
            assert "analyzed_at" in result

    def test_extract_with_empty_comments(self):
        """测试空评论列表"""
        mock_db = MagicMock()
        mock_db.query.return_value.all.return_value = []

        result = extract_keywords(mock_db, top_n=10)

        assert result["keywords"] == []
        assert result["total_terms"] == 0

    def test_extract_filters_stop_words(self):
        """测试停用词过滤"""
        mock_db = MagicMock()
        mock_comment = MagicMock()
        mock_comment.content = "的了我是在"
        mock_db.query.return_value.all.return_value = [mock_comment]

        with patch("app.services.analysis.keywords.jieba.lcut") as mock_lcut:
            mock_lcut.return_value = ["的", "了", "我", "是", "在"]

            result = extract_keywords(mock_db, top_n=10)

            assert result["total_terms"] == 0
            assert result["keywords"] == []
