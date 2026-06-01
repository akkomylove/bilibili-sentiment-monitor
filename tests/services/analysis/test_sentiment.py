from unittest.mock import MagicMock, patch

from app.services.analysis.sentiment import analyze_sentiment


class TestAnalyzeSentiment:
    """测试情感分析"""

    def test_analyze_positive_sentiment(self):
        """测试正面情感"""
        mock_db = MagicMock()
        mock_comment = MagicMock()
        mock_comment.content = "这个视频太棒了！"
        mock_comment.pub_time = None
        mock_db.query.return_value.all.return_value = [mock_comment]

        with patch("app.services.analysis.sentiment.SnowNLP") as mock_snownlp:
            mock_instance = MagicMock()
            mock_instance.sentiments = 0.85
            mock_snownlp.return_value = mock_instance

            result = analyze_sentiment(mock_db)

            assert result["positive_ratio"] == 1.0
            assert result["total_samples"] == 1

    def test_analyze_negative_sentiment(self):
        """测试负面情感"""
        mock_db = MagicMock()
        mock_comment = MagicMock()
        mock_comment.content = "这个视频太差了"
        mock_comment.pub_time = None
        mock_db.query.return_value.all.return_value = [mock_comment]

        with patch("app.services.analysis.sentiment.SnowNLP") as mock_snownlp:
            mock_instance = MagicMock()
            mock_instance.sentiments = 0.15
            mock_snownlp.return_value = mock_instance

            result = analyze_sentiment(mock_db)

            assert result["negative_ratio"] == 1.0

    def test_analyze_neutral_sentiment(self):
        """测试中性情感"""
        mock_db = MagicMock()
        mock_comment = MagicMock()
        mock_comment.content = "这是一个视频"
        mock_comment.pub_time = None
        mock_db.query.return_value.all.return_value = [mock_comment]

        with patch("app.services.analysis.sentiment.SnowNLP") as mock_snownlp:
            mock_instance = MagicMock()
            mock_instance.sentiments = 0.5
            mock_snownlp.return_value = mock_instance

            result = analyze_sentiment(mock_db)

            assert result["neutral_ratio"] == 1.0

    def test_analyze_empty_text(self):
        """测试空文本处理"""
        mock_db = MagicMock()
        mock_comment = MagicMock()
        mock_comment.content = ""
        mock_comment.pub_time = None
        mock_db.query.return_value.all.return_value = [mock_comment]

        result = analyze_sentiment(mock_db)

        assert result["neutral_ratio"] == 1.0
        assert result["total_samples"] == 1

    def test_analyze_batch_comments(self):
        """测试批量评论分析"""
        mock_db = MagicMock()
        comments = []
        for i in range(3):
            c = MagicMock()
            c.content = f"评论{i}"
            c.pub_time = None
            comments.append(c)
        mock_db.query.return_value.all.return_value = comments

        with patch("app.services.analysis.sentiment.SnowNLP") as mock_snownlp:
            mock_instance = MagicMock()
            mock_instance.sentiments = 0.8
            mock_snownlp.return_value = mock_instance

            result = analyze_sentiment(mock_db)

            assert result["total_samples"] == 3
            assert result["positive_ratio"] == 1.0
