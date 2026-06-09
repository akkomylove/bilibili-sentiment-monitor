"""Summarizer 抽象接口

未来可扩展：DeepSeekSummarizer、QwenSummarizer 等 LLM 实现。
本轮只提供接口骨架 + TemplateSummarizer 兜底实现。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Summarizer(ABC):
    """评论摘要器抽象类

    输入：评论列表（每条至少包含 content 字段；可包含 like_count / rpid / uname）
    输出：3-5 句中文摘要
    """

    @abstractmethod
    def summarize(self, comments: list[dict[str, Any]]) -> str:
        """对评论列表生成摘要

        Args:
            comments: 评论列表，每条评论是 dict 或带 content 属性的对象。

        Returns:
            中文摘要字符串（3-5 句）。
        """
        raise NotImplementedError
