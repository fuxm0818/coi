"""scanner.py 单元测试"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scanner import FileScanner, SUPPORTED_EXTENSIONS


class TestFileScanner:
    """文件扫描器测试"""

    def test_scan_finds_supported_files(self, sample_docs_dir):
        """扫描发现所有支持格式的文件"""
        scanner = FileScanner()
        result = scanner.scan(sample_docs_dir)

        found_paths = {c.file_path for c in result.changes}
        assert "hello.txt" in found_paths
        assert "readme.md" in found_paths
        assert "data.csv" in found_paths
        assert os.path.join("subdir", "nested.txt") in found_paths

    def test_scan_excludes_hidden_files(self, sample_docs_dir):
        """排除隐藏文件"""
        scanner = FileScanner()
        result = scanner.scan(sample_docs_dir)

        found_paths = {c.file_path for c in result.changes}
        assert ".hidden.txt" not in found_paths

    def test_scan_excludes_hidden_directories(self, sample_docs_dir):
        """排除隐藏目录中的文件"""
        scanner = FileScanner()
        result = scanner.scan(sample_docs_dir)

        found_paths = {c.file_path for c in result.changes}
        for path in found_paths:
            assert ".hidden_dir" not in path

    def test_scan_excludes_unsupported_formats(self, sample_docs_dir):
        """排除不支持的文件格式"""
        scanner = FileScanner()
        result = scanner.scan(sample_docs_dir)

        found_paths = {c.file_path for c in result.changes}
        assert "image.png" not in found_paths

    def test_scan_case_insensitive_extension(self, tmp_dir):
        """扩展名匹配不区分大小写"""
        with open(os.path.join(tmp_dir, "DOC.TXT"), "w") as f:
            f.write("test")
        with open(os.path.join(tmp_dir, "file.Md"), "w") as f:
            f.write("test")

        scanner = FileScanner()
        result = scanner.scan(tmp_dir)

        found_paths = {c.file_path for c in result.changes}
        assert "DOC.TXT" in found_paths
        assert "file.Md" in found_paths

    def test_scan_empty_directory(self, empty_docs_dir):
        """空目录（无支持格式文件）返回空列表"""
        scanner = FileScanner()
        result = scanner.scan(empty_docs_dir)

        assert len(result.changes) == 0
        assert len(result.errors) == 0

    def test_scan_nonexistent_path_raises(self):
        """不存在的路径抛出 FileNotFoundError"""
        scanner = FileScanner()
        with pytest.raises(FileNotFoundError):
            scanner.scan("/nonexistent/path/xyz")

    def test_scan_file_path_raises(self, tmp_dir):
        """传入文件路径（非目录）抛出 NotADirectoryError"""
        file_path = os.path.join(tmp_dir, "file.txt")
        with open(file_path, "w") as f:
            f.write("test")

        scanner = FileScanner()
        with pytest.raises(NotADirectoryError):
            scanner.scan(file_path)

    def test_scan_result_has_absolute_path(self, sample_docs_dir):
        """扫描结果包含绝对路径"""
        scanner = FileScanner()
        result = scanner.scan(sample_docs_dir)

        for change in result.changes:
            assert os.path.isabs(change.absolute_path)
            assert os.path.exists(change.absolute_path)

    def test_scan_result_has_last_modified(self, sample_docs_dir):
        """扫描结果包含修改时间戳（毫秒）"""
        scanner = FileScanner()
        result = scanner.scan(sample_docs_dir)

        for change in result.changes:
            assert change.last_modified is not None
            assert change.last_modified > 0

    def test_scan_recursive_subdirectories(self, tmp_dir):
        """递归扫描多层子目录"""
        deep_dir = os.path.join(tmp_dir, "a", "b", "c")
        os.makedirs(deep_dir)
        with open(os.path.join(deep_dir, "deep.txt"), "w") as f:
            f.write("deep content")

        scanner = FileScanner()
        result = scanner.scan(tmp_dir)

        found_paths = {c.file_path for c in result.changes}
        assert os.path.join("a", "b", "c", "deep.txt") in found_paths
