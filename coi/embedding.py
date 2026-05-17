"""本地 Embedding 引擎

使用 ONNX Runtime 加载 paraphrase-multilingual-MiniLM-L12-v2 模型，
支持中文和多语言文本的本地向量化，不依赖 PyTorch。

相比 PyTorch 方案：
- 运行时依赖从 ~500MB 降到 ~30MB
- 推理速度更快（ONNX Runtime 优化）
- 打包体积大幅缩小

模型加载优先级：
1. 程序同级 model/ 目录（打包后的离线模型）
2. PyInstaller/Nuitka 打包目录中的 model/
3. 按名称从 HuggingFace 下载（开发模式，首次需联网）
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
    1. 可执行文件同级 model/ 目录
    2. 可执行文件同级 _internal/model/ 目录（PyInstaller 6.x）
    3. 脚本同级 model/ 目录（开发模式）

    Returns:
        模型目录路径，如果不存在返回 None
    """
    candidates = []

    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        candidates.append(os.path.join(exe_dir, "model"))
        candidates.append(os.path.join(exe_dir, "_internal", "model"))
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(os.path.join(meipass, "model"))
    else:
        candidates.append(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "model")
        )

    for path in candidates:
        if os.path.isdir(path):
            # 检查 ONNX 模型文件或 config.json 存在
            has_onnx = os.path.exists(os.path.join(path, "model.onnx"))
            has_config = os.path.exists(os.path.join(path, "config.json"))
            if has_onnx or has_config:
                return path

    return None


class EmbeddingEngine:
    """本地嵌入引擎（ONNX Runtime）

    模型: paraphrase-multilingual-MiniLM-L12-v2（384 维，多语言）
    推理: ONNX Runtime（无需 PyTorch）
    延迟加载：模型在首次调用时才加载。
    """

    MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    VECTOR_DIM = 384

    def __init__(self, model_name: Optional[str] = None):
        self._model_name = model_name or self.MODEL_NAME
        self._session = None
        self._tokenizer = None

    def _ensure_loaded(self) -> None:
        """确保模型已加载（延迟加载）

        Raises:
            RuntimeError: 模型加载失败时
        """
        if self._session is not None:
            return

        try:
            import onnxruntime as ort
            from tokenizers import Tokenizer

            local_path = _get_bundled_model_path()

            if local_path:
                logger.info("从本地目录加载 ONNX 模型: %s", local_path)
                onnx_path = os.path.join(local_path, "model.onnx")
                tokenizer_path = os.path.join(local_path, "tokenizer.json")
            else:
                # 开发模式：从 HuggingFace 下载
                logger.info("从 HuggingFace 下载模型: %s", self._model_name)
                from huggingface_hub import hf_hub_download

                onnx_path = hf_hub_download(
                    repo_id="onnx-models/paraphrase-multilingual-MiniLM-L12-v2-onnx",
                    filename="model.onnx",
                )
                tokenizer_path = hf_hub_download(
                    repo_id=self._model_name,
                    filename="tokenizer.json",
                )

            if not os.path.exists(onnx_path):
                raise FileNotFoundError(f"ONNX 模型文件不存在: {onnx_path}")

            # 加载 ONNX 模型
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            sess_options.intra_op_num_threads = os.cpu_count() or 4
            self._session = ort.InferenceSession(onnx_path, sess_options)

            # 加载 tokenizer
            self._tokenizer = Tokenizer.from_file(tokenizer_path)
            self._tokenizer.enable_padding(pad_id=1, pad_token="<pad>")
            self._tokenizer.enable_truncation(max_length=512)

            logger.info("ONNX 模型加载完成，向量维度: %d", self.VECTOR_DIM)
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
        return self._encode_texts([text])[0]

    def embed_batch(self, texts: list) -> np.ndarray:
        """批量文本向量化

        Args:
            texts: 文本列表

        Returns:
            shape=(n, 384) 的归一化 numpy 数组
        """
        self._ensure_loaded()
        return self._encode_texts(texts)

    def _encode_texts(self, texts: list) -> np.ndarray:
        """内部编码方法：tokenize → ONNX 推理 → mean pooling → normalize"""
        # Tokenize
        encodings = self._tokenizer.encode_batch(texts)

        input_ids = np.array([e.ids for e in encodings], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
        token_type_ids = np.zeros_like(input_ids, dtype=np.int64)

        # ONNX 推理
        feeds = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "token_type_ids": token_type_ids,
        }

        # 检查模型输入名，有些 ONNX 模型没有 token_type_ids
        input_names = [inp.name for inp in self._session.get_inputs()]
        if "token_type_ids" not in input_names:
            del feeds["token_type_ids"]

        outputs = self._session.run(None, feeds)

        # outputs[0] shape: (batch, seq_len, hidden_dim) — last_hidden_state
        token_embeddings = outputs[0]

        # Mean pooling（考虑 attention_mask）
        mask_expanded = attention_mask[:, :, np.newaxis].astype(np.float32)
        sum_embeddings = np.sum(token_embeddings * mask_expanded, axis=1)
        sum_mask = np.sum(mask_expanded, axis=1)
        sum_mask = np.clip(sum_mask, a_min=1e-9, a_max=None)
        embeddings = sum_embeddings / sum_mask

        # L2 归一化
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.clip(norms, a_min=1e-9, a_max=None)
        embeddings = embeddings / norms

        return embeddings.astype(np.float32)

    def get_tokenizer(self):
        """返回 tokenizer 实例供 TextChunker 使用

        返回一个兼容接口的包装器。
        """
        self._ensure_loaded()
        return _TokenizerWrapper(self._tokenizer)


class _TokenizerWrapper:
    """Tokenizer 包装器，提供与 HuggingFace tokenizer 兼容的接口

    TextChunker 需要 encode() 和 decode() 方法。
    """

    def __init__(self, tokenizer):
        self._tokenizer = tokenizer

    def encode(self, text: str, add_special_tokens: bool = False) -> list:
        """编码文本为 token ID 列表"""
        encoding = self._tokenizer.encode(text)
        ids = encoding.ids
        if not add_special_tokens and len(ids) >= 2:
            # 移除 [CLS] 和 [SEP]
            ids = ids[1:-1]
        return ids

    def decode(self, token_ids: list, skip_special_tokens: bool = True) -> str:
        """将 token ID 列表解码为文本"""
        return self._tokenizer.decode(token_ids, skip_special_tokens=skip_special_tokens)
