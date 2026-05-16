"""FQA 标准答案管理

使用 JSON 格式存储用户自定义的问答对（fqa.json）。
支持语义匹配，提问时自动调取相似问题的标准答案。
"""

import json
import logging
import os
from typing import List, Optional, Tuple

import numpy as np

from models import FQAPair

logger = logging.getLogger(__name__)


class FQAManager:
    """FQA 标准答案管理器

    管理 fqa.json 文件中的问答对，支持追加和语义匹配。
    """

    def __init__(self, fqa_file_path: str):
        """初始化 FQAManager

        Args:
            fqa_file_path: fqa.json 文件路径
        """
        self.fqa_file_path = fqa_file_path

    def load(self) -> List[FQAPair]:
        """加载所有 FQA 条目

        JSON 解析失败时返回空列表，不中断程序。

        Returns:
            FQAPair 列表
        """
        if not os.path.exists(self.fqa_file_path):
            return []

        try:
            with open(self.fqa_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            pairs = []
            for item in data:
                if isinstance(item, dict) and "question" in item and "answer" in item:
                    pairs.append(FQAPair(
                        question=item["question"],
                        answer=item["answer"],
                    ))
            return pairs
        except (json.JSONDecodeError, OSError, TypeError) as e:
            logger.error("读取 FQA 文件失败 [%s]: %s", self.fqa_file_path, e)
            return []

    def append(self, question: str, answer: str) -> None:
        """追加一条问答对

        自动创建文件和父目录。如果文件不存在则初始化为 JSON 数组。

        Args:
            question: 问题
            answer: 答案

        Raises:
            RuntimeError: 文件写入失败时
        """
        # 确保父目录存在
        parent_dir = os.path.dirname(self.fqa_file_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        # 加载现有数据
        pairs = []
        if os.path.exists(self.fqa_file_path):
            try:
                with open(self.fqa_file_path, "r", encoding="utf-8") as f:
                    pairs = json.load(f)
            except (json.JSONDecodeError, OSError):
                pairs = []

        # 追加新记录
        pairs.append({"question": question, "answer": answer})

        # 写入文件
        try:
            with open(self.fqa_file_path, "w", encoding="utf-8") as f:
                json.dump(pairs, f, ensure_ascii=False, indent=2)
        except OSError as e:
            raise RuntimeError(f"写入 FQA 文件失败: {e}") from e

    def semantic_match(
        self, query_vector: np.ndarray, embedding_engine, threshold: float = 0.85
    ) -> Optional[Tuple[FQAPair, float]]:
        """语义匹配 FQA 问题，返回最高匹配

        对所有 FQA 问题向量化后计算余弦相似度。

        Args:
            query_vector: 查询向量（归一化）
            embedding_engine: 嵌入引擎实例
            threshold: 匹配阈值（不在此处过滤，由调用方决定）

        Returns:
            最高匹配的 (FQAPair, similarity_score) 或 None（无问答对时）
        """
        pairs = self.load()

        if not pairs:
            return None

        # 提取所有问题文本并批量向量化
        questions = [pair.question for pair in pairs]
        question_vectors = embedding_engine.embed_batch(questions)

        # 准备查询向量
        query_vec = np.asarray(query_vector, dtype=np.float32)
        if query_vec.ndim > 1:
            query_vec = query_vec.flatten()

        # 归一化查询向量
        query_norm = np.linalg.norm(query_vec)
        if query_norm > 0:
            query_vec = query_vec / query_norm

        # 计算余弦相似度（归一化向量的点积）
        best_similarity = -1.0
        best_pair: Optional[FQAPair] = None

        for i, q_vec in enumerate(question_vectors):
            q_vec = np.asarray(q_vec, dtype=np.float32)
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
