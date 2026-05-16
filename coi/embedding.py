"""本地 Embedding 引擎

使用 sentence-transformers 加载 paraphrase-multilingual-MiniLM-L12-v2 模型，
支持中文和多语言文本的本地向量化，不依赖任何在线服务。

模型加载优先级：
1. 程序同级 model/ 目录（打包后的离线模型）
2. PyInstaller _MEIPASS 临时目录中的 model/（打包运行时）
3. 按模型名称加载（开发模式，首次需联网下载）
"""

import logging
import os
import sys
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


def _get_bundled_model_path() -> Optional[str]:
    """获取打包内嵌的模型路径

    按优先级查找：
    1. PyInstaller 运行时临时目录 (_MEIPASS/model)
    2. 可执行文件同级目录 (model/)
    3. 脚本同级目录 (model/) — 开发模式

    Returns:
        模型目录路径，如果不存在返回 None
    """
    candidates = []

    # PyInstaller 打包后的临时目录
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(os.path.join(meipass, "model"))
        # 可执行文件同级
        candidates.append(os.path.join(os.path.dirname(sys.executable), "model"))
    else:
        # 开发模式：脚本同级
        candidates.append(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "model")
        )

    for path in candidates:
        if os.path.isdir(path):
            # 验证目录内有模型文件（至少有 config.json）
            if os.path.exists(os.path.join(path, "config.json")):
                return path

    return None


class EmbeddingEngine:
    """本地嵌入引擎

    模型: paraphrase-multilingual-MiniLM-L12-v2（384 维，多语言）
    延迟加载：模型在首次调用 embed/embed_batch/get_tokenizer 时才加载。
    """

    MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
    VECTOR_DIM = 384

    def __init__(self, model_name: Optional[str] = None):
        """初始化 EmbeddingEngine

        Args:
            model_name: 模型名称或本地路径，默认自动检测
        """
        self._model_name = model_name or self.MODEL_NAME
        self._model = None
        self._tokenizer = None

    def _ensure_loaded(self) -> None:
        """确保模型已加载（延迟加载）

        加载优先级：
        1. 本地打包的 model/ 目录（离线模式）
        2. 按模型名称加载（开发模式，可能需要联网）

        Raises:
            RuntimeError: 模型加载失败时
        """
        if self._model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer

            # 优先使用本地打包的模型
            local_path = _get_bundled_model_path()
            if local_path:
                logger.info("从本地目录加载模型: %s", local_path)
                self._model = SentenceTransformer(local_path)
            else:
                logger.info("按名称加载模型: %s", self._model_name)
                self._model = SentenceTransformer(self._model_name)

            self._tokenizer = self._model.tokenizer
            logger.info("模型加载完成，向量维度: %d", self.VECTOR_DIM)
        except Exception as e:
            raise RuntimeError(f"Embedding 模型加载失败: {e}") from e

    def embed(self, text: str) -> np.ndarray:
        """单条文本向量化

        Args:
            text: 输入文本

        Returns:
            384 维归一化 numpy 数组
        """
        self._ensure_loaded()
        vector = self._model.encode(text, normalize_embeddings=True)
        return np.asarray(vector, dtype=np.float32)

    def embed_batch(self, texts: list) -> np.ndarray:
        """批量文本向量化

        Args:
            texts: 文本列表

        Returns:
            shape=(n, 384) 的归一化 numpy 数组
        """
        self._ensure_loaded()
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return np.asarray(vectors, dtype=np.float32)

    def get_tokenizer(self):
        """返回 tokenizer 实例供 TextChunker 使用

        Returns:
            模型对应的 tokenizer 实例
        """
        self._ensure_loaded()
        return self._tokenizer
