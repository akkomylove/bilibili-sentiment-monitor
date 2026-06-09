"""
B站 API 调用封装
支持 Cookie 认证 + Wbi 签名（搜索API）
"""
import hashlib
import time
import urllib.parse
from dataclasses import dataclass

import httpx

BILIBILI_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

BILIBILI_HEADERS = {
    "User-Agent": BILIBILI_USER_AGENT,
    "Referer": "https://www.bilibili.com/",
}

_SEARCH_URL = "https://api.bilibili.com/x/web-interface/wbi/search/type"
_VIDEO_INFO_URL = "https://api.bilibili.com/x/web-interface/view"
_COMMENTS_URL = "https://api.bilibili.com/x/v2/reply"
_REPLIES_URL = "https://api.bilibili.com/x/v2/reply/reply"
_DANMAKU_URL = "https://api.bilibili.com/x/v1/dm/list.so"
_DANMAKU_PROTO_URL = "https://api.bilibili.com/x/v2/dm/web/seg.so"
_HOT_SEARCH_URL = "https://s.search.bilibili.com/main/hotword"
_HOT_SEARCH_DETAIL_URL = "https://api.bilibili.com/x/web-interface/search/type"
_NAV_URL = "https://api.bilibili.com/x/web-interface/wbi/index/top/feed/rcmd"

MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
]


def _get_mixin_key(raw_key: str) -> str:
    return "".join(raw_key[i] for i in MIXIN_KEY_ENC_TAB if i < len(raw_key))[:32]


def _sign_params(params: dict, img_key: str, sub_key: str) -> dict:
    raw_key = img_key + sub_key
    mixin_key = _get_mixin_key(raw_key)
    params["wts"] = int(time.time())
    sorted_keys = sorted(params.keys())
    query_string = "&".join(
        f"{k}={urllib.parse.quote(str(params[k]), safe='')}"
        for k in sorted_keys
    )
    sign_string = query_string + mixin_key
    params["w_rid"] = hashlib.md5(sign_string.encode()).hexdigest()
    return params


@dataclass
class VideoInfo:
    bvid: str
    title: str
    description: str
    play_count: int
    danmaku_count: int
    comment_count: int
    pub_time: str
    partition_tag: str
    cid: int = 0
    aid: int = 0
    duration: int = 0


@dataclass
class CommentInfo:
    rpid: int
    user_mid: str
    content: str
    like_count: int
    reply_count: int
    has_image: bool
    image_urls: list[str]
    pub_time: str
    parent_rpid: int = 0


@dataclass
class DanmakuInfo:
    content: str
    timeline: float
    send_time: str
    mode: int = 0
    fontsize: int = 0
    color: int = 0
    mid_hash: str = ""
    weight: int = 0
    danmaku_id: int = 0
    pool: int = 0


@dataclass
class HotSearchInfo:
    keyword: str
    rank: int
    heat_score: int = 0
    icon: str = ""


class BilibiliAPI:
    def __init__(
        self,
        timeout: int = 30,
        cookie: str = "",
        wbi_img_url: str = "",
        wbi_sub_url: str = "",
    ):
        self.timeout = timeout
        self.cookie = cookie

        if wbi_img_url:
            self._img_key = wbi_img_url.rsplit("/", 1)[-1].split(".")[0]
        else:
            self._img_key = ""

        if wbi_sub_url:
            self._sub_key = wbi_sub_url.rsplit("/", 1)[-1].split(".")[0]
        else:
            self._sub_key = ""

        self._headers = dict(BILIBILI_HEADERS)
        if cookie:
            self._headers["Cookie"] = cookie

    def _get(self, url: str, params: dict | None = None, sign: bool = False) -> dict:
        if params is None:
            params = {}
        if sign and self._img_key and self._sub_key:
            params = _sign_params(dict(params), self._img_key, self._sub_key)

        with httpx.Client(timeout=self.timeout, headers=self._headers) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()

    def _get_text(self, url: str, params: dict | None = None) -> str:
        if params is None:
            params = {}
        with httpx.Client(timeout=self.timeout, headers=self._headers) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            return resp.text

    def _get_bytes(self, url: str, params: dict | None = None) -> bytes:
        if params is None:
            params = {}
        with httpx.Client(timeout=self.timeout, headers=self._headers) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            return resp.content

    def search_videos(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20,
        order: str = "totalrank",
    ) -> list[VideoInfo]:
        params = {
            "search_type": "video",
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
            "order": order,
        }
        data = self._get(_SEARCH_URL, params=params, sign=True)
        if data.get("code") != 0:
            return []

        results = []
        for item in data.get("data", {}).get("result", []):
            bvid = item.get("bvid", "")
            if not bvid:
                continue
            results.append(VideoInfo(
                bvid=bvid,
                title=item.get("title", "")
                    .replace('<em class="keyword">', "")
                    .replace("</em>", ""),
                description=item.get("description", ""),
                play_count=item.get("play", 0),
                danmaku_count=item.get("video_review", 0),
                comment_count=item.get("review", 0),
                pub_time=datetime_from_timestamp(item.get("pubdate", 0)),
                partition_tag=item.get("typename", ""),
            ))
        return results

    def get_danmaku_proto(self, cid: int, segment_index: int = 1) -> list[DanmakuInfo]:
        from app.services.crawler.danmaku_proto import parse_danmaku_seg

        params = {"oid": cid, "segment_index": segment_index, "type": 1}
        try:
            raw = self._get_bytes(_DANMAKU_PROTO_URL, params=params)
        except Exception:
            return []

        elements = parse_danmaku_seg(raw)
        results: list[DanmakuInfo] = []
        for elem in elements:
            results.append(DanmakuInfo(
                content=elem.get("content", ""),
                timeline=elem.get("timeline", 0.0),
                send_time=elem.get("send_time", ""),
                mode=elem.get("mode", 0),
                fontsize=elem.get("fontsize", 0),
                color=elem.get("color", 0),
                mid_hash=elem.get("mid_hash", ""),
                weight=elem.get("weight", 0),
                danmaku_id=elem.get("id", 0),
                pool=elem.get("pool", 0),
            ))
        return results

    def get_all_danmaku_proto(self, cid: int, duration: int = 0) -> list[DanmakuInfo]:
        all_danmakus: list[DanmakuInfo] = []
        seg_duration = 360
        if duration > 0:
            max_segments = max(1, (duration + seg_duration - 1) // seg_duration)
        else:
            max_segments = 20
        for seg in range(1, max_segments + 1):
            danmakus = self.get_danmaku_proto(cid, segment_index=seg)
            if not danmakus:
                break
            all_danmakus.extend(danmakus)
            time.sleep(0.3)
        return all_danmakus

    def get_video_info(self, bvid: str) -> VideoInfo | None:
        params = {"bvid": bvid}
        data = self._get(_VIDEO_INFO_URL, params=params)
        if data.get("code") != 0:
            return None

        item = data.get("data", {})
        return VideoInfo(
            bvid=item.get("bvid", bvid),
            title=item.get("title", ""),
            description=item.get("desc", ""),
            play_count=item.get("stat", {}).get("view", 0),
            danmaku_count=item.get("stat", {}).get("danmaku", 0),
            comment_count=item.get("stat", {}).get("reply", 0),
            pub_time=datetime_from_timestamp(item.get("pubdate", 0)),
            partition_tag=item.get("tname", ""),
            cid=item.get("cid", 0),
            aid=item.get("aid", 0),
            duration=item.get("duration", 0),
        )

    def _parse_reply(self, reply: dict) -> CommentInfo | None:
        content_obj = reply.get("content", {})
        image_urls = []
        if isinstance(content_obj, dict):
            message = content_obj.get("message", "")
            if not message:
                message = content_obj.get("text", "")
            if not message:
                message = content_obj.get("content", "")
            pics = content_obj.get("pictures", [])
            if not pics:
                pics = content_obj.get("pics", [])
            for pic in pics:
                if isinstance(pic, dict):
                    img_src = pic.get("img_src", "")
                    if not img_src:
                        img_src = pic.get("url", "")
                elif isinstance(pic, str):
                    img_src = pic
                else:
                    img_src = ""
                if img_src:
                    image_urls.append(img_src)
        else:
            message = str(content_obj) if content_obj else ""

        if not message:
            return None

        return CommentInfo(
            rpid=reply.get("rpid", 0),
            user_mid=str(reply.get("mid", 0)),
            content=message,
            like_count=reply.get("like", 0),
            reply_count=reply.get("rcount", 0),
            has_image=len(image_urls) > 0,
            image_urls=image_urls,
            pub_time=datetime_from_timestamp(reply.get("ctime", 0)),
            parent_rpid=reply.get("parent", 0) or 0,
        )

    def get_comments(self, oid: str, page: int = 1, page_size: int = 20, sort: int = 1) -> list[CommentInfo]:
        params = {
            "type": 1,
            "oid": oid,
            "pn": page,
            "ps": page_size,
            "sort": sort,
        }
        data = self._get(_COMMENTS_URL, params=params)
        if data.get("code") != 0:
            return []

        results = []
        replies = data.get("data", {}).get("replies", [])
        if not replies:
            return results

        for reply in replies:
            top_rpid = reply.get("rpid", 0)
            comment = self._parse_reply(reply)
            if comment:
                results.append(comment)

            folded_replies = reply.get("replies", [])
            if folded_replies:
                for folded in folded_replies:
                    folded_comment = self._parse_reply(folded)
                    if folded_comment:
                        folded_comment.content = f"[回复] {folded_comment.content}"
                        if not folded_comment.parent_rpid:
                            folded_comment.parent_rpid = top_rpid
                        results.append(folded_comment)

        return results

    def get_all_comments(self, oid: str, max_pages: int = 50, page_size: int = 20, sort: int = 1) -> list[CommentInfo]:
        all_comments: list[CommentInfo] = []
        for page in range(1, max_pages + 1):
            comments = self.get_comments(oid, page=page, page_size=page_size, sort=sort)
            if not comments:
                break
            all_comments.extend(comments)
            time.sleep(0.5)
        return all_comments

    def get_top_comments_with_replies(self, oid: str, max_top: int = 100, reply_ratio: float = 0.1) -> list[CommentInfo]:
        """获取前N条热评及其回复

        Args:
            oid: 视频oid
            max_top: 最多取多少条热评
            reply_ratio: 每条热评下取回复的比例（0.1=10%）
        """
        all_comments: list[CommentInfo] = []
        top_comments: list[CommentInfo] = []

        # 第1步：采集前max_top条热评（按热度排序，sort=1）
        pages_needed = (max_top + 19) // 20  # 每页20条
        for page in range(1, pages_needed + 1):
            comments = self.get_comments(oid, page=page, page_size=20, sort=1)
            if not comments:
                break
            # 分离主评论和回复（回复带有[回复]前缀）
            for c in comments:
                if not c.content.startswith("[回复]"):
                    top_comments.append(c)
                all_comments.append(c)
            if len(top_comments) >= max_top:
                break
            time.sleep(0.5)

        # 限制为max_top条
        top_comments = top_comments[:max_top]

        # 第2步：为每条热评采集回复
        for top in top_comments:
            if top.reply_count <= 0:
                continue
            # 计算需要采集的回复数
            max_replies = max(1, int(top.reply_count * reply_ratio))
            # B站回复API每页最多20条
            reply_pages = (max_replies + 19) // 20
            fetched_replies = 0
            for rp in range(1, reply_pages + 1):
                if fetched_replies >= max_replies:
                    break
                replies = self._get_replies(oid, top.rpid, page=rp, page_size=20)
                for r in replies:
                    if fetched_replies >= max_replies:
                        break
                    r.content = f"[回复@{top.user_mid}] {r.content}"
                    all_comments.append(r)
                    fetched_replies += 1
                time.sleep(0.3)

        return all_comments

    def _get_replies(self, oid: str, root: int, page: int = 1, page_size: int = 20) -> list[CommentInfo]:
        """获取指定评论的回复列表"""
        params = {
            "type": 1,
            "oid": oid,
            "root": root,
            "pn": page,
            "ps": page_size,
        }
        data = self._get(_REPLIES_URL, params=params)
        if data.get("code") != 0:
            return []

        results = []
        replies = data.get("data", {}).get("replies", [])
        if not replies:
            return results

        for reply in replies:
            comment = self._parse_reply(reply)
            if comment:
                results.append(comment)
        return results

    def get_danmaku(self, cid: int) -> list[DanmakuInfo]:
        params = {"oid": cid}
        resp_text = self._get_text(_DANMAKU_URL, params=params)

        results: list[DanmakuInfo] = []
        for line in resp_text.splitlines():
            line = line.strip()
            if not line or not line.startswith("<d "):
                continue
            p_attr = _extract_xml_attr(line, "p")
            if not p_attr:
                continue
            parts = p_attr.split(",")
            if len(parts) < 5:
                continue
            try:
                timeline = float(parts[0])
                send_timestamp = int(parts[4])
            except (ValueError, IndexError):
                continue
            content = _extract_xml_text(line)
            send_time_str = datetime_from_timestamp(send_timestamp)
            results.append(DanmakuInfo(
                content=content,
                timeline=timeline,
                send_time=send_time_str,
            ))
        return results

    def get_hot_search(self) -> list[HotSearchInfo]:
        """获取B站实时热搜榜"""
        try:
            data = self._get(_HOT_SEARCH_URL)
        except Exception:
            return []

        results: list[HotSearchInfo] = []
        if data.get("code") != 0:
            return results

        hot_list = data.get("list", [])
        for idx, item in enumerate(hot_list, start=1):
            keyword = item.get("keyword", "").strip()
            if not keyword:
                continue
            results.append(HotSearchInfo(
                keyword=keyword,
                rank=idx,
                heat_score=item.get("heat_score", 0),
                icon=item.get("icon", ""),
            ))
        return results


def _extract_xml_attr(line: str, attr: str) -> str:
    key = f'{attr}="'
    start = line.find(key)
    if start == -1:
        return ""
    start += len(key)
    end = line.find('"', start)
    if end == -1:
        return ""
    return line[start:end]


def _extract_xml_text(line: str) -> str:
    start = line.find(">")
    if start == -1:
        return ""
    start += 1
    end = line.find("</d>", start)
    if end == -1:
        return ""
    return line[start:end]


def datetime_from_timestamp(ts: int) -> str | None:
    if ts <= 0:
        return None
    from datetime import datetime, timedelta, timezone
    tz = timezone(timedelta(hours=8))
    return datetime.fromtimestamp(ts, tz=tz).strftime("%Y-%m-%d %H:%M:%S")
