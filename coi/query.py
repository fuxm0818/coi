"""双源查询引擎

实现双源合并查询策略：
- 向量库检索文档原文相关片段
- FQA 标准答案语义匹配
两类信息叠加整合，统一输出完整结果。
"""

import logging

from embedding import EmbeddingEngine
from fqa import FQAManager
from models import QueryResult
from store import VectorStore

logger = logging.getLogger(__name__)


class QueryEngine:
    """双源查询引擎

    查询流程：
    1. 将问题向量化
    2. 向量库检索 top-k 相似文档片段
    3. FQA 语义匹配标准答案
    4. 合并两类结果统一返回
    """

    def __init__(
        self,
        embedding_engine: EmbeddingEngine,
        vector_store: VectorStore,
        fqa_manager: FQAManager,
        fqa_threshold: float = 0.85,
    ):
        """初始化 QueryEngine

        Args:
            embedding_engine: 嵌入引擎实例
            vector_store: 向量存储实例
            fqa_manager: FQA 管理器实例
            fqa_threshold: FQA 匹配阈值（严格大于此值才包含）
        """
        self.embedding_engine = embedding_engine
        self.vector_store = vector_store
        self.fqa_manager = fqa_manager
        self.fqa_threshold = fqa_threshold

    def query(self, question: str, top_k: int = 15) -> QueryResult:
        """执行双源合并查询

        最终回答 = 向量库检索到的文档原文相关片段 + 用户自定义 FQA 标准答案
        两类信息叠加整合，统一输出。

        Args:
            question: 用户查询问题
            top_k: 向量检索返回的最大结果数量

        Returns:
            QueryResult 对象（包含 FQA 答案和向量检索结果）

        Raises:
            ValueError: 问题为空时
        """
        if not question or not question.strip():
            raise ValueError("查询问题不能为空")

        # 将问题向量化
        query_vector = self.embedding_engine.embed(question)

        result = QueryResult()

        # 1. FQA 语义匹配
        fqa_result = self.fqa_manager.semantic_match(
            query_vector, self.embedding_engine, self.fqa_threshold
        )
        if fqa_result is not None:
            fqa_pair, similarity = fqa_result
            # 仅当相似度严格大于阈值时包含 FQA 答案
            if similarity > self.fqa_threshold:
                result.fqa_answer = fqa_pair.answer
                result.fqa_similarity = similarity
                logger.info(
                    "FQA 命中: question='%s', similarity=%.4f",
                    fqa_pair.question,
                    similarity,
                )

        # 2. 向量库检索
        search_results = self.vector_store.search(query_vector, top_k)
        if search_results:
            result.vector_chunks = search_results
            # cosine distance = 1 - cosine_similarity
            result.vector_best_similarity = 1.0 - search_results[0].distance

        return result
