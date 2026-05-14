"""查询引擎

实现 FQA 优先级查询策略：先语义匹配 FQA 问答对，
相似度超过阈值时直接返回 FQA 答案，否则回退到向量检索。
"""

import logging

from src.embedding import EmbeddingEngine
from src.fqa import FQAManager
from src.models import QueryResult
from src.store import VectorStore

logger = logging.getLogger(__name__)


class QueryEngine:
    """查询引擎，实现 FQA 优先级策略。

    查询流程：
    1. 验证问题有效性（拒绝空字符串或纯空白）
    2. 将问题向量化
    3. 先对 FQA 进行语义匹配
    4. 若最高相似度 > fqa_threshold，直接返回 FQA 答案
    5. 否则回退到 Vector_Store 语义检索

    Attributes:
        FQA_THRESHOLD: 默认 FQA 匹配阈值
    """

    FQA_THRESHOLD = 0.85

    def __init__(
        self,
        embedding_engine: EmbeddingEngine,
        vector_store: VectorStore,
        fqa_manager: FQAManager,
        fqa_threshold: float = 0.85,
    ):
        """初始化 QueryEngine。

        Args:
            embedding_engine: 嵌入引擎实例
            vector_store: 向量存储实例
            fqa_manager: FQA 管理器实例
            fqa_threshold: FQA 匹配阈值，默认 0.85
        """
        self.embedding_engine = embedding_engine
        self.vector_store = vector_store
        self.fqa_manager = fqa_manager
        self.fqa_threshold = fqa_threshold

    def validate_question(self, question: str) -> bool:
        """验证查询问题是否有效。

        拒绝空字符串或仅包含空白字符的查询。

        Args:
            question: 用户输入的查询问题

        Returns:
            True 表示问题有效，False 表示无效
        """
        if not question or not question.strip():
            return False
        return True

    def query(self, question: str, top_k: int = 5) -> QueryResult:
        """执行查询，实现 FQA 优先级策略。

        流程：
        1. 验证问题（拒绝空/空白查询）
        2. 使用 embedding_engine 将问题向量化
        3. 调用 fqa_manager.semantic_match 进行 FQA 语义匹配
        4. 若最高相似度 > fqa_threshold，返回 FQA 答案 (source='fqa')
        5. 否则调用 vector_store.search 进行语义检索 (source='vector_store')

        Args:
            question: 用户查询问题
            top_k: 向量检索返回的最大结果数量，默认 5

        Returns:
            QueryResult 对象

        Raises:
            ValueError: 当问题为空或纯空白时
        """
        # 1. 验证问题
        if not self.validate_question(question):
            raise ValueError("查询问题不能为空或纯空白字符，请输入有效的查询内容")

        # 2. 将问题向量化
        query_vector = self.embedding_engine.embed(question)

        # 3. FQA 语义匹配
        fqa_result = self.fqa_manager.semantic_match(query_vector, self.embedding_engine)

        # 4. 检查 FQA 匹配结果
        if fqa_result is not None:
            fqa_pair, similarity = fqa_result
            if similarity > self.fqa_threshold:
                logger.info(
                    "FQA 命中: question='%s', similarity=%.4f",
                    fqa_pair.question,
                    similarity,
                )
                return QueryResult(
                    source="fqa",
                    answer=fqa_pair.answer,
                    chunks=[],
                    similarity=similarity,
                )

        # 5. 回退到 Vector_Store 语义检索
        search_results = self.vector_store.search(query_vector, top_k)

        if not search_results:
            logger.info("Vector_Store 无结果: question='%s'", question)
            return QueryResult(
                source="vector_store",
                answer="未找到相关内容",
                chunks=[],
                similarity=0.0,
            )

        # 取最高相似度（距离越小越相似，转换为相似度）
        # ChromaDB cosine distance = 1 - cosine_similarity
        best_similarity = 1.0 - search_results[0].distance if search_results else 0.0

        logger.info(
            "Vector_Store 检索: question='%s', results=%d, best_similarity=%.4f",
            question,
            len(search_results),
            best_similarity,
        )

        return QueryResult(
            source="vector_store",
            answer=None,
            chunks=search_results,
            similarity=best_similarity,
        )
