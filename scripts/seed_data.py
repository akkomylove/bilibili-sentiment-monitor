"""
演示数据填充脚本
用法: python scripts/seed_data.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models.monitor import MonitorKeyword
from app.models.video import Video
from app.models.comment import Comment
from app.models.danmaku import Danmaku
from app.models.governance import GovernanceRule


def seed_monitor_keywords(db):
    keywords = [
        MonitorKeyword(keyword="Python教程", partition_filter="科技", crawl_interval=60, is_active=True),
        MonitorKeyword(keyword="数据分析", partition_filter="科技,知识", crawl_interval=120, is_active=True),
        MonitorKeyword(keyword="机器学习", partition_filter="科技", crawl_interval=180, is_active=False),
    ]
    for kw in keywords:
        existing = db.query(MonitorKeyword).filter(MonitorKeyword.keyword == kw.keyword).first()
        if not existing:
            db.add(kw)
    db.commit()
    print("✅ 监控关键词已填充")


def seed_governance_rules(db):
    rules = [
        GovernanceRule(rule_name="评论长度截断", rule_type="format_check", rule_config={"max_length": 2000}, phase="format_check", is_active=True),
        GovernanceRule(rule_name="重复评论去重", rule_type="dedup", rule_config={"strategy": "exact"}, phase="dedup", is_active=True),
        GovernanceRule(rule_name="HTML标签清洗", rule_type="clean", rule_config={"remove_tags": ["br", "div"]}, phase="clean", is_active=True),
        GovernanceRule(rule_name="敏感信息脱敏", rule_type="desensitize", rule_config={"patterns": ["phone", "email"]}, phase="desensitize", is_active=True),
    ]
    for rule in rules:
        existing = db.query(GovernanceRule).filter(GovernanceRule.rule_name == rule.rule_name).first()
        if not existing:
            db.add(rule)
    db.commit()
    print("✅ 治理规则已填充")


def seed_videos_and_comments(db):
    base_time = datetime(2026, 5, 1, 12, 0, 0)
    videos = [
        Video(bvid="BV1xx411c7mD", title="Python入门教程", description="适合新手的Python教程", play_count=150000, danmaku_count=3000, comment_count=500, pub_time=base_time, partition_tag="科技", keyword_id=1),
        Video(bvid="BV1yy411c7mE", title="数据分析实战", description="用Python做数据分析", play_count=80000, danmaku_count=1500, comment_count=300, pub_time=base_time - timedelta(days=1), partition_tag="科技", keyword_id=2),
    ]
    for video in videos:
        existing = db.query(Video).filter(Video.bvid == video.bvid).first()
        if not existing:
            db.add(video)
    db.commit()

    comments = [
        Comment(rpid=10001, video_bvid="BV1xx411c7mD", user_mid="user_a_hash", content="这个教程太棒了！讲得很清楚", like_count=50, reply_count=5, has_image=False, pub_time=base_time + timedelta(hours=1)),
        Comment(rpid=10002, video_bvid="BV1xx411c7mD", user_mid="user_b_hash", content="有点难理解，希望能多举例子", like_count=20, reply_count=2, has_image=False, pub_time=base_time + timedelta(hours=2)),
        Comment(rpid=10003, video_bvid="BV1xx411c7mD", user_mid="user_c_hash", content="666666", like_count=5, reply_count=0, has_image=False, pub_time=base_time + timedelta(hours=3)),
        Comment(rpid=10004, video_bvid="BV1yy411c7mE", user_mid="user_d_hash", content="数据分析很有用，学到了", like_count=30, reply_count=3, has_image=False, pub_time=base_time + timedelta(hours=1)),
        Comment(rpid=10005, video_bvid="BV1yy411c7mE", user_mid="user_e_hash", content="代码能分享一下吗", like_count=15, reply_count=1, has_image=False, pub_time=base_time + timedelta(hours=2)),
    ]
    for comment in comments:
        existing = db.query(Comment).filter(Comment.rpid == comment.rpid).first()
        if not existing:
            db.add(comment)
    db.commit()
    print("✅ 视频和评论演示数据已填充")


def seed_danmaku(db):
    danmakus = [
        Danmaku(video_bvid="BV1xx411c7mD", content="来了来了", timeline=10.5, send_time=datetime(2026, 5, 1, 12, 5, 0)),
        Danmaku(video_bvid="BV1xx411c7mD", content="前排", timeline=15.0, send_time=datetime(2026, 5, 1, 12, 5, 5)),
        Danmaku(video_bvid="BV1xx411c7mD", content="讲得好", timeline=30.2, send_time=datetime(2026, 5, 1, 12, 6, 0)),
        Danmaku(video_bvid="BV1xx411c7mD", content="666", timeline=45.0, send_time=datetime(2026, 5, 1, 12, 6, 30)),
        Danmaku(video_bvid="BV1xx411c7mD", content="收藏了", timeline=60.0, send_time=datetime(2026, 5, 1, 12, 7, 0)),
    ]
    for dm in danmakus:
        db.add(dm)
    db.commit()
    print("✅ 弹幕演示数据已填充")


def main():
    db = SessionLocal()
    try:
        seed_monitor_keywords(db)
        seed_governance_rules(db)
        seed_videos_and_comments(db)
        seed_danmaku(db)
        print("\n🎉 所有演示数据填充完成！")
    finally:
        db.close()


if __name__ == "__main__":
    main()
