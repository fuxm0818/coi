"""ChromaDB 向量存储

基于 ChromaDB PersistentClient 的本地向量存储，
使用 cosine 距离度量进行语义检索。
"""

from typing import List, Union

import chromadb
import numpy as np

from models import ChunkMetadata, SearchResult


class VectorStore:
    """本地向量存储（ChromaDB）

    使用 cosine 距离度量，支持持久化存储。
    """

    def __init__(self, chroma_path: str, collection_name: str = "coi_knowledge"):
        """初始化 VectorStore

        Args:
            chroma_path: ChromaDB 本地持久化路径
            collection_name: ChromaDB collection 名称
        """
        self.chroma_path = chroma_path
        self.collection_name = collection_name
        self._client = None
        self._collection = None

    def initialize(self) -> None:
        """创建或获取 collection（cosine 距离度量）"""
        self._client = chromadb.PersistentClient(path=self.chroma_path)
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(
        self,
        id: str,
        vector: Union[List[float], "np.ndarray"],
        text: str,
        metadata: ChunkMetadata,
    ) -> None:
        """插入或更新向量记录

        ID 格式: "{file_path}::{chunk_index}"

        Args:
            id: 向量记录唯一标识
            vector: 嵌入向量
            text: 文本内容
            metadata: 元数据对象
        """
        if isinstance(vector, np.ndarray):
            embedding = vector.tolist()
        else:
            embedding = list(vector)

        meta_dict = {
            "file_path": metadata.file_path,
            "file_hash": metadata.file_hash,
            "chunk_index": metadata.chunk_index,
            "last_modified": metadata.last_modified,
        }

        self._collection.upsert(
            ids=[id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[meta_dict],
        )

    def delete_all(self) -> int:
        """删除所有向量记录

        Returns:
            删除的记录数量
        """
        count = self._collection.count()
        if count > 0:
            all_records = self._collection.get()
            self._collection.delete(ids=all_records["ids"])
        return count

    def search(
        self, vector: Union[List[float], "np.ndarray"], top_k: int = 5
    ) -> List[SearchResult]:
        """语义检索

        Args:
            vector: 查询向量
            top_k: 返回结果数量

        Returns:
            检索结果列表，按距离升序排列（越小越相似）
        """
        if isinstance(vector, np.ndarray):
            query_embedding = vector.tolist()
        else:
            query_embedding = list(vector)

        # collection 为空时直接返回
        if self._collection.count() == 0:
            return []

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self._collection.count()),
        )

        search_results = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][i]
                chunk_metadata = ChunkMetadata(
                    file_path=meta["file_path"],
                    file_hash=meta["file_hash"],
                    chunk_index=meta["chunk_index"],
                    last_modified=meta["last_modified"],
                )
                search_results.append(
                    SearchResult(
                        text=results["documents"][0][i],
                        metadata=chunk_metadata,
                        distance=results["distances"][0][i],
                    )
                )

        return search_results

    def get_record_count(self) -> int:
        """获取当前向量记录总数"""
        return self._collection.count()
