"""SyncManager 单元测试"""

import hashlib
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from src.models import Chunk, ChunkMetadata, FileChange, ScanResult
from src.sync import SyncManager


@pytest.fixture
def mock_file_scanner():
    return MagicMock()


@pytest.fixture
def mock_text_chunker():
    return MagicMock()


@pytest.fixture
def mock_embedding_engine():
    return MagicMock()


@pytest.fixture
def mock_vector_store():
    store = MagicMock()
    store.get_existing_files.return_value = {}
    store._collection = MagicMock()
    return store


@pytest.fixture
def sync_manager(mock_file_scanner, mock_text_chunker, mock_embedding_engine, mock_vector_store):
    return SyncManager(
        file_scanner=mock_file_scanner,
        text_chunker=mock_text_chunker,
        embedding_engine=mock_embedding_engine,
        vector_store=mock_vector_store,
    )


class TestIncrementalSync:
    """增量同步测试"""

    def test_empty_folder_no_changes(self, sync_manager, mock_file_scanner, mock_vector_store):
        """空文件夹无变更"""
        mock_vector_store.get_existing_files.return_value = {}
        mock_file_scanner.scan.return_value = ScanResult(changes=[], unchanged=0, errors=[])

        result = sync_manager.incremental_sync("/some/folder")

        assert result["added"] == 0
        assert result["modified"] == 0
        assert result["deleted"] == 0
        assert result["unchanged"] == 0
        assert result["failed"] == 0
        assert result["total_chunks"] == 0
        assert result["errors"] == []

    def test_added_file_success(self, sync_manager, mock_file_scanner, mock_vector_store,
                                 mock_text_chunker, mock_embedding_engine, tmp_dir):
        """新增文件成功处理"""
        # 创建测试文件
        test_file = os.path.join(tmp_dir, "test.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("hello world")

        change = FileChange(
            file_path="test.txt",
            absolute_path=test_file,
            status="added",
            last_modified=1000,
        )
        mock_vector_store.get_existing_files.return_value = {}
        mock_file_scanner.scan.return_value = ScanResult(changes=[change], unchanged=0, errors=[])
        mock_text_chunker.extract_text.return_value = "hello world"
        mock_text_chunker.chunk.return_value = [
            Chunk(text="hello world", index=0, token_count=3),
        ]
        mock_embedding_engine.embed.return_value = [0.1] * 384

        result = sync_manager.incremental_sync(tmp_dir)

        assert result["added"] == 1
        assert result["total_chunks"] == 1
        assert result["failed"] == 0
        mock_vector_store.upsert.assert_called_once()

    def test_added_file_empty_content(self, sync_manager, mock_file_scanner, mock_vector_store,
                                       mock_text_chunker, tmp_dir):
        """新增文件内容为空"""
        test_file = os.path.join(tmp_dir, "empty.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("")

        change = FileChange(
            file_path="empty.txt",
            absolute_path=test_file,
            status="added",
            last_modified=1000,
        )
        mock_vector_store.get_existing_files.return_value = {}
        mock_file_scanner.scan.return_value = ScanResult(changes=[change], unchanged=0, errors=[])
        mock_text_chunker.extract_text.return_value = None

        result = sync_manager.incremental_sync(tmp_dir)

        assert result["added"] == 0
        assert result["failed"] == 1
        assert len(result["errors"]) == 1

    def test_deleted_file_success(self, sync_manager, mock_file_scanner, mock_vector_store):
        """删除文件成功处理"""
        change = FileChange(
            file_path="deleted.txt",
            absolute_path="/some/path/deleted.txt",
            status="deleted",
            last_modified=None,
        )
        mock_vector_store.get_existing_files.return_value = {"deleted.txt": 1000}
        mock_file_scanner.scan.return_value = ScanResult(changes=[change], unchanged=0, errors=[])

        result = sync_manager.incremental_sync("/some/folder")

        assert result["deleted"] == 1
        mock_vector_store.delete_by_file_path.assert_called_once_with("deleted.txt")

    def test_modified_file_success(self, sync_manager, mock_file_scanner, mock_vector_store,
                                    mock_text_chunker, mock_embedding_engine, tmp_dir):
        """修改文件成功处理"""
        test_file = os.path.join(tmp_dir, "modified.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("updated content")

        change = FileChange(
            file_path="modified.txt",
            absolute_path=test_file,
            status="modified",
            last_modified=2000,
        )
        mock_vector_store.get_existing_files.return_value = {"modified.txt": 1000}
        mock_file_scanner.scan.return_value = ScanResult(changes=[change], unchanged=0, errors=[])
        mock_text_chunker.extract_text.return_value = "updated content"
        mock_text_chunker.chunk.return_value = [
            Chunk(text="updated content", index=0, token_count=3),
        ]
        mock_embedding_engine.embed.return_value = [0.2] * 384

        # 模拟备份
        mock_vector_store._collection.get.return_value = {
            "ids": ["modified.txt::0"],
            "embeddings": [[0.1] * 384],
            "documents": ["old content"],
            "metadatas": [{"file_path": "modified.txt", "file_hash": "abc", "chunk_index": 0, "last_modified": 1000}],
        }

        result = sync_manager.incremental_sync(tmp_dir)

        assert result["modified"] == 1
        assert result["total_chunks"] == 1
        mock_vector_store.delete_by_file_path.assert_called_once_with("modified.txt")
        mock_vector_store.upsert.assert_called_once()

    def test_modified_file_rollback_on_failure(self, sync_manager, mock_file_scanner,
                                                mock_vector_store, mock_text_chunker, tmp_dir):
        """修改文件处理失败时回滚"""
        test_file = os.path.join(tmp_dir, "fail.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("content")

        change = FileChange(
            file_path="fail.txt",
            absolute_path=test_file,
            status="modified",
            last_modified=2000,
        )
        mock_vector_store.get_existing_files.return_value = {"fail.txt": 1000}
        mock_file_scanner.scan.return_value = ScanResult(changes=[change], unchanged=0, errors=[])

        # 模拟备份
        backup_data = {
            "ids": ["fail.txt::0"],
            "embeddings": [[0.1] * 384],
            "documents": ["old content"],
            "metadatas": [{"file_path": "fail.txt", "file_hash": "abc", "chunk_index": 0, "last_modified": 1000}],
        }
        mock_vector_store._collection.get.return_value = backup_data

        # 模拟提取文本时抛出异常
        mock_text_chunker.extract_text.side_effect = Exception("提取失败")

        result = sync_manager.incremental_sync(tmp_dir)

        assert result["modified"] == 0
        assert result["failed"] == 1
        assert len(result["errors"]) == 1
        assert "提取失败" in result["errors"][0]["reason"]

        # 验证回滚被调用
        mock_vector_store._collection.upsert.assert_called_once_with(
            ids=backup_data["ids"],
            embeddings=backup_data["embeddings"],
            documents=backup_data["documents"],
            metadatas=backup_data["metadatas"],
        )

    def test_unchanged_files_counted(self, sync_manager, mock_file_scanner, mock_vector_store):
        """未变更文件正确计数"""
        mock_vector_store.get_existing_files.return_value = {"a.txt": 1000, "b.txt": 2000}
        mock_file_scanner.scan.return_value = ScanResult(changes=[], unchanged=3, errors=[])

        result = sync_manager.incremental_sync("/some/folder")

        assert result["unchanged"] == 3

    def test_scan_errors_recorded(self, sync_manager, mock_file_scanner, mock_vector_store):
        """扫描错误被记录"""
        mock_vector_store.get_existing_files.return_value = {}
        mock_file_scanner.scan.return_value = ScanResult(
            changes=[],
            unchanged=0,
            errors=[{"path": "bad.txt", "reason": "Permission denied"}],
        )

        result = sync_manager.incremental_sync("/some/folder")

        assert result["failed"] == 1
        assert result["errors"][0]["path"] == "bad.txt"
        assert result["errors"][0]["reason"] == "Permission denied"

    def test_multiple_changes_mixed(self, sync_manager, mock_file_scanner, mock_vector_store,
                                     mock_text_chunker, mock_embedding_engine, tmp_dir):
        """混合变更（新增+删除+未变更）"""
        test_file = os.path.join(tmp_dir, "new.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("new content")

        changes = [
            FileChange(file_path="new.txt", absolute_path=test_file, status="added", last_modified=1000),
            FileChange(file_path="old.txt", absolute_path="/path/old.txt", status="deleted", last_modified=None),
        ]
        mock_vector_store.get_existing_files.return_value = {"old.txt": 500}
        mock_file_scanner.scan.return_value = ScanResult(changes=changes, unchanged=2, errors=[])
        mock_text_chunker.extract_text.return_value = "new content"
        mock_text_chunker.chunk.return_value = [
            Chunk(text="new content", index=0, token_count=3),
        ]
        mock_embedding_engine.embed.return_value = [0.1] * 384

        result = sync_manager.incremental_sync(tmp_dir)

        assert result["added"] == 1
        assert result["deleted"] == 1
        assert result["unchanged"] == 2
        assert result["total_chunks"] == 1

    def test_single_file_failure_continues_processing(
        self, sync_manager, mock_file_scanner, mock_vector_store,
        mock_text_chunker, mock_embedding_engine, tmp_dir
    ):
        """单个文件处理失败时继续处理剩余文件"""
        good_file = os.path.join(tmp_dir, "good.txt")
        bad_file = os.path.join(tmp_dir, "bad.txt")
        with open(good_file, "w", encoding="utf-8") as f:
            f.write("good content")
        with open(bad_file, "w", encoding="utf-8") as f:
            f.write("bad content")

        changes = [
            FileChange(file_path="bad.txt", absolute_path=bad_file, status="added", last_modified=1000),
            FileChange(file_path="good.txt", absolute_path=good_file, status="added", last_modified=2000),
        ]
        mock_vector_store.get_existing_files.return_value = {}
        mock_file_scanner.scan.return_value = ScanResult(changes=changes, unchanged=0, errors=[])

        # 第一个文件提取失败，第二个成功
        mock_text_chunker.extract_text.side_effect = [
            Exception("文件损坏"),
            "good content",
        ]
        mock_text_chunker.chunk.return_value = [
            Chunk(text="good content", index=0, token_count=3),
        ]
        mock_embedding_engine.embed.return_value = [0.1] * 384

        result = sync_manager.incremental_sync(tmp_dir)

        assert result["added"] == 1
        assert result["failed"] == 1
        assert result["total_chunks"] == 1


class TestFullRebuild:
    """全量重建测试"""

    def test_full_rebuild_deletes_all_then_indexes(
        self, sync_manager, mock_file_scanner, mock_vector_store,
        mock_text_chunker, mock_embedding_engine, tmp_dir
    ):
        """全量重建先删除所有记录再重新索引"""
        test_file = os.path.join(tmp_dir, "doc.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("document content")

        mock_vector_store.delete_all.return_value = 5
        changes = [
            FileChange(file_path="doc.txt", absolute_path=test_file, status="added", last_modified=1000),
        ]
        mock_file_scanner.scan.return_value = ScanResult(changes=changes, unchanged=0, errors=[])
        mock_text_chunker.extract_text.return_value = "document content"
        mock_text_chunker.chunk.return_value = [
            Chunk(text="document content", index=0, token_count=3),
        ]
        mock_embedding_engine.embed.return_value = [0.1] * 384

        result = sync_manager.full_rebuild(tmp_dir)

        mock_vector_store.delete_all.assert_called_once()
        assert result["added"] == 1
        assert result["total_chunks"] == 1

    def test_full_rebuild_with_empty_folder(
        self, sync_manager, mock_file_scanner, mock_vector_store
    ):
        """全量重建空文件夹"""
        mock_vector_store.delete_all.return_value = 0
        mock_file_scanner.scan.return_value = ScanResult(changes=[], unchanged=0, errors=[])

        result = sync_manager.full_rebuild("/some/folder")

        mock_vector_store.delete_all.assert_called_once()
        assert result["added"] == 0
        assert result["total_chunks"] == 0


class TestFileHash:
    """文件哈希计算测试"""

    def test_compute_file_hash(self, sync_manager, tmp_dir):
        """正确计算文件 SHA-256 哈希"""
        test_file = os.path.join(tmp_dir, "hash_test.txt")
        content = "hello world"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(content)

        expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        actual_hash = sync_manager._compute_file_hash(test_file)

        assert actual_hash == expected_hash


class TestBackupAndRestore:
    """备份与恢复测试"""

    def test_get_file_records_backup(self, sync_manager, mock_vector_store):
        """获取文件记录备份"""
        mock_vector_store._collection.get.return_value = {
            "ids": ["file.txt::0", "file.txt::1"],
            "embeddings": [[0.1] * 384, [0.2] * 384],
            "documents": ["chunk 0", "chunk 1"],
            "metadatas": [
                {"file_path": "file.txt", "file_hash": "abc", "chunk_index": 0, "last_modified": 1000},
                {"file_path": "file.txt", "file_hash": "abc", "chunk_index": 1, "last_modified": 1000},
            ],
        }

        backup = sync_manager._get_file_records_backup("file.txt")

        assert len(backup["ids"]) == 2
        assert backup["ids"] == ["file.txt::0", "file.txt::1"]
        mock_vector_store._collection.get.assert_called_once_with(
            where={"file_path": "file.txt"},
            include=["embeddings", "documents", "metadatas"],
        )

    def test_restore_backup_empty(self, sync_manager, mock_vector_store):
        """恢复空备份不执行操作"""
        backup = {"ids": [], "embeddings": [], "documents": [], "metadatas": []}
        sync_manager._restore_backup(backup)
        mock_vector_store._collection.upsert.assert_not_called()

    def test_restore_backup_with_data(self, sync_manager, mock_vector_store):
        """恢复有数据的备份"""
        backup = {
            "ids": ["file.txt::0"],
            "embeddings": [[0.1] * 384],
            "documents": ["chunk 0"],
            "metadatas": [{"file_path": "file.txt", "file_hash": "abc", "chunk_index": 0, "last_modified": 1000}],
        }
        sync_manager._restore_backup(backup)
        mock_vector_store._collection.upsert.assert_called_once_with(
            ids=["file.txt::0"],
            embeddings=[[0.1] * 384],
            documents=["chunk 0"],
            metadatas=[{"file_path": "file.txt", "file_hash": "abc", "chunk_index": 0, "last_modified": 1000}],
        )
