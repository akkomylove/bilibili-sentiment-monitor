import hashlib
import sys
import time
from pathlib import Path
from typing import Any

# Force UTF-8 on stdout so the "Celery Worker" PowerShell window can
# render Chinese video titles correctly. Without this Windows defaults
# to GBK/cp936 and titles show as 涓€绫? etc.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import yaml

from app.config import settings
from app.database import SessionLocal
from app.models.comment import Comment
from app.models.danmaku import Danmaku
from app.models.video import Video
from app.services.crawler.bilibili import BilibiliAPI
from app.tasks import celery_app

SALT = "bilibili_sentiment_salt_2026"


def hash_mid(mid: str) -> str:
    return hashlib.sha256(f"{mid}{SALT}".encode()).hexdigest()[:16]


# === v2: 投资领域配置加载 ===

def _resolve_sectors_config_path() -> Path:
    """解析 sectors.yaml 路径：优先按 settings.sectors_config_path 绝对路径，
    失败时回退到项目根/config/sectors.yaml
    """
    configured = settings.sectors_config_path
    # 1) 已是绝对路径
    p = Path(configured)
    if p.is_absolute() and p.exists():
        return p
    # 2) 相对当前工作目录
    if p.exists():
        return p
    # 3) 相对项目根（this file's parent's parent）
    project_root = Path(__file__).resolve().parent.parent
    candidate = project_root / configured
    if candidate.exists():
        return candidate
    raise FileNotFoundError(
        f"sectors.yaml 找不到，已尝试: {configured!r}、{p}、{candidate}"
    )


def load_sectors_config() -> dict[str, Any]:
    """加载投资领域 YAML 配置

    Returns:
        {
            "sectors": [
                {
                    "name": "半导体",
                    "keywords": ["半导体", "芯片", ...],
                    "hot_threshold": {"min_play": 10000, "min_comment": 50},
                },
                ...
            ],
            "crawl": {
                "max_videos_per_keyword": 10,
                "max_pages": 3,
                "max_comments_per_video": 100,
                "reply_top_percent": 10,
                "schedule": "0 9 * * *",
                ...
            },
        }
    """
    path = _resolve_sectors_config_path()
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if "sectors" not in data:
        raise ValueError(f"sectors.yaml 缺少 'sectors' 字段: {path}")
    # 兜底 crawl 块
    data.setdefault("crawl", {})
    return data


def _build_api() -> BilibiliAPI:
    return BilibiliAPI(
        timeout=30,
        cookie=settings.bilibili_cookie,
        wbi_img_url=settings.bilibili_wbi_img_url,
        wbi_sub_url=settings.bilibili_wbi_sub_url,
    )


def _build_api_no_cookie() -> BilibiliAPI:
    return BilibiliAPI(timeout=30)


@celery_app.task(bind=True)
def crawl_by_keyword(
    self,
    keyword_id: int,
    keyword: str,
    max_pages: int = 3,
    sort_order: str = "totalrank",
    min_play: int | None = None,
    min_comment: int | None = None,
    max_top: int = 100,
    reply_ratio: float = 0.1,
    enable_danmaku: bool = False,
    max_videos_per_keyword: int = 20,
):
    """按关键词采集视频 + 评论

    Args:
        keyword_id: 数据库 MonitorKeyword.id
        keyword: 搜索关键词
        max_pages: 搜索结果翻页数（每页 20 条）
        sort_order: 搜索排序
        min_play: 最低播放量（None=不限）
        min_comment: 最低评论数（None=不限）
        max_top: 每视频最多热评数
        reply_ratio: 回复占比
        enable_danmaku: 是否抓取弹幕（v2 默认 False）
        max_videos_per_keyword: 单关键词最终保留的视频数上限
            （截断在热度过滤之后；防止分页拉满 5×20=100 条）
    """
    self.update_state(state="PROGRESS", meta={"stage": "searching", "keyword": keyword, "sort": sort_order})

    def _log(msg: str) -> None:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

    _log(f"[CRAWL] keyword='{keyword}' (id={keyword_id}) START  max_pages={max_pages}  max_videos={max_videos_per_keyword}")

    api = _build_api()
    api_no_cookie = _build_api_no_cookie()

    all_videos = []
    for page in range(1, max_pages + 1):
        page_videos = api.search_videos(keyword, page=page, page_size=20, order=sort_order)
        if not page_videos:
            _log(f"[SEARCH] page={page} returned 0 videos, stop")
            break
        all_videos.extend(page_videos)
        _log(f"[SEARCH] page={page} got {len(page_videos)} videos (running total {len(all_videos)})")
        time.sleep(1.0)

    # 硬截断：单关键词总视频数不超过 max_videos_per_keyword
    if max_videos_per_keyword and len(all_videos) > max_videos_per_keyword:
        _log(f"[TRIM] {len(all_videos)} -> {max_videos_per_keyword} (max_videos_per_keyword cap)")
        all_videos = all_videos[:max_videos_per_keyword]

    # v2 热度过滤
    def _pass_hot(v) -> bool:
        if min_play is not None and (v.play_count or 0) < min_play:
            return False
        if min_comment is not None and (v.comment_count or 0) < min_comment:
            return False
        return True

    filtered_videos = [v for v in all_videos if _pass_hot(v)]

    self.update_state(state="PROGRESS", meta={
        "stage": "fetching_details",
        "videos_found": len(all_videos),
        "videos_after_filter": len(filtered_videos),
    })

    db = SessionLocal()
    total_comments = 0
    total_danmaku = 0

    try:
        for i, video_info in enumerate(filtered_videos):
            self.update_state(state="PROGRESS", meta={
                "stage": "processing_video",
                "video": video_info.bvid,
                "progress": f"{i + 1}/{len(filtered_videos)}",
            })
            short_title = (video_info.title or '')[:36].replace('\n', ' ')
            _log(f"[VIDEO {i+1}/{len(filtered_videos)}] {video_info.bvid}  '{short_title}'  play={video_info.play_count:,}  cmt={video_info.comment_count:,}")

            existing = db.query(Video).filter(Video.bvid == video_info.bvid).first()
            if existing:
                # v2.1 BUG fix: 二次爬取改为轻量更新（更新元数据 + 评论增量）
                # 仅刷新播放/评论/弹幕数等动态字段；标题/描述/keyword_id 不动
                detailed_existing = api.get_video_info(video_info.bvid)
                if detailed_existing:
                    existing.play_count = detailed_existing.play_count
                    existing.danmaku_count = detailed_existing.danmaku_count
                    existing.comment_count = detailed_existing.comment_count
                    _log(f"  [UPDATE] meta refreshed: play={existing.play_count:,} cmt={existing.comment_count:,}")
                # 弹幕和评论都跳过（v2 默认不抓弹幕；评论走下方 rpid 增量分支）
                target_bvid = existing.bvid
            else:
                detailed = api.get_video_info(video_info.bvid)
                if detailed:
                    cid = detailed.cid
                    video_info = detailed
                else:
                    cid = video_info.cid

                video = Video(
                    bvid=video_info.bvid,
                    title=video_info.title,
                    description=video_info.description,
                    play_count=video_info.play_count,
                    danmaku_count=video_info.danmaku_count,
                    comment_count=video_info.comment_count,
                    pub_time=video_info.pub_time,
                    partition_tag=video_info.partition_tag,
                    keyword_id=keyword_id,
                )
                db.add(video)
                db.flush()
                target_bvid = video.bvid
                _log(f"  [INSERT] new video saved (id={video.id})")
                # v2 默认不抓弹幕
                if enable_danmaku and cid > 0:
                    try:
                        danmakus = api_no_cookie.get_all_danmaku_proto(cid, duration=video_info.duration)
                        for d in danmakus:
                            dm = Danmaku(
                                video_bvid=video_info.bvid,
                                content=d.content[:500],
                                timeline=d.timeline,
                                send_time=d.send_time,
                            )
                            db.add(dm)
                            total_danmaku += 1
                    except Exception:
                        pass

            try:
                comments = api_no_cookie.get_top_comments_with_replies(
                    target_bvid, max_top=max_top, reply_ratio=reply_ratio
                )
                _log(f"  [COMMENTS] fetched {len(comments)} candidates, processing...")
                new_count = 0
                dup_count = 0
                for c in comments:
                    existing_comment = db.query(Comment).filter(Comment.rpid == c.rpid).first()
                    if existing_comment:
                        dup_count += 1
                        continue
                    try:
                        comment = Comment(
                            rpid=c.rpid,
                            video_bvid=target_bvid,
                            user_mid=hash_mid(c.user_mid),
                            raw_content=c.content,
                            content=c.content,
                            like_count=c.like_count,
                            reply_count=c.reply_count,
                            has_image=c.has_image,
                            image_urls=c.image_urls if c.image_urls else None,
                            pub_time=c.pub_time,
                            parent_rpid=c.parent_rpid or 0,
                        )
                        db.add(comment)
                        db.flush()  # 立即发现唯一键冲突
                        total_comments += 1
                        new_count += 1
                    except Exception:
                        # rpid 唯一约束冲突：可能同一评论被多个关键词抓到，跳过
                        db.rollback()
                        dup_count += 1
                        continue
                _log(f"  [COMMENTS] +{new_count} new, {dup_count} dup (running total: {total_comments:,})")
            except Exception as e:
                _log(f"  [COMMENTS] ERROR: {type(e).__name__}: {str(e)[:80]}")

            time.sleep(0.8)

        db.commit()

        from app.models.monitor import MonitorKeyword

        mk = db.query(MonitorKeyword).filter(MonitorKeyword.id == keyword_id).first()
        if mk:
            from datetime import datetime

            mk.last_crawled_at = datetime.now()
            db.commit()

        _log(f"[CRAWL] keyword='{keyword}' DONE  videos={len(filtered_videos)}  comments={total_comments:,}  danmaku={total_danmaku:,}")

        return {
            "keyword_id": keyword_id,
            "keyword": keyword,
            "status": "completed",
            "videos_found": len(all_videos),
            "videos_saved": len(filtered_videos),
            "comments_saved": total_comments,
            "danmaku_saved": total_danmaku,
        }
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


@celery_app.task(bind=True)
def crawl_comments_deep(self, bvid: str, max_pages: int = 20):
    self.update_state(state="PROGRESS", meta={"stage": "fetching", "bvid": bvid})

    api = _build_api()
    # 使用新的热评+回复采集策略：前100条热评 + 10%回复
    all_comments = api.get_top_comments_with_replies(bvid, max_top=100, reply_ratio=0.1)

    db = SessionLocal()
    total_new = 0
    try:
        for c in all_comments:
            existing = db.query(Comment).filter(Comment.rpid == c.rpid).first()
            if existing:
                continue
            comment = Comment(
                rpid=c.rpid,
                video_bvid=bvid,
                user_mid=hash_mid(c.user_mid),
                raw_content=c.content,
                content=c.content,
                like_count=c.like_count,
                reply_count=c.reply_count,
                has_image=c.has_image,
                image_urls=c.image_urls if c.image_urls else None,
                pub_time=c.pub_time,
                parent_rpid=c.parent_rpid or 0,
            )
            db.add(comment)
            total_new += 1

        db.commit()
        return {
            "bvid": bvid,
            "status": "completed",
            "total_fetched": len(all_comments),
            "new_saved": total_new,
        }
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


@celery_app.task(bind=True)
def crawl_danmaku_proto(self, bvid: str):
    self.update_state(state="PROGRESS", meta={"stage": "fetching", "bvid": bvid})

    api = _build_api()
    video_info = api.get_video_info(bvid)
    if not video_info or video_info.cid <= 0:
        return {"status": "failed", "error": "无法获取视频信息或cid"}

    api_no_cookie = _build_api_no_cookie()
    danmakus = api_no_cookie.get_all_danmaku_proto(video_info.cid, duration=video_info.duration)

    db = SessionLocal()
    total_new = 0
    try:
        for d in danmakus:
            dm = Danmaku(
                video_bvid=bvid,
                content=d.content[:500],
                timeline=d.timeline,
                send_time=d.send_time,
            )
            db.add(dm)
            total_new += 1

        db.commit()
        return {
            "bvid": bvid,
            "status": "completed",
            "total_fetched": len(danmakus),
            "new_saved": total_new,
        }
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


@celery_app.task(bind=True)
def auto_crawl_keywords(self):
    """自动采集所有活跃关键词的视频数据

    v2 行为：
    - 优先遍历 sectors.yaml 中所有板块+关键词（覆盖用户已注册但 YAML 中没有的关键词）
    - 对每个关键词应用该板块的 hot_threshold 热度过滤
    - 评论采集：max_top=100, reply_ratio=0.1（与 spec 一致）
    - 不抓弹幕
    """
    self.update_state(state="PROGRESS", meta={"stage": "loading_config"})

    # 1) 加载 YAML 配置
    try:
        config = load_sectors_config()
        sectors = config.get("sectors", [])
        crawl_cfg = config.get("crawl", {})
    except Exception as e:
        # 配置加载失败时，降级用 MonitorKeyword 全表
        sectors = []
        crawl_cfg = {}

    default_max_pages = int(crawl_cfg.get("max_pages", 3))
    default_max_videos_per_keyword = int(crawl_cfg.get("max_videos_per_keyword", 20))
    default_max_top = int(crawl_cfg.get("max_comments_per_video", 100))
    default_reply_ratio = float(crawl_cfg.get("reply_top_percent", 10)) / 100.0
    default_sort_order = crawl_cfg.get("sort_order", "totalrank")

    # 2) 组装 (sector_name, keyword, hot_threshold) 三元组
    from app.models.monitor import MonitorKeyword

    db = SessionLocal()
    try:
        active_keywords = db.query(MonitorKeyword).filter(MonitorKeyword.is_active).all()

        # 关键词 → 板块 映射表（用于快速查 hot_threshold）
        kw_to_sector: dict[str, dict[str, Any]] = {}
        for sec in sectors:
            for kw in sec.get("keywords", []):
                kw_to_sector[kw] = sec

        dispatched = []
        for mk in active_keywords:
            sec = kw_to_sector.get(mk.keyword)
            if sec:
                threshold = sec.get("hot_threshold", {})
                min_play = threshold.get("min_play")
                min_comment = threshold.get("min_comment")
            else:
                min_play = None
                min_comment = None

            task = crawl_by_keyword.delay(
                mk.id,
                mk.keyword,
                max_pages=default_max_pages,
                sort_order=mk.sort_order or default_sort_order,
                min_play=min_play,
                min_comment=min_comment,
                max_top=default_max_top,
                reply_ratio=default_reply_ratio,
                enable_danmaku=False,
                max_videos_per_keyword=default_max_videos_per_keyword,
            )
            dispatched.append({
                "keyword_id": mk.id,
                "keyword": mk.keyword,
                "task_id": task.id,
                "min_play": min_play,
                "min_comment": min_comment,
            })

        return {
            "status": "dispatched",
            "keywords_count": len(active_keywords),
            "sectors_loaded": len(sectors),
            "dispatched": dispatched,
        }
    finally:
        db.close()


@celery_app.task(bind=True)
def crawl_hot_search(self, max_items: int = 10):
    """采集B站热搜榜并进行情感分析"""
    if self.request.id:
        self.update_state(state="PROGRESS", meta={"stage": "fetching_hot_search"})

    api = _build_api()
    hot_list = api.get_hot_search()
    if not hot_list:
        return {"status": "failed", "error": "无法获取热搜数据"}

    hot_list = hot_list[:max_items]

    from snownlp import SnowNLP

    db = SessionLocal()
    try:
        from app.models.hot_search import HotSearch

        # 清空旧数据
        db.query(HotSearch).delete()
        db.commit()

        saved = []
        for item in hot_list:
            if self.request.id:
                self.update_state(state="PROGRESS", meta={
                    "stage": "analyzing",
                    "keyword": item.keyword,
                    "rank": item.rank,
                })

            # 搜索该关键词的相关视频
            videos = api.search_videos(item.keyword, page=1, page_size=10)
            video_count = len(videos)

            # 采集这些视频的评论进行情感分析
            all_comments: list[str] = []
            for v in videos[:3]:
                try:
                    comments = api.get_top_comments_with_replies(v.bvid, max_top=20, reply_ratio=0.0)
                    for c in comments:
                        if not c.content.startswith("[回复"):
                            all_comments.append(c.content)
                except Exception:
                    pass
                time.sleep(0.5)

            # 情感分析
            positive = neutral = negative = 0
            for text in all_comments:
                if not text.strip():
                    neutral += 1
                    continue
                try:
                    score = SnowNLP(text).sentiments
                except Exception:
                    score = 0.5
                if score > 0.6:
                    positive += 1
                elif score < 0.4:
                    negative += 1
                else:
                    neutral += 1

            total = len(all_comments)
            sentiment_summary = "中性"
            if total > 0:
                pos_ratio = positive / total
                neg_ratio = negative / total
                if pos_ratio > 0.5:
                    sentiment_summary = "正面"
                elif neg_ratio > 0.4:
                    sentiment_summary = "负面"
                elif neg_ratio > pos_ratio:
                    sentiment_summary = "偏负面"
                elif pos_ratio > neg_ratio:
                    sentiment_summary = "偏正面"

            hs = HotSearch(
                keyword=item.keyword,
                rank=item.rank,
                heat_score=item.heat_score,
                sentiment_positive=round(positive / max(total, 1), 4),
                sentiment_neutral=round(neutral / max(total, 1), 4),
                sentiment_negative=round(negative / max(total, 1), 4),
                sentiment_summary=sentiment_summary,
                video_count=video_count,
                comment_count=total,
            )
            db.add(hs)
            saved.append({
                "keyword": item.keyword,
                "rank": item.rank,
                "sentiment_summary": sentiment_summary,
                "comment_count": total,
            })

        db.commit()
        return {
            "status": "completed",
            "total": len(saved),
            "items": saved,
        }
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
