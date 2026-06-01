import hashlib
import time

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


def _build_api() -> BilibiliAPI:
    return BilibiliAPI(
        timeout=30,
        cookie=settings.bilibili_cookie,
        wbi_img_url=settings.bilibili_wbi_img_url,
        wbi_sub_url=settings.bilibili_wbi_sub_url,
    )


def _build_api_no_cookie() -> BilibiliAPI:
    return BilibiliAPI(timeout=30)


@celery_app.task(bind=True, name="crawl_by_keyword")
def crawl_by_keyword(self, keyword_id: int, keyword: str, max_pages: int = 5, sort_order: str = "totalrank"):
    self.update_state(state="PROGRESS", meta={"stage": "searching", "keyword": keyword, "sort": sort_order})

    api = _build_api()
    api_no_cookie = _build_api_no_cookie()

    all_videos = []
    for page in range(1, max_pages + 1):
        page_videos = api.search_videos(keyword, page=page, page_size=20, order=sort_order)
        if not page_videos:
            break
        all_videos.extend(page_videos)
        time.sleep(1.0)

    self.update_state(state="PROGRESS", meta={
        "stage": "fetching_details",
        "videos_found": len(all_videos),
    })

    db = SessionLocal()
    total_comments = 0
    total_danmaku = 0

    try:
        for i, video_info in enumerate(all_videos):
            self.update_state(state="PROGRESS", meta={
                "stage": "processing_video",
                "video": video_info.bvid,
                "progress": f"{i + 1}/{len(all_videos)}",
            })

            existing = db.query(Video).filter(Video.bvid == video_info.bvid).first()
            if existing:
                continue

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

            if cid > 0:
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
                comments = api_no_cookie.get_all_comments(video_info.bvid, max_pages=5, page_size=20)
                for c in comments:
                    existing_comment = db.query(Comment).filter(Comment.rpid == c.rpid).first()
                    if existing_comment:
                        continue
                    comment = Comment(
                        rpid=c.rpid,
                        video_bvid=video_info.bvid,
                        user_mid=hash_mid(c.user_mid),
                        raw_content=c.content,
                        content=c.content,
                        like_count=c.like_count,
                        reply_count=c.reply_count,
                        has_image=c.has_image,
                        image_urls=c.image_urls if c.image_urls else None,
                        pub_time=c.pub_time,
                    )
                    db.add(comment)
                    total_comments += 1
            except Exception:
                pass

            time.sleep(0.8)

        db.commit()

        from app.models.monitor import MonitorKeyword

        mk = db.query(MonitorKeyword).filter(MonitorKeyword.id == keyword_id).first()
        if mk:
            from datetime import datetime

            mk.last_crawled_at = datetime.now()
            db.commit()

        return {
            "keyword_id": keyword_id,
            "keyword": keyword,
            "status": "completed",
            "videos_saved": len(all_videos),
            "comments_saved": total_comments,
            "danmaku_saved": total_danmaku,
        }
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


@celery_app.task(bind=True, name="crawl_comments_deep")
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


@celery_app.task(bind=True, name="crawl_danmaku_proto")
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


@celery_app.task(bind=True, name="auto_crawl_keywords")
def auto_crawl_keywords(self):
    """自动采集所有活跃关键词的视频数据"""
    db = SessionLocal()
    try:
        from app.models.monitor import MonitorKeyword

        active_keywords = db.query(MonitorKeyword).filter(MonitorKeyword.is_active).all()
        dispatched = []
        for mk in active_keywords:
            task = crawl_by_keyword.delay(mk.id, mk.keyword, sort_order=mk.sort_order)
            dispatched.append({"keyword_id": mk.id, "keyword": mk.keyword, "task_id": task.id})

        return {
            "status": "dispatched",
            "keywords_count": len(active_keywords),
            "dispatched": dispatched,
        }
    finally:
        db.close()


@celery_app.task(bind=True, name="crawl_hot_search")
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
