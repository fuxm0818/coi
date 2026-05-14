"""QueryEngine 单元测试"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.fqa import FQAManager
from src.models import (
    ChunkMetadata,
    FQAPair,
    QueryResult,
    SearchResult,
)
from src.query import QueryEngine


@pytest.fixture
def mock_embedding_engine():
    """创建 mock EmbeddingEngine"""
    engine = MagicMock()
    # embed 返回一个 384 维的随机向量
    engine.embed.return_value = np.random.rand(384).astype(np.float32)
    engine.embed_batch.return_value = np.random.rand(3, 384).astype(np.float32)
    return engine


@pytest.fixture
def mock_vector_store():
    """创建 mock VectorStore"""
    store = MagicMock()
    store.search.return_value = []
    return store


@pytest.fixture
def mock_fqa_manager():
    """创建 mock FQAManager"""
    manager = MagicMock(spec=FQAManager)
    manager.semantic_match.return_value = None
    return manager


@pytest.fixture
def query_engine(mock_embedding_engine, mock_vector_store, mock_fqa_manager):
    """创建 QueryEngine 实例"""
    return QueryEngine(
        embedding_engine=mock_embedding_engine,
        vector_store=mock_vector_store,
        fqa_manager=mock_fqa_manager,
        fqa_threshold=0.85,
    )


class TestValidateQuestion:
    """测试 validate_question 方法"""

    def test_valid_question(self, query_engine):
        """有效问题返回 True"""
        assert query_engine.validate_question("如何退货") is True

    def test_empty_string(self, query_engine):
        """空字符串返回 False"""
        assert query_engine.validate_question("") is False

    def test_whitespace_only(self, query_engine):
        """纯空白字符返回 False"""
        assert query_engine.validate_question("   ") is False
        assert query_engine.validate_question("\t\n") is False

    def test_whitespace_with_content(self, query_engine):
        """包含有效内容的字符串返回 True"""
        assert query_engine.validate_question("  hello  ") is True


class TestQueryFQAPriority:
    """测试 FQA 优先级策略"""

    def test_fqa_hit_above_threshold(
        self, query_engine, mock_fqa_manager, mock_vector_store
    ):
        """FQA 相似度 > 0.85 时直接返回 FQA 答案"""
        fqa_pair = FQAPair(question="如何退货", answer="请联系客服400-xxx-xxxx")
        mock_fqa_manager.semantic_match.return_value = (fqa_pair, 0.92)

        result = query_engine.query("怎么退货")

        assert result.source == "fqa"
        assert result.answer == "请联系客服400-xxx-xxxx"
        assert result.similarity == 0.92
        assert result.chunks == []
        # FQA 命中时不应查询 Vector_Store
        mock_vector_store.search.assert_not_called()

    def test_fqa_at_threshold_falls_through(
        self, query_engine, mock_fqa_manager, mock_vector_store
    ):
        """FQA 相似度 == 0.85 时不命中，回退到向量检索"""
        fqa_pair = FQAPair(question="如何退货", answer="请联系客服")
        mock_fqa_manager.semantic_match.return_value = (fqa_pair, 0.85)
        mock_vector_store.search.return_value = []

        result = query_engine.query("退货流程")

        assert result.source == "vector_store"
        mock_vector_store.search.assert_called_once()

    def test_fqa_below_threshold_falls_through(
        self, query_engine, mock_fqa_manager, mock_vector_store
    ):
        """FQA 相似度 < 0.85 时回退到向量检索"""
        fqa_pair = FQAPair(question="如何退货", answer="请联系客服")
        mock_fqa_manager.semantic_match.return_value = (fqa_pair, 0.70)
        mock_vector_store.search.return_value = []

        result = query_engine.query("天气怎么样")

        assert result.source == "vector_store"
        mock_vector_store.search.assert_called_once()

    def test_fqa_no_match(self, query_engine, mock_fqa_manager, mock_vector_store):
        """FQA 无匹配时回退到向量检索"""
        mock_fqa_manager.semantic_match.return_value = None
        mock_vector_store.search.return_value = []

        result = query_engine.query("随便问个问题")

        assert result.source == "vector_store"
        mock_vector_store.search.assert_called_once()


class TestQueryVectorStore:
    """测试向量检索回退"""

    def test_vector_store_returns_results(
        self, query_engine, mock_fqa_manager, mock_vector_store
    ):
        """向量检索有结果时返回 chunks"""
        mock_fqa_manager.semantic_match.return_value = None

        search_results = [
            SearchResult(
                text="退货政策：7天无理由退货",
                metadata=ChunkMetadata(
                    file_path="docs/policy.md",
                    file_hash="abc123",
                    chunk_index=0,
                    last_modified=1700000000,
                ),
                distance=0.15,
            ),
            SearchResult(
                text="退货流程说明",
                metadata=ChunkMetadata(
                    file_path="docs/faq.md",
                    file_hash="def456",
                    chunk_index=2,
                    last_modified=1700000001,
                ),
                distance=0.25,
            ),
        ]
        mock_vector_store.search.return_value = search_results

        result = query_engine.query("退货政策", top_k=5)

        assert result.source == "vector_store"
        assert result.answer is None
        assert len(result.chunks) == 2
        assert result.chunks[0].text == "退货政策：7天无理由退货"
        # similarity = 1 - distance
        assert result.similarity == pytest.approx(0.85, abs=0.01)

    def test_vector_store_no_results(
        self, query_engine, mock_fqa_manager, mock_vector_store
    ):
        """向量检索无结果时返回提示信息"""
        mock_fqa_manager.semantic_match.return_value = None
        mock_vector_store.search.return_value = []

        result = query_engine.query("完全无关的问题xyz")

        assert result.source == "vector_store"
        assert result.answer == "未找到相关内容"
        assert result.chunks == []
        assert result.similarity == 0.0

    def test_top_k_passed_to_vector_store(
        self, query_engine, mock_fqa_manager, mock_vector_store
    ):
        """top_k 参数正确传递给 vector_store.search"""
        mock_fqa_manager.semantic_match.return_value = None
        mock_vector_store.search.return_value = []

        query_engine.query("测试问题", top_k=3)

        mock_vector_store.search.assert_called_once()
        call_args = mock_vector_store.search.call_args
        assert call_args[0][1] == 3  # top_k 参数


class TestQueryValidation:
    """测试查询验证"""

    def test_empty_query_raises_error(self, query_engine):
        """空查询抛出 ValueError"""
        with pytest.raises(ValueError, match="查询问题不能为空"):
            query_engine.query("")

    def test_whitespace_query_raises_error(self, query_engine):
        """纯空白查询抛出 ValueError"""
        with pytest.raises(ValueError, match="查询问题不能为空"):
            query_engine.query("   ")

    def test_tab_newline_query_raises_error(self, query_engine):
        """制表符和换行符查询抛出 ValueError"""
        with pytest.raises(ValueError, match="查询问题不能为空"):
            query_engine.query("\t\n")


class TestQueryEngineInit:
    """测试 QueryEngine 初始化"""

    def test_default_threshold(self, mock_embedding_engine, mock_vector_store, mock_fqa_manager):
        """默认阈值为 0.85"""
        engine = QueryEngine(
            embedding_engine=mock_embedding_engine,
            vector_store=mock_vector_store,
            fqa_manager=mock_fqa_manager,
        )
        assert engine.fqa_threshold == 0.85

    def test_custom_threshold(self, mock_embedding_engine, mock_vector_store, mock_fqa_manager):
        """自定义阈值"""
        engine = QueryEngine(
            embedding_engine=mock_embedding_engine,
            vector_store=mock_vector_store,
            fqa_manager=mock_fqa_manager,
            fqa_threshold=0.90,
        )
        assert engine.fqa_threshold == 0.90
