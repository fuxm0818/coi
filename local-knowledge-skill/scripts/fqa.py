"""FQA 文件管理

负责读取、写入和查询 FQA 问答对文件。
FQA 文件采用 UTF-8 编码的纯文本格式，每行一个问答对，使用第一个等号分隔问题和答案。
"""

import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from models import FQAPair

logger = logging.getLogger(__name__)


class FQAManager:
    """FQA 文件管理器

    负责读取、写入和查询 FQA 问答对文件。

    Attributes:
        fqa_file_path: FQA 文件路径
    """

    def __init__(self, fqa_file_path: str):
        """初始化 FQAManager。

        Args:
            fqa_file_path: FQA 文件路径
        """
        self.fqa_file_path = fqa_file_path

    def load(self) -> List[FQAPair]:
        """加载并解析 FQA 文件。

        每行以第一个 `=` 分隔问题和答案。
        跳过空行和不含 `=` 的行。

        Returns:
            解析后的 FQAPair 列表

        Raises:
            显示包含失败原因的错误信息（I/O 错误时）
        """
        pairs: List[FQAPair] = []

        if not os.path.exists(self.fqa_file_path):
            return pairs

        try:
            with open(self.fqa_file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.rstrip("\n").rstrip("\r")
                    # 跳过空行
                    if not line.strip():
                        continue
                    # 跳过不含 = 的行
                    if "=" not in line:
                        continue
                    # 以第一个 = 分隔问题和答案
                    question, answer = line.split("=", 1)
                    pairs.append(FQAPair(question=question, answer=answer))
        except OSError as e:
            logger.error("读取 FQA 文件失败 [%s]: %s", self.fqa_file_path, e)
            raise RuntimeError(f"读取 FQA 文件失败 [{self.fqa_file_path}]: {e}") from e

        return pairs

    def append(self, question: str, answer: str) -> None:
        """追加写入一条问答对到 FQA 文件末尾。

        如果 FQA 文件不存在，自动创建文件及父目录。

        Args:
            question: 问题
            answer: 答案

        Raises:
            RuntimeError: I/O 错误时显示包含失败原因的错误信息
        """
        try:
            # 确保父目录存在
            parent_dir = os.path.dirname(self.fqa_file_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            with open(self.fqa_file_path, "a", encoding="utf-8") as f:
                f.write(f"{question}={answer}\n")
        except OSError as e:
            logger.error("写入 FQA 文件失败 [%s]: %s", self.fqa_file_path, e)
            raise RuntimeError(f"写入 FQA 文件失败 [{self.fqa_file_path}]: {e}") from e

    def semantic_match(
        self, query_vector: np.ndarray, embedding_engine
    ) -> Optional[Tuple[FQAPair, float]]:
        """对所有 FQA 问题向量化后计算余弦相似度，返回最高匹配。

        流程：
        1. 加载所有 FQA 问答对
        2. 使用 embedding_engine.embed_batch() 对所有问题进行向量化
        3. 计算 query_vector 与每个问题向量的余弦相似度
        4. 返回最高匹配的 (FQAPair, similarity_score) 或 None（无问答对时）

        Args:
            query_vector: 查询向量（numpy 数组）
            embedding_engine: 嵌入引擎实例，需提供 embed_batch() 方法

        Returns:
            最高匹配的 (FQAPair, similarity_score) 元组，或 None（无问答对时）
        """
        pairs = self.load()

        if not pairs:
            return None

        # 提取所有问题文本
        questions = [pair.question for pair in pairs]

        # 批量向量化所有问题
        question_vectors = embedding_engine.embed_batch(questions)

        # 计算余弦相似度
        # query_vector 和 question_vectors 都已经过 normalize_embeddings=True 归一化
        # 所以余弦相似度 = 点积
        query_vec = np.asarray(query_vector, dtype=np.float32)

        # 确保 query_vector 是一维的
        if query_vec.ndim > 1:
            query_vec = query_vec.flatten()

        # 归一化 query_vector（以防未归一化）
        query_norm = np.linalg.norm(query_vec)
        if query_norm > 0:
            query_vec = query_vec / query_norm

        best_similarity = -1.0
        best_pair: Optional[FQAPair] = None

        for i, q_vec in enumerate(question_vectors):
            q_vec = np.asarray(q_vec, dtype=np.float32)
            # 归一化问题向量
            q_norm = np.linalg.norm(q_vec)
            if q_norm > 0:
                q_vec = q_vec / q_norm

            similarity = float(np.dot(query_vec, q_vec))

            if similarity > best_similarity:
                best_similarity = similarity
                best_pair = pairs[i]

        if best_pair is None:
            return None

        return (best_pair, best_similarity)
