"""chunker.py 单元测试 - 文本提取与切块"""

import csv
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chunker import TextChunker


class TestTextExtraction:
    """文本提取测试"""

    def test_extract_txt(self, tmp_dir):
        """TXT 文件提取"""
        content = "这是测试内容。\n第二行。"
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        chunker = TextChunker()
        result = chunker.extract_text(path)
        assert result == content

    def test_extract_txt_empty_returns_none(self, tmp_dir):
        """空 TXT 文件返回 None"""
        path = os.path.join(tmp_dir, "empty.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("")

        chunker = TextChunker()
        result = chunker.extract_text(path)
        assert result is None

    def test_extract_txt_whitespace_only_returns_none(self, tmp_dir):
        """纯空白 TXT 文件返回 None"""
        path = os.path.join(tmp_dir, "blank.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("   \n\t\n  ")

        chunker = TextChunker()
        result = chunker.extract_text(path)
        assert result is None

    def test_extract_markdown(self, tmp_dir):
        """Markdown 文件提取纯文本"""
        content = "# 标题\n\n正文内容。\n\n## 二级标题\n\n- 列表项"
        path = os.path.join(tmp_dir, "doc.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        chunker = TextChunker()
        result = chunker.extract_text(path)
        assert result is not None
        assert "标题" in result
        assert "正文内容" in result

    def test_extract_csv(self, tmp_dir):
        """CSV 文件提取为制表符分隔文本"""
        path = os.path.join(tmp_dir, "data.csv")
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["姓名", "年龄", "城市"])
            writer.writerow(["张三", "25", "北京"])
            writer.writerow(["李四", "30", "上海"])

        chunker = TextChunker()
        result = chunker.extract_text(path)
        assert result is not None
        lines = result.strip().split("\n")
        assert len(lines) == 3
        assert "姓名\t年龄\t城市" in lines[0]
        assert "张三\t25\t北京" in lines[1]

    def test_extract_unsupported_format_returns_none(self, tmp_dir):
        """不支持的格式返回 None"""
        path = os.path.join(tmp_dir, "image.png")
        with open(path, "wb") as f:
            f.write(b"\x89PNG")

        chunker = TextChunker()
        result = chunker.extract_text(path)
        assert result is None

    def test_extract_corrupted_file_returns_none(self, tmp_dir):
        """损坏文件返回 None 不抛异常"""
        path = os.path.join(tmp_dir, "bad.pdf")
        with open(path, "wb") as f:
            f.write(b"not a real pdf content")

        chunker = TextChunker()
        result = chunker.extract_text(path)
        assert result is None


class TestChunking:
    """文本切块测试（需要 tokenizer）"""

    @pytest.fixture
    def chunker_with_tokenizer(self):
        """创建带 tokenizer 的 chunker（使用简单的字符级 mock）"""
        class MockTokenizer:
            def encode(self, text, add_special_tokens=False):
                # 简单按字符 tokenize
                return list(range(len(text)))

            def decode(self, token_ids, skip_special_tokens=True):
                # 无法真正 decode，返回占位
                return "x" * len(token_ids)

        return TextChunker(tokenizer=MockTokenizer(), chunk_size=10, chunk_overlap=2)

    def test_chunk_short_text_single_chunk(self, chunker_with_tokenizer):
        """短文本（不超过 chunk_size）返回单个 chunk"""
        chunks = chunker_with_tokenizer.chunk("12345")
        assert len(chunks) == 1
        assert chunks[0].index == 0
        assert chunks[0].token_count == 5

    def test_chunk_empty_text_returns_empty(self, chunker_with_tokenizer):
        """空文本返回空列表"""
        chunks = chunker_with_tokenizer.chunk("")
        assert chunks == []

    def test_chunk_whitespace_only_returns_empty(self, chunker_with_tokenizer):
        """纯空白文本返回空列表"""
        chunks = chunker_with_tokenizer.chunk("   \n\t  ")
        assert chunks == []

    def test_chunk_long_text_multiple_chunks(self, chunker_with_tokenizer):
        """长文本切分为多个 chunk"""
        # 30 字符，chunk_size=10, overlap=2 → 应产生多个 chunk
        text = "a" * 30
        chunks = chunker_with_tokenizer.chunk(text)
        assert len(chunks) > 1

    def test_chunk_token_count_within_limit(self, chunker_with_tokenizer):
        """每个 chunk 的 token_count 不超过 chunk_size"""
        text = "a" * 100
        chunks = chunker_with_tokenizer.chunk(text)
        for chunk in chunks:
            # 允许尾部合并时略超（合并逻辑）
            assert chunk.token_count <= chunker_with_tokenizer.chunk_size + chunker_with_tokenizer.chunk_overlap

    def test_chunk_indices_sequential(self, chunker_with_tokenizer):
        """chunk 索引从 0 开始递增"""
        text = "a" * 50
        chunks = chunker_with_tokenizer.chunk(text)
        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    def test_chunk_no_tokenizer_raises(self):
        """未设置 tokenizer 时抛出 ValueError"""
        chunker = TextChunker(tokenizer=None)
        with pytest.raises(ValueError):
            chunker.chunk("some text")
