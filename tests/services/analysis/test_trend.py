from datetime import datetime
from unittest.mock import MagicMock

from app.services.analysis.trend import analyze_trend


class TestAnalyzeTrend:
    """测试趋势分析"""

    def test_analyze_trend_with_data(self):
        """测试有数据时的趋势分析"""
        mock_db = MagicMock()
        mock_row = MagicMock()
        mock_row.date = datetime(2026, 5, 1).date()
        mock_row.count = 10

        mock_query = MagicMock()
        mock_query.join.return_value.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = [mock_row]
        mock_query.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = [mock_row]
        mock_db.query.return_value = mock_query

        result = analyze_trend(mock_db, keyword_id=1)

        assert "time_series" in result
        assert "peak_points" in result
        assert "analyzed_at" in result
        assert len(result["time_series"]) == 1

    def test_analyze_trend_empty_data(self):
        """测试空数据趋势分析"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.join.return_value.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = []
        mock_query.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = []
        mock_db.query.return_value = mock_query

        result = analyze_trend(mock_db)

        assert result["time_series"] == []
        assert result["peak_points"] == []

    def test_analyze_trend_peak_detection(self):
        """测试峰值检测"""
        mock_db = MagicMock()
        rows = []
        for i, (d, c) in enumerate([
            (datetime(2026, 5, 1).date(), 10),
            (datetime(2026, 5, 2).date(), 50),
            (datetime(2026, 5, 3).date(), 100),
            (datetime(2026, 5, 4).date(), 30),
            (datetime(2026, 5, 5).date(), 20),
        ]):
            row = MagicMock()
            row.date = d
            row.count = c
            rows.append(row)

        mock_query = MagicMock()
        mock_query.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = rows
        mock_db.query.return_value = mock_query

        result = analyze_trend(mock_db)

        assert len(result["time_series"]) == 5
        assert len(result["peak_points"]) >= 1
        assert result["peak_points"][0]["date"] == "2026-05-03"

    def test_analyze_trend_no_significant_peaks(self):
        """测试无明显峰值"""
        mock_db = MagicMock()
        rows = []
        for d, c in [
            (datetime(2026, 5, 1).date(), 10),
            (datetime(2026, 5, 2).date(), 12),
            (datetime(2026, 5, 3).date(), 15),
        ]:
            row = MagicMock()
            row.date = d
            row.count = c
            rows.append(row)

        mock_query = MagicMock()
        mock_query.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = rows
        mock_db.query.return_value = mock_query

        result = analyze_trend(mock_db)

        assert result["peak_points"] == []
