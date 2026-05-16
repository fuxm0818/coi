"""文本提取与切块

从多种格式文档中提取纯文本，并按 token 切分为适合向量化的块。
支持格式：TXT、MD、PDF、DOCX、XLSX、CSV
"""

import csv
import logging
import os
from typing import List, Optional

from models import Chunk

logger = logging.getLogger(__name__)


class TextChunker:
    """文本提取与切块器

    负责从多种格式的文档中提取纯文本，并将文本切分为适合向量化的块。
    切块策略：按 512 token 切分，64 token 重叠，中文句子边界优先。
    """

    SUPPORTED_EXTENSIONS = {
        ".txt": "_extract_txt",
        ".md": "_extract_markdown",
        ".docx": "_extract_word",
        ".xlsx": "_extract_excel",
        ".pdf": "_extract_pdf",
        ".csv": "_extract_csv",
    }

    # 中文句子结束标点
    _SENTENCE_BOUNDARIES = set("。！？；\n")

    def __init__(self, tokenizer=None, chunk_size: int = 512, chunk_overlap: int = 64):
        """初始化 TextChunker

        Args:
            tokenizer: tokenizer 实例（用于 token 计数和切块）
            chunk_size: 目标块大小（token），默认 512
            chunk_overlap: 重叠区域大小（token），默认 64
        """
        self.tokenizer = tokenizer
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def extract_text(self, file_path: str) -> Optional[str]:
        """从文件提取纯文本

        根据文件扩展名分发到对应的提取器。
        提取失败或内容为空时返回 None。

        Args:
            file_path: 文件绝对路径

        Returns:
            提取的纯文本内容，失败返回 None
        """
        ext = os.path.splitext(file_path)[1].lower()

        if ext not in self.SUPPORTED_EXTENSIONS:
            logger.warning("不支持的文件格式: %s", file_path)
            return None

        method_name = self.SUPPORTED_EXTENSIONS[ext]
        extract_method = getattr(self, method_name)

        try:
            text = extract_method(file_path)
        except Exception as e:
            logger.error("文件提取失败 [%s]: %s", file_path, str(e))
            return None

        # 空白内容视为无效
        if text is None or text.strip() == "":
            logger.warning("文件内容为空: %s", file_path)
            return None

        return text

    def chunk(self, text: str) -> List[Chunk]:
        """将文本切分为多个 Chunk

        使用 tokenizer 进行 token 计数，按 chunk_size 切分，
        相邻块保留 chunk_overlap token 重叠。
        以中文标点为优先分割边界。

        Args:
            text: 原始文本

        Returns:
            切块列表
        """
        if not self.tokenizer:
            raise ValueError("tokenizer 未设置，无法进行切块")

        if not text or not text.strip():
            return []

        # 对整个文本进行 tokenize
        token_ids = self.tokenizer.encode(text, add_special_tokens=False)
        total_tokens = len(token_ids)

        if total_tokens == 0:
            return []

        # 总 token 数不超过 chunk_size，直接返回单个 chunk
        if total_tokens <= self.chunk_size:
            return [Chunk(text=text.strip(), index=0, token_count=total_tokens)]

        chunks: List[Chunk] = []
        start = 0
        chunk_index = 0

        while start < total_tokens:
            end = min(start + self.chunk_size, total_tokens)

            if end < total_tokens:
                # 尝试在句子边界处切分
                boundary = self._find_sentence_boundary(token_ids, start, end)
                if boundary > start:
                    end = boundary

            chunk_token_ids = token_ids[start:end]
            chunk_text = self.tokenizer.decode(chunk_token_ids, skip_special_tokens=True)
            chunk_token_count = len(chunk_token_ids)

            # 尾部不足 overlap 时合并到当前块
            remaining = total_tokens - end
            if remaining > 0 and remaining < self.chunk_overlap:
                chunk_token_ids = token_ids[start:]
                chunk_text = self.tokenizer.decode(chunk_token_ids, skip_special_tokens=True)
                chunk_token_count = len(chunk_token_ids)
                chunks.append(Chunk(
                    text=chunk_text.strip(),
                    index=chunk_index,
                    token_count=chunk_token_count,
                ))
                break

            chunks.append(Chunk(
                text=chunk_text.strip(),
                index=chunk_index,
                token_count=chunk_token_count,
            ))

            if end >= total_tokens:
                break

            # 下一块从 end - overlap 开始
            start = end - self.chunk_overlap
            chunk_index += 1

        # 最后一块不足 overlap 时合并到前一块
        if len(chunks) > 1 and chunks[-1].token_count < self.chunk_overlap:
            chunks.pop()
            merged_start = self._get_chunk_start(chunks)
            merged_token_ids = token_ids[merged_start:]
            merged_text = self.tokenizer.decode(merged_token_ids, skip_special_tokens=True)
            chunks[-1] = Chunk(
                text=merged_text.strip(),
                index=chunks[-1].index,
                token_count=len(merged_token_ids),
            )

        return chunks

    def _get_chunk_start(self, chunks: List[Chunk]) -> int:
        """计算最后一个 chunk 的起始 token 位置"""
        if len(chunks) <= 1:
            return 0
        start = 0
        for chunk in chunks[:-1]:
            end = start + chunk.token_count
            start = end - self.chunk_overlap
        return start

    def _find_sentence_boundary(self, token_ids: list, start: int, max_end: int) -> int:
        """在 token 序列中找到最近的中文句子边界

        从 max_end 向前搜索，找到最近的句子结束标点位置。
        """
        search_start = max(start + self.chunk_overlap, start)

        for pos in range(max_end - 1, search_start - 1, -1):
            token_text = self.tokenizer.decode([token_ids[pos]], skip_special_tokens=True)
            for ch in token_text:
                if ch in self._SENTENCE_BOUNDARIES:
                    return pos + 1

        return max_end

    # ===== 文本提取方法 =====

    def _extract_txt(self, file_path: str) -> Optional[str]:
        """提取 TXT 文件（UTF-8）"""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def _extract_markdown(self, file_path: str) -> Optional[str]:
        """提取 Markdown 文件，移除语法标记保留纯文本"""
        from markdown_it import MarkdownIt

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        md = MarkdownIt()
        tokens = md.parse(content)

        text_parts = []
        for token in tokens:
            if token.type == "inline" and token.children:
                inline_text = self._extract_inline_text(token.children)
                if inline_text:
                    text_parts.append(inline_text)
            elif token.type == "fence":
                if token.content:
                    text_parts.append(token.content.rstrip("\n"))

        return "\n".join(text_parts)

    def _extract_inline_text(self, children) -> str:
        """从 inline token 的 children 中提取纯文本"""
        parts = []
        for child in children:
            if child.type == "text":
                parts.append(child.content)
            elif child.type == "code_inline":
                parts.append(child.content)
            elif child.type in ("softbreak", "hardbreak"):
                parts.append("\n")
        return "".join(parts)

    def _extract_word(self, file_path: str) -> Optional[str]:
        """提取 Word (.docx) 文件，按段落提取"""
        from docx import Document

        doc = Document(file_path)
        paragraphs = []
        for para in doc.paragraphs:
            if para.text:
                paragraphs.append(para.text)
        return "\n".join(paragraphs)

    def _extract_excel(self, file_path: str) -> Optional[str]:
        """提取 Excel (.xlsx) 文件，按行制表符分隔"""
        from openpyxl import load_workbook

        wb = load_workbook(file_path, read_only=True, data_only=True)
        all_text = []

        for sheet in wb.worksheets:
            for row in sheet.iter_rows():
                cells = []
                for cell in row:
                    value = cell.value
                    if value is not None:
                        cells.append(str(value))
                    else:
                        cells.append("")
                all_text.append("\t".join(cells))

        wb.close()
        return "\n".join(all_text)

    def _extract_pdf(self, file_path: str) -> Optional[str]:
        """提取 PDF 文件，按页顺序拼接"""
        from PyPDF2 import PdfReader

        reader = PdfReader(file_path)
        pages_text = []

        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)

        return "\n".join(pages_text)

    def _extract_csv(self, file_path: str) -> Optional[str]:
        """提取 CSV 文件（UTF-8），按行制表符分隔"""
        rows = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                rows.append("\t".join(row))
        return "\n".join(rows)
