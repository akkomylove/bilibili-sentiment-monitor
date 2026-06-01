from unittest.mock import MagicMock, patch

from app.services.crawler.bilibili import BilibiliAPI, VideoInfo, CommentInfo


class TestBilibiliAPI:
    """测试 BilibiliAPI"""

    def test_get_video_info(self):
        """测试获取视频信息"""
        api = BilibiliAPI()
        mock_data = {
            "code": 0,
            "data": {
                "bvid": "BV1xx411c7mD",
                "aid": 12345,
                "title": "测试视频",
                "desc": "这是一个测试视频",
                "stat": {
                    "view": 10000,
                    "danmaku": 500,
                    "reply": 200,
                },
                "pubdate": 1609459200,
                "tname": "科技",
                "cid": 123,
            },
        }

        with patch.object(api, "_get", return_value=mock_data):
            result = api.get_video_info("BV1xx411c7mD")

            assert isinstance(result, VideoInfo)
            assert result.bvid == "BV1xx411c7mD"
            assert result.title == "测试视频"
            assert result.play_count == 10000
            assert result.danmaku_count == 500
            assert result.comment_count == 200
            assert result.partition_tag == "科技"
            assert result.cid == 123

    def test_get_comments(self):
        """测试获取评论"""
        api = BilibiliAPI()
        mock_data = {
            "code": 0,
            "data": {
                "replies": [
                    {
                        "rpid": 1,
                        "mid": 123,
                        "content": {
                            "message": "评论内容",
                            "jump_structure": {},
                        },
                        "ctime": 1609459200,
                        "like": 10,
                        "rcount": 2,
                    }
                ]
            },
        }

        with patch.object(api, "_get", return_value=mock_data):
            result = api.get_comments("123")

            assert len(result) == 1
            assert isinstance(result[0], CommentInfo)
            assert result[0].content == "评论内容"
            assert result[0].like_count == 10
            assert result[0].reply_count == 2

    def test_get_video_info_error(self):
        """测试视频信息接口返回错误"""
        api = BilibiliAPI()
        mock_data = {"code": -404, "message": "视频不存在"}

        with patch.object(api, "_get", return_value=mock_data):
            result = api.get_video_info("BV1xx411c7mD")

            assert result is None

    def test_get_comments_empty(self):
        """测试空评论列表"""
        api = BilibiliAPI()
        mock_data = {"code": 0, "data": {"replies": []}}

        with patch.object(api, "_get", return_value=mock_data):
            result = api.get_comments("123")

            assert result == []
