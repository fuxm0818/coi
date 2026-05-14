"""增量同步协调

协调 FileScanner、TextChunker、EmbeddingEngine、VectorStore 完成增量同步。
支持新增、修改、删除文件的处理，修改文件更新失败时回滚，
单个文件处理失败时跳过并记录错误，继续处理剩余文件。
"""

import hashlib
import logging
from typing import Dict, List

from src.chunker import TextChunker
from src.embedding import EmbeddingEngine
from src.models import ChunkMetadata, FileChange
from src.scanner import FileScanner
from src.store import VectorStore

logger = logging.getLogger(__name__)


class SyncManager:
    """增量同步管理器

    协调 FileScanner、TextChunker、EmbeddingEngine、VectorStore 完成增量同步。
    """

    def __init__(
        self,
        file_scanner: FileScanner,
        text_chunker: TextChunker,
        embedding_engine: EmbeddingEngine,
        vector_store: VectorStore,
    ):
        """初始化 SyncManager

        Args:
            file_scanner: 文件扫描器实例
            text_chunker: 文本切块器实例
            embedding_engine: 嵌入引擎实例
            vector_store: 向量存储实例
        """
        self.file_scanner = file_scanner
        self.text_chunker = text_chunker
        self.embedding_engine = embedding_engine
        self.vector_store = vector_store

    def incremental_sync(self, folder_path: str) -> dict:
        """执行增量同步

        扫描文件夹变更，对新增/修改/删除文件分别处理。

        Args:
            folder_path: 知识库文件夹路径

        Returns:
            统计摘要字典，包含 keys:
            - added: 新增文件数
            - modified: 修改文件数
            - deleted: 删除文件数
            - unchanged: 未变更文件数
            - failed: 失败文件数
            - total_chunks: 本次处理的总 chunk 数
            - errors: 错误列表，每项为 {path, reason}
        """
        stats = {
            "added": 0,
            "modified": 0,
            "deleted": 0,
            "unchanged": 0,
            "failed": 0,
            "total_chunks": 0,
            "errors": [],
        }

        # 获取向量库中已有文件记录
        existing_records = self.vector_store.get_existing_files()

        # 扫描文件夹变更
        scan_result = self.file_scanner.scan(folder_path, existing_records)
        stats["unchanged"] = scan_result.unchanged

        # 将扫描错误加入统计
        for error in scan_result.errors:
            stats["errors"].append(error)
            stats["failed"] += 1

        # 处理每个变更文件
        for change in scan_result.changes:
            if change.status == "added":
                self._process_added(change, folder_path, stats)
            elif change.status == "modified":
                self._process_modified(change, folder_path, stats)
            elif change.status == "deleted":
                self._process_deleted(change, stats)

        logger.info(
            "增量同步完成: 新增=%d, 修改=%d, 删除=%d, 未变更=%d, 失败=%d, 总块数=%d",
            stats["added"],
            stats["modified"],
            stats["deleted"],
            stats["unchanged"],
            stats["failed"],
            stats["total_chunks"],
        )

        return stats

    def full_rebuild(self, folder_path: str) -> dict:
        """全量重建知识库

        删除所有现有记录，重新扫描并索引所有文件。

        Args:
            folder_path: 知识库文件夹路径

        Returns:
            统计摘要字典，格式同 incremental_sync
        """
        stats = {
            "added": 0,
            "modified": 0,
            "deleted": 0,
            "unchanged": 0,
            "failed": 0,
            "total_chunks": 0,
            "errors": [],
        }

        # 删除所有现有记录
        deleted_count = self.vector_store.delete_all()
        logger.info("全量重建: 已删除 %d 条旧记录", deleted_count)

        # 使用空的 existing_records 进行扫描，所有文件都会被标记为 added
        scan_result = self.file_scanner.scan(folder_path, {})

        # 将扫描错误加入统计
        for error in scan_result.errors:
            stats["errors"].append(error)
            stats["failed"] += 1

        # 处理所有文件（全部为 added 状态）
        for change in scan_result.changes:
            self._process_added(change, folder_path, stats)

        logger.info(
            "全量重建完成: 新增=%d, 失败=%d, 总块数=%d",
            stats["added"],
            stats["failed"],
            stats["total_chunks"],
        )

        return stats

    def _process_added(self, change: FileChange, folder_path: str, stats: dict) -> None:
        """处理新增文件：提取文本 → 切块 → 向量化 → 存储

        Args:
            change: 文件变更记录
            folder_path: 知识库文件夹路径
            stats: 统计字典（会被修改）
        """
        try:
            chunks_stored = self._extract_chunk_embed_store(change)
            if chunks_stored > 0:
                stats["added"] += 1
                stats["total_chunks"] += chunks_stored
            else:
                # 文件内容为空或提取失败，记录为失败
                stats["failed"] += 1
                stats["errors"].append({
                    "path": change.file_path,
                    "reason": "文件内容为空或提取失败",
                })
        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append({
                "path": change.file_path,
                "reason": str(e),
            })
            logger.error("处理新增文件失败 [%s]: %s", change.file_path, str(e))

    def _process_modified(self, change: FileChange, folder_path: str, stats: dict) -> None:
        """处理修改文件：备份旧记录 → 删除旧记录 → 重新处理 → 失败时回滚

        Args:
            change: 文件变更记录
            folder_path: 知识库文件夹路径
            stats: 统计字典（会被修改）
        """
        # Step 1: 备份旧记录
        backup = self._get_file_records_backup(change.file_path)

        # Step 2: 删除旧记录
        try:
            self.vector_store.delete_by_file_path(change.file_path)
        except Exception as e:
            # 删除失败，不需要回滚（旧记录仍在）
            stats["failed"] += 1
            stats["errors"].append({
                "path": change.file_path,
                "reason": f"删除旧记录失败: {str(e)}",
            })
            logger.error("删除旧记录失败 [%s]: %s", change.file_path, str(e))
            return

        # Step 3: 重新提取、切块、向量化、存储
        try:
            chunks_stored = self._extract_chunk_embed_store(change)
            if chunks_stored > 0:
                stats["modified"] += 1
                stats["total_chunks"] += chunks_stored
            else:
                # 新内容为空，回滚
                self._restore_backup(backup)
                stats["failed"] += 1
                stats["errors"].append({
                    "path": change.file_path,
                    "reason": "修改后文件内容为空或提取失败，已回滚",
                })
                logger.warning("修改文件内容为空，已回滚 [%s]", change.file_path)
        except Exception as e:
            # Step 4: 失败时回滚
            logger.error("处理修改文件失败 [%s]: %s，正在回滚", change.file_path, str(e))
            try:
                self._restore_backup(backup)
                logger.info("回滚成功 [%s]", change.file_path)
            except Exception as rollback_error:
                logger.error(
                    "回滚失败 [%s]: %s", change.file_path, str(rollback_error)
                )
            stats["failed"] += 1
            stats["errors"].append({
                "path": change.file_path,
                "reason": f"处理失败已回滚: {str(e)}",
            })

    def _process_deleted(self, change: FileChange, stats: dict) -> None:
        """处理删除文件：删除对应向量记录

        Args:
            change: 文件变更记录
            stats: 统计字典（会被修改）
        """
        try:
            self.vector_store.delete_by_file_path(change.file_path)
            stats["deleted"] += 1
        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append({
                "path": change.file_path,
                "reason": f"删除向量记录失败: {str(e)}",
            })
            logger.error("删除文件向量记录失败 [%s]: %s", change.file_path, str(e))

    def _extract_chunk_embed_store(self, change: FileChange) -> int:
        """提取文本 → 切块 → 向量化 → 存储

        Args:
            change: 文件变更记录

        Returns:
            成功存储的 chunk 数量

        Raises:
            Exception: 处理过程中的任何异常
        """
        # 提取文本
        text = self.text_chunker.extract_text(change.absolute_path)
        if text is None:
            return 0

        # 切块
        chunks = self.text_chunker.chunk(text)
        if not chunks:
            return 0

        # 计算文件哈希
        file_hash = self._compute_file_hash(change.absolute_path)

        # 向量化并存储
        stored_count = 0
        for chunk in chunks:
            try:
                # 向量化
                vector = self.embedding_engine.embed(chunk.text)

                # 构建元数据
                metadata = ChunkMetadata(
                    file_path=change.file_path,
                    file_hash=file_hash,
                    chunk_index=chunk.index,
                    last_modified=change.last_modified,
                )

                # 构建 ID
                record_id = f"{change.file_path}::{chunk.index}"

                # 存储
                self.vector_store.upsert(record_id, vector, chunk.text, metadata)
                stored_count += 1
            except Exception as e:
                logger.error(
                    "Chunk 向量化/存储失败 [%s::chunk_%d]: %s",
                    change.file_path,
                    chunk.index,
                    str(e),
                )
                # 单个 chunk 失败时继续处理剩余 chunk
                continue

        return stored_count

    def _compute_file_hash(self, file_path: str) -> str:
        """计算文件内容的 SHA-256 哈希

        Args:
            file_path: 文件绝对路径

        Returns:
            SHA-256 哈希字符串（十六进制）
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(8192), b""):
                sha256.update(block)
        return sha256.hexdigest()

    def _get_file_records_backup(self, file_path: str) -> dict:
        """获取指定文件的所有向量记录备份

        Args:
            file_path: 源文件相对路径

        Returns:
            备份字典，包含 ids, embeddings, documents, metadatas
        """
        collection = self.vector_store._collection
        try:
            results = collection.get(
                where={"file_path": file_path},
                include=["embeddings", "documents", "metadatas"],
            )
            return {
                "ids": results.get("ids", []),
                "embeddings": results.get("embeddings", []),
                "documents": results.get("documents", []),
                "metadatas": results.get("metadatas", []),
            }
        except Exception as e:
            logger.warning("获取备份记录失败 [%s]: %s", file_path, str(e))
            return {"ids": [], "embeddings": [], "documents": [], "metadatas": []}

    def _restore_backup(self, backup: dict) -> None:
        """恢复备份的向量记录

        Args:
            backup: 备份字典，包含 ids, embeddings, documents, metadatas
        """
        if not backup["ids"]:
            return

        collection = self.vector_store._collection
        collection.upsert(
            ids=backup["ids"],
            embeddings=backup["embeddings"],
            documents=backup["documents"],
            metadatas=backup["metadatas"],
        )
