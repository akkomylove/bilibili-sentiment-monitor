

def deduplicate_comments(comments):
    seen = set()
    result = []
    for c in comments:
        key = (c["content"], c["author"])
        if key not in seen:
            seen.add(key)
            result.append(c)
    return result


def clean_data(comments):
    result = []
    for c in comments:
        content = c.get("content", "")
        if not content or content.strip() == "":
            continue
        cleaned = content.strip()
        if cleaned:
            result.append({**c, "content": cleaned})
    return result


def desensitize_data(comments):
    import re
    patterns = {
        "phone": re.compile(r"1[3-9]\d{9}"),
        "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    }
    result = []
    for c in comments:
        content = c.get("content", "")
        for name, pattern in patterns.items():
            content = pattern.sub(f"[{name}]", content)
        result.append({**c, "content": content})
    return result


def calculate_quality_score(comment):
    content_len = len(comment.get("content", ""))
    likes = comment.get("likes", 0)
    replies = comment.get("replies_count", 0)
    length_score = min(content_len / 50 * 20, 20)
    like_score = min(likes * 0.5, 30)
    reply_score = min(replies * 2, 20)
    quality_score = length_score + like_score + reply_score
    return round(quality_score, 2)


class TestDeduplicateComments:
    """测试评论去重逻辑"""

    def test_remove_exact_duplicates(self):
        """测试去除完全重复评论"""
        comments = [
            {"content": "相同内容", "author": "用户A"},
            {"content": "相同内容", "author": "用户A"},
            {"content": "不同内容", "author": "用户B"},
        ]

        result = deduplicate_comments(comments)

        assert len(result) == 2
        contents = [c["content"] for c in result]
        assert contents.count("相同内容") == 1

    def test_empty_list(self):
        """测试空列表"""
        result = deduplicate_comments([])
        assert result == []


class TestCleanData:
    """测试数据清洗逻辑"""

    def test_remove_html_tags(self):
        """测试去除前后空白"""
        comments = [
            {"content": "  评论内容  ", "author": "用户"},
        ]

        result = clean_data(comments)

        assert result[0]["content"] == "评论内容"

    def test_filter_empty_comments(self):
        """测试过滤空评论"""
        comments = [
            {"content": "", "author": "用户A"},
            {"content": "   ", "author": "用户B"},
            {"content": "有效评论", "author": "用户C"},
        ]

        result = clean_data(comments)

        assert len(result) == 1
        assert result[0]["content"] == "有效评论", f"Got: {repr(result[0]['content'])}"
        assert result[0]["author"] == "用户C"


class TestDesensitizeData:
    """测试数据脱敏逻辑"""

    def test_hide_phone_numbers(self):
        """测试手机号脱敏"""
        comments = [
            {"content": "我的电话是13812345678", "author": "用户"},
        ]

        result = desensitize_data(comments)

        assert "13812345678" not in result[0]["content"]
        assert "[phone]" in result[0]["content"]

    def test_hide_email(self):
        """测试邮箱脱敏"""
        comments = [
            {"content": "联系邮箱 test@example.com", "author": "用户"},
        ]

        result = desensitize_data(comments)

        assert "test@example.com" not in result[0]["content"]

    def test_no_sensitive_info(self):
        """测试无敏感信息时不改变"""
        comments = [
            {"content": "普通评论内容", "author": "用户"},
        ]

        result = desensitize_data(comments)

        assert result[0]["content"] == "普通评论内容"


class TestCalculateQualityScore:
    """测试质量评分计算"""

    def test_high_quality_comment(self):
        """测试高质量评论"""
        comment = {
            "content": "这是一条非常有价值的评论，内容充实，观点明确，数据分析很有用",
            "likes": 100,
            "replies_count": 20,
        }

        score = calculate_quality_score(comment)

        assert score >= 50

    def test_low_quality_comment(self):
        """测试低质量评论"""
        comment = {
            "content": "666",
            "likes": 0,
            "replies_count": 0,
        }

        score = calculate_quality_score(comment)

        assert score < 50

    def test_empty_comment(self):
        """测试空评论"""
        comment = {
            "content": "",
            "likes": 0,
            "replies_count": 0,
        }

        score = calculate_quality_score(comment)

        assert score == 0
