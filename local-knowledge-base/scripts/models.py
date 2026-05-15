"""核心数据模型与类型定义"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class FileChange:
    """文件变更记录

    Attributes:
        file_path: 相对于 knowledge_folder 的路径
        absolute_path: 文件绝对路径
        status: 变更状态 ('added', 'modified', 'deleted')
        last_modified: 文件最后修改时间戳（毫秒）
    """

    file_path: str
    absolute_path: str
    status: str  # 'added' | 'modified' | 'deleted'
    last_modified: Optional[int] = None


@dataclass
class ScanResult:
    """文件扫描结果

    Attributes:
        changes: 变更文件列表
        unchanged: 未变更文件数
        errors: 扫描过程中的错误列表
    """

    changes: List[FileChange] = field(default_factory=list)
    unchanged: int = 0
    errors: List[dict] = field(default_factory=list)
    # errors 中每个 dict 包含 'path' 和 'reason' 字段


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
        distance: 距离（越小越相似）
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
    """查询结果

    Attributes:
        source: 结果来源 ('fqa' 或 'vector_store')
        answer: FQA 答案（仅当 source 为 'fqa' 时有值）
        chunks: 向量检索结果列表（仅当 source 为 'vector_store' 时有值）
        similarity: 最高相似度
    """

    source: str  # 'fqa' | 'vector_store'
    answer: Optional[str] = None
    chunks: List[SearchResult] = field(default_factory=list)
    similarity: float = 0.0


@dataclass
class CLIConfig:
    """CLI 配置项

    Attributes:
        knowledge_folder: 知识库文件夹路径
        chroma_path: ChromaDB 本地持久化路径
        chroma_collection: ChromaDB collection 名称
        fqa_file_path: FQA 文件路径
        embedding_model: Embedding 模型名称
        chunk_size: 切块大小（token）
        chunk_overlap: 重叠大小（token）
        fqa_threshold: FQA 匹配阈值
        top_k: 向量检索返回数量
    """

    knowledge_folder: str = "./docs"
    chroma_path: str = "./chroma_data"
    chroma_collection: str = "knowledge_base"
    fqa_file_path: str = "./fqa.txt"
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    chunk_size: int = 512
    chunk_overlap: int = 64
    fqa_threshold: float = 0.85
    top_k: int = 5
