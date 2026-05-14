"""本地 Embedding 引擎

使用 sentence-transformers 加载 paraphrase-multilingual-MiniLM-L12-v2 模型，
支持中文和多语言文本的本地向量化，不依赖任何在线服务。
"""

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingEngine:
    """本地嵌入引擎，使用 sentence-transformers 进行文本向量化。

    采用延迟加载策略，模型在首次调用 embed/embed_batch/get_tokenizer 时才加载。

    Attributes:
        MODEL_NAME: 默认模型名称
        VECTOR_DIM: 向量维度（384）
    """

    MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
    VECTOR_DIM = 384

    def __init__(self, model_name: Optional[str] = None):
        """初始化 EmbeddingEngine。

        Args:
            model_name: 模型名称，默认使用 paraphrase-multilingual-MiniLM-L12-v2
        """
        self._model_name = model_name or self.MODEL_NAME
        self._model = None
        self._tokenizer = None

    def _ensure_loaded(self) -> None:
        """确保模型已加载（延迟加载）。

        首次调用时加载模型和 tokenizer，后续调用直接返回。
        """
        if self._model is None:
            logger.info("正在加载 Embedding 模型: %s", self._model_name)
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
            self._tokenizer = self._model.tokenizer
            logger.info("模型加载完成，向量维度: %d", self.VECTOR_DIM)

    def embed(self, text: str) -> np.ndarray:
        """单条文本向量化。

        Args:
            text: 输入文本

        Returns:
            384 维 numpy 数组
        """
        self._ensure_loaded()
        vector = self._model.encode(text, normalize_embeddings=True)
        return np.asarray(vector, dtype=np.float32)

    def embed_batch(self, texts: list) -> np.ndarray:
        """批量文本向量化。

        Args:
            texts: 文本列表

        Returns:
            shape=(n, 384) 的 numpy 数组
        """
        self._ensure_loaded()
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return np.asarray(vectors, dtype=np.float32)

    def get_tokenizer(self):
        """返回 tokenizer 实例供 TextChunker 使用。

        Returns:
            模型对应的 tokenizer 实例
        """
        self._ensure_loaded()
        return self._tokenizer
