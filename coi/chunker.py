"""文本提取与切块

从多种格式文档中提取纯文本，并按 token 切分为适合向量化的块。
支持格式：TXT、MD、PDF、DOCX、XLSX、CSV

动态 chunk size 策略：
- 根据文件类型自动选择合适的 chunk size
- PDF 文件使用较小的 chunk（384 token），因为提取质量可能不稳定
- 表格类文件（XLSX/CSV）使用更小的 chunk（256 token）
- 文本类文件（TXT/MD/DOCX）使用标准 chunk（512 token）
"""

import csv
import logging
import os
import re
from typing import List, Optional

from models import Chunk

logger = logging.getLogger(__name__)


class TextChunker:
    """文本提取与切块器

    负责从多种格式的文档中提取纯文本，并将文本切分为适合向量化的块。
    
    动态切块策略：
    - 根据文件类型自动选择 chunk size
    - 按中文句子边界优先切分
    - 相邻块保留重叠区域
    """

    SUPPORTED_EXTENSIONS = {
        ".txt": "_extract_txt",
        ".md": "_extract_markdown",
        ".docx": "_extract_word",
        ".xlsx": "_extract_excel",
        ".pdf": "_extract_pdf",
        ".csv": "_extract_csv",
        ".pptx": "_extract_ppt",
        ".ppt": "_extract_ppt",
    }

    # 按文件类型的默认 chunk size 配置
    _CHUNK_SIZE_BY_TYPE = {
        ".txt": 512,
        ".md": 512,
        ".docx": 512,
        ".xlsx": 256,
        ".pdf": 384,
        ".csv": 256,
        ".pptx": 512,
        ".ppt": 512,
    }

    # 按文件类型的默认 overlap 配置
    _OVERLAP_BY_TYPE = {
        ".txt": 64,
        ".md": 64,
        ".docx": 64,
        ".xlsx": 32,
        ".pdf": 48,
        ".csv": 32,
        ".pptx": 64,
        ".ppt": 64,
    }

    # 中文句子结束标点
    _SENTENCE_BOUNDARIES = set("。！？；\n")

    def __init__(self, tokenizer=None, chunk_size: int = None, chunk_overlap: int = None):
        """初始化 TextChunker

        Args:
            tokenizer: tokenizer 实例（用于 token 计数和切块）
            chunk_size: 目标块大小（token），为 None 时按文件类型自动选择
            chunk_overlap: 重叠区域大小（token），为 None 时按文件类型自动选择
        """
        self.tokenizer = tokenizer
        self.default_chunk_size = chunk_size
        self.default_chunk_overlap = chunk_overlap

    def _get_chunk_params(self, file_path: str) -> tuple:
        """根据文件类型获取合适的 chunk 参数

        Args:
            file_path: 文件路径

        Returns:
            (chunk_size, chunk_overlap) 元组
        """
        if self.default_chunk_size is not None and self.default_chunk_overlap is not None:
            return (self.default_chunk_size, self.default_chunk_overlap)

        ext = os.path.splitext(file_path)[1].lower()
        chunk_size = self._CHUNK_SIZE_BY_TYPE.get(ext, 512)
        chunk_overlap = self._OVERLAP_BY_TYPE.get(ext, 64)
        return (chunk_size, chunk_overlap)

    def extract_text(self, file_path: str) -> Optional[str]:
        """从文件提取纯文本

        根据文件扩展名分发到对应的提取器。
        提取失败或内容为空时返回 None。
        所有提取的文本都会经过中文空格清理。

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

        if text is None or text.strip() == "":
            logger.warning("文件内容为空: %s", file_path)
            return None

        text = self._normalize_chinese_spacing(text)
        
        return text

    def chunk(self, text: str, file_path: str = None) -> List[Chunk]:
        """将文本切分为多个 Chunk

        使用 tokenizer 进行 token 计数，按动态计算的 chunk_size 切分，
        相邻块保留重叠区域。以中文标点为优先分割边界。

        Args:
            text: 原始文本
            file_path: 文件路径（用于确定 chunk size）

        Returns:
            切块列表
        """
        if not self.tokenizer:
            raise ValueError("tokenizer 未设置，无法进行切块")

        if not text or not text.strip():
            return []

        chunk_size, chunk_overlap = self._get_chunk_params(file_path or "")

        token_ids = self.tokenizer.encode(text, add_special_tokens=False)
        total_tokens = len(token_ids)

        if total_tokens == 0:
            return []

        if total_tokens <= chunk_size:
            return [Chunk(text=text.strip(), index=0, token_count=total_tokens)]

        chunks: List[Chunk] = []
        start = 0
        chunk_index = 0

        while start < total_tokens:
            end = min(start + chunk_size, total_tokens)

            if end < total_tokens:
                boundary = self._find_sentence_boundary(token_ids, start, end, chunk_overlap)
                if boundary > start:
                    end = boundary

            chunk_token_ids = token_ids[start:end]
            chunk_text = self.tokenizer.decode(chunk_token_ids, skip_special_tokens=True)
            chunk_token_count = len(chunk_token_ids)

            remaining = total_tokens - end
            if remaining > 0 and remaining < chunk_overlap:
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

            start = end - chunk_overlap
            chunk_index += 1

        if len(chunks) > 1 and chunks[-1].token_count < chunk_overlap:
            chunks.pop()
            merged_start = self._get_chunk_start(chunks, chunk_overlap)
            merged_token_ids = token_ids[merged_start:]
            merged_text = self.tokenizer.decode(merged_token_ids, skip_special_tokens=True)
            chunks[-1] = Chunk(
                text=merged_text.strip(),
                index=chunks[-1].index,
                token_count=len(merged_token_ids),
            )

        return chunks

    def _get_chunk_start(self, chunks: List[Chunk], chunk_overlap: int) -> int:
        """计算最后一个 chunk 的起始 token 位置"""
        if len(chunks) <= 1:
            return 0
        start = 0
        for chunk in chunks[:-1]:
            end = start + chunk.token_count
            start = end - chunk_overlap
        return start

    def _find_sentence_boundary(self, token_ids: list, start: int, max_end: int, chunk_overlap: int) -> int:
        """在 token 序列中找到最近的中文句子边界

        从 max_end 向前搜索，找到最近的句子结束标点位置。
        """
        search_start = max(start + chunk_overlap, start)

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
        """提取 PDF 文件，按页顺序拼接

        PyPDF2 提取的中文文本存在字符间加空格的问题，
        使用正则清理中文汉字和中文字符之间的多余空格。
        """
        from PyPDF2 import PdfReader

        reader = PdfReader(file_path)
        pages_text = []

        for page in reader.pages:
            text = page.extract_text()
            if text:
                text = self._normalize_chinese_spacing(text)
                pages_text.append(text)

        return "\n".join(pages_text)

    def _normalize_chinese_spacing(self, text: str) -> str:
        """清理中文文本中的多余空格

        PyPDF2 等库提取 PDF 时，会在中文汉字之间插入空格，
        如"产 品 解 说"应还原为"产品解说"。
        同时保留英文单词间的正常空格、换行符和制表符。

        处理的空白字符：普通空格(0x20)、非断行空格(0xA0)、全角空格(0x3000)
        """
        chinese_char = r'[\u4e00-\u9fff]'
        chinese_punctuation = r'[\u3002\uff0c\uff01\uff1f\uff1b\uff1a\u201c\u201d\u2018\u2019\u300a\u300b\u3008\u3009\u3010\u3011\u3001\u00b7]'

        space_chars = r' \xa0\u3000'

        pattern1 = re.compile(f'({chinese_char})[{space_chars}]+({chinese_char})')
        pattern2 = re.compile(f'({chinese_char})[{space_chars}]+({chinese_punctuation})')
        pattern3 = re.compile(f'({chinese_punctuation})[{space_chars}]+({chinese_char})')

        prev_text = text
        while True:
            text = pattern1.sub(r'\1\2', text)
            text = pattern2.sub(r'\1\2', text)
            text = pattern3.sub(r'\1\2', text)
            if text == prev_text:
                break
            prev_text = text

        return text

    def chunk(self, text: str, file_path: str = None) -> List[Chunk]:
        """将文本切分为多个 Chunk

        使用 tokenizer 进行 token 计数，按动态计算的 chunk_size 切分，
        相邻块保留重叠区域。以中文标点为优先分割边界。

        Args:
            text: 原始文本
            file_path: 文件路径（用于确定 chunk size）

        Returns:
            切块列表
        """
        if not self.tokenizer:
            raise ValueError("tokenizer 未设置，无法进行切块")

        if not text or not text.strip():
            return []

        chunk_size, chunk_overlap = self._get_chunk_params(file_path or "")

        token_ids = self.tokenizer.encode(text, add_special_tokens=False)
        total_tokens = len(token_ids)

        if total_tokens == 0:
            return []

        if total_tokens <= chunk_size:
            return [Chunk(text=text.strip(), index=0, token_count=total_tokens)]

        text_len = len(text)
        avg_token_len = text_len / max(total_tokens, 1)

        chunks: List[Chunk] = []
        start = 0
        chunk_index = 0

        while start < total_tokens:
            end = min(start + chunk_size, total_tokens)

            if end < total_tokens:
                boundary = self._find_sentence_boundary(token_ids, start, end, chunk_overlap)
                if boundary > start:
                    end = boundary

            chunk_token_ids = token_ids[start:end]
            chunk_token_count = len(chunk_token_ids)

            char_start = int(start * avg_token_len)
            char_end = int(end * avg_token_len)
            char_end = min(char_end, text_len)

            if char_end > char_start and char_end <= text_len:
                chunk_text = text[char_start:char_end]
            else:
                chunk_text = self.tokenizer.decode(chunk_token_ids, skip_special_tokens=True)

            remaining = total_tokens - end
            if remaining > 0 and remaining < chunk_overlap:
                chunk_token_ids = token_ids[start:]
                char_start = int(start * avg_token_len)
                char_end = text_len
                chunk_text = text[char_start:char_end] if char_end > char_start else self.tokenizer.decode(chunk_token_ids, skip_special_tokens=True)
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

            start = end - chunk_overlap
            chunk_index += 1

        if len(chunks) > 1 and chunks[-1].token_count < chunk_overlap:
            chunks.pop()
            merged_start = self._get_chunk_start(chunks, chunk_overlap)
            merged_token_ids = token_ids[merged_start:]
            merged_text = self.tokenizer.decode(merged_token_ids, skip_special_tokens=True)
            chunks[-1] = Chunk(
                text=merged_text.strip(),
                index=chunks[-1].index,
                token_count=len(merged_token_ids),
            )

        return chunks

    def _decode_chunk_text(self, original_text: str, token_ids: List[int], offset_mapping, start: int, end: int) -> str:
        """从原始文本中提取 chunk 对应的字符片段

        使用 tokenizer 的 offset_mapping 来确定 token 对应的字符位置，
        直接从原始文本提取，避免 decode 改变空白符。

        Args:
            original_text: 原始文本
            token_ids: 完整的 token IDs 列表
            offset_mapping: tokenizer 的 offset_mapping（可选）
            start: chunk 起始 token 索引
            end: chunk 结束 token 索引

        Returns:
            chunk 对应的原始文本片段
        """
        chunk_token_ids = token_ids[start:end]

        if offset_mapping is not None and start < len(offset_mapping) and end <= len(offset_mapping):
            char_start = offset_mapping[start][0]
            char_end = offset_mapping[end - 1][1]

            if char_start < len(original_text) and char_end <= len(original_text) and char_start < char_end:
                return original_text[char_start:char_end]

        decoded = self.tokenizer.decode(chunk_token_ids, skip_special_tokens=True)
        return decoded

    def _extract_csv(self, file_path: str) -> Optional[str]:
        """提取 CSV 文件（UTF-8），按行制表符分隔"""
        rows = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                rows.append("\t".join(row))
        return "\n".join(rows)

    def _extract_ppt(self, file_path: str) -> Optional[str]:
        """提取 PowerPoint (.pptx) 文件，按幻灯片顺序拼接文本

        对于 .ppt 文件，由于格式较旧，使用 python-pptx 时可能需要提醒用户另存为 .pptx。
        """
        from pptx import Presentation
        from pptx.exc import PackageNotFoundError

        try:
            prs = Presentation(file_path)
            slides_text = []

            for i, slide in enumerate(prs.slides, 1):
                slide_content = []
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        slide_content.append(shape.text.strip())
                
                if slide_content:
                    slides_text.append(f"[幻灯片 {i}]")
                    slides_text.extend(slide_content)

            return "\n\n".join(slides_text)

        except PackageNotFoundError:
            logger.warning(f"文件格式可能不是有效的 .pptx，仅支持现代 PowerPoint 格式: {file_path}")
            return None
        except Exception as e:
            logger.error(f"PowerPoint 提取失败 [{file_path}]: {e}")
            return None