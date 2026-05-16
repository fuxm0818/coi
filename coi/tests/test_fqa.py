"""fqa.py 单元测试"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fqa import FQAManager


class TestFQALoad:
    """FQA 加载测试"""

    def test_load_nonexistent_returns_empty(self, tmp_dir):
        """文件不存在时返回空列表"""
        mgr = FQAManager(os.path.join(tmp_dir, "fqa.json"))
        pairs = mgr.load()
        assert pairs == []

    def test_load_valid_json(self, tmp_dir):
        """正确加载 JSON 数组"""
        path = os.path.join(tmp_dir, "fqa.json")
        data = [
            {"question": "Q1", "answer": "A1"},
            {"question": "Q2", "answer": "A2"},
        ]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        mgr = FQAManager(path)
        pairs = mgr.load()
        assert len(pairs) == 2
        assert pairs[0].question == "Q1"
        assert pairs[0].answer == "A1"
        assert pairs[1].question == "Q2"
        assert pairs[1].answer == "A2"

    def test_load_corrupted_json_returns_empty(self, tmp_dir):
        """JSON 损坏时返回空列表不抛异常"""
        path = os.path.join(tmp_dir, "fqa.json")
        with open(path, "w") as f:
            f.write("[{invalid")

        mgr = FQAManager(path)
        pairs = mgr.load()
        assert pairs == []

    def test_load_skips_invalid_entries(self, tmp_dir):
        """跳过缺少字段的条目"""
        path = os.path.join(tmp_dir, "fqa.json")
        data = [
            {"question": "Q1", "answer": "A1"},
            {"question": "Q2"},  # 缺少 answer
            {"answer": "A3"},  # 缺少 question
            {"question": "Q4", "answer": "A4"},
        ]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        mgr = FQAManager(path)
        pairs = mgr.load()
        assert len(pairs) == 2
        assert pairs[0].question == "Q1"
        assert pairs[1].question == "Q4"


class TestFQAAppend:
    """FQA 追加测试"""

    def test_append_creates_file(self, tmp_dir):
        """文件不存在时自动创建"""
        path = os.path.join(tmp_dir, "fqa.json")
        mgr = FQAManager(path)

        mgr.append("问题1", "答案1")

        assert os.path.exists(path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0] == {"question": "问题1", "answer": "答案1"}

    def test_append_preserves_existing(self, tmp_dir):
        """追加不覆盖已有记录"""
        path = os.path.join(tmp_dir, "fqa.json")
        mgr = FQAManager(path)

        mgr.append("Q1", "A1")
        mgr.append("Q2", "A2")
        mgr.append("Q3", "A3")

        pairs = mgr.load()
        assert len(pairs) == 3
        assert pairs[0].question == "Q1"
        assert pairs[1].question == "Q2"
        assert pairs[2].question == "Q3"

    def test_append_creates_parent_directory(self, tmp_dir):
        """自动创建父目录"""
        path = os.path.join(tmp_dir, "sub", "dir", "fqa.json")
        mgr = FQAManager(path)

        mgr.append("Q", "A")
        assert os.path.exists(path)

    def test_append_order_preserved(self, tmp_dir):
        """插入顺序保持"""
        path = os.path.join(tmp_dir, "fqa.json")
        mgr = FQAManager(path)

        for i in range(10):
            mgr.append(f"Q{i}", f"A{i}")

        pairs = mgr.load()
        assert len(pairs) == 10
        for i, pair in enumerate(pairs):
            assert pair.question == f"Q{i}"
            assert pair.answer == f"A{i}"
