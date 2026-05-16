"""COI 核心数据模型

定义所有模块间共享的数据结构，使用 Python dataclass 实现。
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class FileChange:
    """文件扫描记录

    Attributes:
        file_path: 相对于文档文件夹的路径
        absolute_path: 文件绝对路径
        status: 状态（'added'）
        last_modified: 文件最后修改时间戳（毫秒）
    """

    file_path: str
    absolute_path: str
    status: str  # 'added'
    last_modified: Optional[int] = None


@dataclass
class ScanResult:
    """文件扫描结果

    Attributes:
        changes: 发现的文件列表
        errors: 扫描过程中的错误列表（每项含 'path' 和 'reason'）
    """

    changes: List[FileChange] = field(default_factory=list)
    errors: List[dict] = field(default_factory=list)


@dataclass
class Chunk:
    """文本切块

    Attributes:
        text: 切块文本内容
        index: 在源文件中的序号（从 0 开始）
        token_count: 该块的 token 数量
    """

    text: str
    index: int
    token_count: int


@dataclass
class ChunkMetadata:
    """向量块元数据

    Attributes:
        file_path: 源文件相对路径
        file_hash: 源文件内容 SHA-256 哈希
        chunk_index: Chunk 序号（从 0 开始）
        last_modified: 源文件最后修改时间戳（毫秒）
    """

    file_path: str
    file_hash: str
    chunk_index: int
    last_modified: int


@dataclass
class SearchResult:
    """向量检索结果

    Attributes:
        text: 文本内容
        metadata: 元数据
        distance: cosine 距离（越小越相似）
    """

    text: str
    metadata: ChunkMetadata
    distance: float


@dataclass
class FQAPair:
    """FQA 问答对

    Attributes:
        question: 问题
        answer: 答案
    """

    question: str
    answer: str


@dataclass
class QueryResult:
    """双源合并查询结果

    最终回答 = 向量库检索到的文档原文相关片段 + 用户自定义 FQA 标准答案
    两类信息叠加整合，统一输出。

    Attributes:
        fqa_answer: FQA 匹配到的标准答案（无匹配时为 None）
        fqa_similarity: FQA 匹配相似度
        vector_chunks: 向量检索结果列表
        vector_best_similarity: 向量检索最高相似度
    """

    fqa_answer: Optional[str] = None
    fqa_similarity: float = 0.0
    vector_chunks: List[SearchResult] = field(default_factory=list)
    vector_best_similarity: float = 0.0
