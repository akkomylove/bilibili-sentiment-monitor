"""sectors.yaml 加载与配置测试"""

from __future__ import annotations

import pytest


class TestLoadSectorsConfig:
    def test_load_returns_three_sectors(self):
        from app.tasks.crawl import load_sectors_config
        cfg = load_sectors_config()
        assert "sectors" in cfg
        assert len(cfg["sectors"]) == 3
        names = [s["name"] for s in cfg["sectors"]]
        assert "半导体" in names
        assert "光通信" in names
        assert "光芯片" in names

    def test_sector_has_keywords_and_threshold(self):
        from app.tasks.crawl import load_sectors_config
        cfg = load_sectors_config()
        for sec in cfg["sectors"]:
            assert "keywords" in sec
            assert len(sec["keywords"]) > 0
            assert "hot_threshold" in sec
            assert "min_play" in sec["hot_threshold"]
            assert "min_comment" in sec["hot_threshold"]

    def test_crawl_block_defaults(self):
        from app.tasks.crawl import load_sectors_config
        cfg = load_sectors_config()
        c = cfg["crawl"]
        assert c["max_videos_per_keyword"] == 20
        assert c["max_pages"] == 3
        assert c["max_comments_per_video"] == 100
        assert c["reply_top_percent"] == 10
        assert c["schedule"] == "0 9 * * *"

    def test_sectors_keyword_uniqueness(self):
        """同一关键词不应重复出现"""
        from app.tasks.crawl import load_sectors_config
        cfg = load_sectors_config()
        all_kws: list[str] = []
        for sec in cfg["sectors"]:
            all_kws.extend(sec["keywords"])
        # 允许少量重复（"光通信" 和 "光模块" 等），但不应有大量重复
        assert len(all_kws) == len(set(all_kws)), f"关键词重复: {all_kws}"
