"""
小说文本解析器

负责将原始小说文本按章节拆分，提取章节标题、段落，
并进行基础的 NLP 预处理（分句、命名实体识别提示等）。
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class Chapter:
    """解析后的章节"""
    number: int
    title: str = ""
    raw_text: str = ""
    paragraphs: List[str] = field(default_factory=list)
    word_count: int = 0
    start_line: int = 0
    end_line: int = 0

    def __repr__(self) -> str:
        return f"Chapter({self.number}, '{self.title}', {self.word_count} words)"


@dataclass
class ParsedNovel:
    """解析后的小说"""
    title: str = ""
    author: str = ""
    chapters: List[Chapter] = field(default_factory=list)
    total_words: int = 0
    raw_text: str = ""

    @property
    def chapter_count(self) -> int:
        return len(self.chapters)


class NovelParser:
    """
    小说文本解析器

    支持多种章节标记模式：
    - "第X章" / "Chapter X" / "CH X"
    - "第X回"（章回体）
    - "Part X" / "卷X"
    - 数字序号分隔符
    """

    # 章节检测正则模式（按优先级排序）
    CHAPTER_PATTERNS = [
        # 中文：第X章、第X回
        re.compile(
            r'^\s*(第[零一二三四五六七八九十百千万\d]+[章回节卷部集篇])\s*[：:]*\s*(.*?)\s*$',
            re.MULTILINE
        ),
        # 中文：第一章、第二章
        re.compile(
            r'^\s*(第[零一二三四五六七八九十百千万\d]+\s*章)\s*[：:]*\s*(.*?)\s*$',
            re.MULTILINE
        ),
        # 英文：Chapter X / CH X
        re.compile(
            r'^\s*(?:Chapter|CH|Ch\.?)\s*(\d+|[IVXLCDM]+)\s*[：:]*\s*(.*?)\s*$',
            re.MULTILINE | re.IGNORECASE
        ),
        # 英文：Part X
        re.compile(
            r'^\s*(?:Part|Section|Book)\s*(\d+|[IVXLCDM]+)\s*[：:]*\s*(.*?)\s*$',
            re.MULTILINE | re.IGNORECASE
        ),
        # 纯数字章节：1. / 1、/ #1
        re.compile(
            r'^\s*#?\s*(\d{1,3})\s*[\.、．\s]+\s*(.*?)\s*$',
            re.MULTILINE
        ),
    ]

    # 中文数字映射
    CN_NUM_MAP = {
        '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
        '十': 10, '百': 100, '千': 1000, '万': 10000,
    }

    # 罗马数字映射
    ROMAN_MAP = {
        'I': 1, 'V': 5, 'X': 10, 'L': 50,
        'C': 100, 'D': 500, 'M': 1000,
    }

    @classmethod
    def _parse_chinese_number(cls, text: str) -> int:
        """解析中文数字（如 '一百二十三' -> 123）"""
        total = 0
        current = 0
        for ch in text:
            if ch in cls.CN_NUM_MAP:
                val = cls.CN_NUM_MAP[ch]
                if val >= 10:
                    if current == 0:
                        current = 1
                    total += current * val
                    current = 0
                else:
                    current = val
            elif ch.isdigit():
                current = current * 10 + int(ch)
        total += current
        return total

    @classmethod
    def _parse_roman_number(cls, text: str) -> int:
        """解析罗马数字"""
        result = 0
        prev = 0
        for ch in reversed(text.upper()):
            val = cls.ROMAN_MAP.get(ch, 0)
            if val >= prev:
                result += val
            else:
                result -= val
            prev = val
        return result

    @classmethod
    def _parse_chapter_number(cls, num_str: str) -> int:
        """统一解析章节号"""
        num_str = num_str.strip()
        # 先尝试纯数字
        if num_str.isdigit():
            return int(num_str)
        # 尝试中文数字
        if any(ch in cls.CN_NUM_MAP for ch in num_str):
            return cls._parse_chinese_number(num_str)
        # 尝试罗马数字
        if all(ch in cls.ROMAN_MAP for ch in num_str.upper()):
            return cls._parse_roman_number(num_str)
        return -1

    @classmethod
    def _find_chapter_boundaries(cls, text: str) -> List[Tuple[int, int, str, int]]:
        """
        查找所有章节边界
        返回: [(起始位置, 结束位置, 章节标题, 章节号), ...]
        """
        boundaries: List[Tuple[int, int, str, int]] = []

        # 对每种模式尝试匹配
        for pattern in cls.CHAPTER_PATTERNS:
            matches = list(pattern.finditer(text))
            if len(matches) >= 3:  # 至少匹配到 3 个才算有效
                for m in matches:
                    num_str = m.group(1)
                    title = m.group(2) if m.lastindex and m.lastindex >= 2 else ""
                    # 从匹配中提取纯数字部分
                    num_match = re.search(r'(\d+|[零一二三四五六七八九十百千万]+|[IVXLCDM]+)', num_str)
                    if num_match:
                        ch_num = cls._parse_chapter_number(num_match.group(1))
                        if ch_num > 0:
                            boundaries.append((m.start(), m.end(), title.strip(), ch_num))
                if boundaries:
                    break  # 使用第一个成功匹配的模式

        # 按位置排序
        boundaries.sort(key=lambda x: x[0])
        return boundaries

    @classmethod
    def parse(cls, filepath: str) -> ParsedNovel:
        """
        解析小说文件

        Args:
            filepath: 小说文本文件路径

        Returns:
            ParsedNovel 对象

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 章节数不足（少于 3 章）
        """
        with open(filepath, "r", encoding="utf-8") as f:
            raw_text = f.read()

        return cls.parse_text(raw_text, source_name=filepath)

    @classmethod
    def parse_text(cls, text: str, source_name: str = "unknown") -> ParsedNovel:
        """
        解析小说文本

        Args:
            text: 小说全文
            source_name: 来源标识

        Returns:
            ParsedNovel 对象
        """
        novel = ParsedNovel(raw_text=text)
        lines = text.split("\n")

        # 尝试提取标题（前 5 行中取第一个非空且长度合适的行）
        for i, line in enumerate(lines[:5]):
            stripped = line.strip()
            if stripped and 3 <= len(stripped) <= 80 and not stripped.startswith(('第', 'Chapter')):
                novel.title = stripped
                break

        # 查找章节边界
        boundaries = cls._find_chapter_boundaries(text)

        if len(boundaries) < 3:
            # 回退策略：按大段落拆分
            boundaries = cls._fallback_split(text)

        if len(boundaries) < 3:
            raise ValueError(
                f"检测到的章节数不足（仅 {len(boundaries)} 章）。"
                f"本工具要求至少 3 章以上。请检查文本格式。"
            )

        # 按边界切分章节
        for idx, (start, end, ch_title, ch_num) in enumerate(boundaries):
            # 确定本章文本范围
            if idx + 1 < len(boundaries):
                chapter_text = text[end:boundaries[idx + 1][0]]
            else:
                chapter_text = text[end:]

            paragraphs = cls._split_paragraphs(chapter_text)
            word_count = sum(len(p) for p in paragraphs)

            # 计算在原文本中的行号
            start_line = text[:start].count("\n") + 1
            end_line = start_line + chapter_text.count("\n")

            chapter = Chapter(
                number=ch_num,
                title=ch_title,
                raw_text=chapter_text.strip(),
                paragraphs=paragraphs,
                word_count=word_count,
                start_line=start_line,
                end_line=end_line,
            )
            novel.chapters.append(chapter)
            novel.total_words += word_count

        # 如果标题未提取到，用文件名
        if not novel.title and source_name != "unknown":
            import os
            novel.title = os.path.splitext(os.path.basename(source_name))[0]

        return novel

    @classmethod
    def _fallback_split(cls, text: str) -> List[Tuple[int, int, str, int]]:
        """
        回退分割策略：按连续空行分隔的大段落作为章节
        """
        boundaries = []
        parts = re.split(r'\n{3,}', text)
        pos = 0
        ch_num = 1
        for part in parts:
            part = part.strip()
            if len(part) < 100:  # 太短的段落跳过
                pos = text.find(part, pos) + len(part)
                continue
            start = text.find(part, pos)
            end = start + len(part)
            boundaries.append((start, end, f"第{ch_num}章", ch_num))
            ch_num += 1
            pos = end
        return boundaries

    @classmethod
    def _split_paragraphs(cls, text: str) -> List[str]:
        """将章节文本拆分为段落"""
        paragraphs = []
        for para in re.split(r'\n\s*\n', text):
            para = para.strip()
            if para and len(para) > 5:
                paragraphs.append(para)
        return paragraphs

    @classmethod
    def extract_dialogues(cls, chapter: Chapter) -> List[Tuple[str, str]]:
        """
        从章节文本中提取对话
        返回: [(说话人, 对话内容), ...]

        支持多种引号格式：
        - 中文双引号：「」“”
        - 英文引号：""
        - 破折号引导的对话
        """
        dialogues: List[Tuple[str, str]] = []

        # 匹配中文引号对话
        patterns = [
            # 「...」
            re.compile(r'「([^」]+)」'),
            # “...”
            re.compile(r'["""]([^"""]+)["""]'),
            # "..."
            re.compile(r'"([^"]+)"'),
            # ——某人说："..."
            re.compile(r'——[^：:\n]+[：:]\s*["""「]([^"""」]+)["""」]'),
        ]

        for para in chapter.paragraphs:
            for pattern in patterns:
                for match in pattern.finditer(para):
                    dialogue_text = match.group(1).strip()
                    if len(dialogue_text) > 1:
                        # 尝试推断说话人（在引号前的文字中）
                        speaker = cls._infer_speaker(para, match.start())
                        dialogues.append((speaker, dialogue_text))

        return dialogues

    @classmethod
    def _infer_speaker(cls, paragraph: str, quote_pos: int) -> str:
        """从段落中推断说话人"""
        before = paragraph[:quote_pos]
        # 常见说话人引导模式
        patterns = [
            r'(\S{1,4})[说问道喊叫嚷言讲曰答]',
            r'(\S{1,4})[：:]$',
            r'(\S{1,4})[冷冷|淡淡|轻轻|大声|小声|低声|喃喃|愤愤|笑]',
        ]
        for pat in patterns:
            m = re.search(pat, before)
            if m:
                return m.group(1)
        return "未知"

    @classmethod
    def print_summary(cls, novel: ParsedNovel) -> None:
        """打印解析摘要"""
        print(f"\n{'='*50}")
        print(f"📖 小说解析结果: {novel.title}")
        print(f"{'='*50}")
        print(f"  总字数: {novel.total_words:,}")
        print(f"  章节数: {novel.chapter_count}")
        print(f"{'─'*50}")
        for ch in novel.chapters:
            dialogue_count = len(cls.extract_dialogues(ch))
            print(f"  📄 第{ch.number}章: {ch.title or '(无标题)'}")
            print(f"     字数: {ch.word_count:,} | 段落: {len(ch.paragraphs)} | 对话: {dialogue_count}")
        print(f"{'='*50}\n")
