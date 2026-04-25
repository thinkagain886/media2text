# -*- coding: utf-8 -*-
"""Markdown 格式化"""

from pathlib import Path


def format_single(filename: str, text: str) -> str:
    """单文件：# 文件名（去后缀）\\n\\n文本"""
    title = Path(filename).stem
    return f"# {title}\n\n{text}"


def format_merged(files: list[tuple[str, str]]) -> str:
    """
    合并：多个 # 标题 段落，用 \\n\\n---\\n\\n 分隔。
    files: [(filename, text), ...]
    """
    sections = []
    for filename, text in files:
        title = Path(filename).stem
        sections.append(f"# {title}\n\n{text}")
    return "\n\n---\n\n".join(sections)
