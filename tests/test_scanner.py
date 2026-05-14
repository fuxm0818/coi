"""FileScanner 单元测试"""

import os
import time

import pytest

from src.scanner import FileScanner, SUPPORTED_EXTENSIONS


@pytest.fixture
def scanner():
    return FileScanner()


@pytest.fixture
def knowledge_folder(tmp_dir):
    """创建包含多种文件的知识库文件夹"""
    # 创建支持格式的文件
    for ext in [".txt", ".md", ".pdf", ".docx", ".xlsx"]:
        filepath = os.path.join(tmp_dir, f"test{ext}")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"content for {ext}")

    # 创建子目录中的文件
    subdir = os.path.join(tmp_dir, "subdir")
    os.makedirs(subdir)
    with open(os.path.join(subdir, "nested.txt"), "w", encoding="utf-8") as f:
        f.write("nested content")

    # 创建不支持格式的文件
    with open(os.path.join(tmp_dir, "image.png"), "w") as f:
        f.write("fake image")
    with open(os.path.join(tmp_dir, "script.py"), "w") as f:
        f.write("print('hello')")

    return tmp_dir


class TestFileScannerNewFiles:
    """测试新增文件检测"""

    def test_all_files_added_when_no_existing_records(self, scanner, knowledge_folder):
        result = scanner.scan(knowledge_folder, {})
        added = [c for c in result.changes if c.status == "added"]
        # 应该有 6 个支持格式的文件（5 个根目录 + 1 个子目录）
        assert len(added) == 6
        assert result.unchanged == 0

    def test_added_file_has_correct_attributes(self, scanner, knowledge_folder):
        result = scanner.scan(knowledge_folder, {})
        added = [c for c in result.changes if c.status == "added"]
        for change in added:
            assert change.file_path  # 相对路径非空
            assert change.absolute_path  # 绝对路径非空
            assert change.status == "added"
            assert change.last_modified is not None
            assert change.last_modified > 0


class TestFileScannerModifiedFiles:
    """测试修改文件检测"""

    def test_modified_when_timestamp_differs(self, scanner, knowledge_folder):
        # 先获取当前文件的时间戳
        txt_path = os.path.join(knowledge_folder, "test.txt")
        current_mtime = int(os.path.getmtime(txt_path) * 1000)

        # 使用不同的时间戳作为已有记录
        existing = {"test.txt": current_mtime - 1000}
        result = scanner.scan(knowledge_folder, existing)

        modified = [c for c in result.changes if c.status == "modified"]
        assert any(c.file_path == "test.txt" for c in modified)

    def test_unchanged_when_timestamp_matches(self, scanner, knowledge_folder):
        txt_path = os.path.join(knowledge_folder, "test.txt")
        current_mtime = int(os.path.getmtime(txt_path) * 1000)

        existing = {"test.txt": current_mtime}
        result = scanner.scan(knowledge_folder, existing)

        # test.txt 应该是未变更的
        assert result.unchanged >= 1
        modified = [c for c in result.changes if c.status == "modified" and c.file_path == "test.txt"]
        assert len(modified) == 0


class TestFileScannerDeletedFiles:
    """测试删除文件检测"""

    def test_deleted_when_record_exists_but_file_missing(self, scanner, knowledge_folder):
        existing = {"deleted_file.txt": 1000000}
        result = scanner.scan(knowledge_folder, existing)

        deleted = [c for c in result.changes if c.status == "deleted"]
        assert len(deleted) == 1
        assert deleted[0].file_path == "deleted_file.txt"
        assert deleted[0].last_modified is None

    def test_multiple_deleted_files(self, scanner, knowledge_folder):
        existing = {
            "gone1.md": 1000,
            "gone2.pdf": 2000,
            "subdir/gone3.txt": 3000,
        }
        result = scanner.scan(knowledge_folder, existing)

        deleted = [c for c in result.changes if c.status == "deleted"]
        assert len(deleted) == 3


class TestFileScannerExtensionFilter:
    """测试文件扩展名过滤"""

    def test_unsupported_extensions_skipped(self, scanner, knowledge_folder):
        result = scanner.scan(knowledge_folder, {})
        all_paths = [c.file_path for c in result.changes]
        # 不应包含 .png 和 .py 文件
        assert not any(p.endswith(".png") for p in all_paths)
        assert not any(p.endswith(".py") for p in all_paths)

    def test_all_supported_extensions_included(self, scanner, tmp_dir):
        for ext in SUPPORTED_EXTENSIONS:
            filepath = os.path.join(tmp_dir, f"file{ext}")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("content")

        result = scanner.scan(tmp_dir, {})
        added = [c for c in result.changes if c.status == "added"]
        assert len(added) == len(SUPPORTED_EXTENSIONS)


class TestFileScannerErrorHandling:
    """测试错误处理"""

    def test_nonexistent_path_raises_error(self, scanner):
        with pytest.raises(FileNotFoundError, match="知识库路径不存在"):
            scanner.scan("/nonexistent/path/xyz", {})

    def test_file_path_raises_error(self, scanner, tmp_dir):
        file_path = os.path.join(tmp_dir, "a_file.txt")
        with open(file_path, "w") as f:
            f.write("content")

        with pytest.raises(NotADirectoryError, match="知识库路径不是目录"):
            scanner.scan(file_path, {})

    def test_empty_folder_returns_empty_result(self, scanner, tmp_dir):
        result = scanner.scan(tmp_dir, {})
        assert len(result.changes) == 0
        assert result.unchanged == 0


class TestFileScannerRecursive:
    """测试递归遍历"""

    def test_scans_nested_directories(self, scanner, knowledge_folder):
        result = scanner.scan(knowledge_folder, {})
        added = [c for c in result.changes if c.status == "added"]
        nested = [c for c in added if "subdir" in c.file_path]
        assert len(nested) == 1
        assert nested[0].file_path == os.path.join("subdir", "nested.txt")

    def test_deeply_nested_files(self, scanner, tmp_dir):
        deep_dir = os.path.join(tmp_dir, "a", "b", "c")
        os.makedirs(deep_dir)
        with open(os.path.join(deep_dir, "deep.md"), "w", encoding="utf-8") as f:
            f.write("deep content")

        result = scanner.scan(tmp_dir, {})
        added = [c for c in result.changes if c.status == "added"]
        assert len(added) == 1
        assert added[0].file_path == os.path.join("a", "b", "c", "deep.md")
