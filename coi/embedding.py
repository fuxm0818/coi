"""本地 Embedding 引擎

使用 ONNX Runtime 加载 BAAI/bge-small-zh-v1.5 模型，
专为中文文档检索优化，不依赖 PyTorch。

模型特点：
- 中文检索效果优秀（C-MTEB Retrieval 顶级）
- 体积小（24M 参数，~95MB ONNX）
- 512 维向量输出
- v1.5 修复了相似度分布问题，阈值判断更准确

模型加载优先级：
1. 程序同级 model/ 目录（打包后的离线模型）
2. PyInstaller 打包目录中的 model/
3. 从 HuggingFace 下载（开发模式，首次需联网）
"""

import logging
import os
import sys
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


def _get_bundled_model_path() -> Optional[str]:
    """获取打包内嵌的模型路径

    PyInstaller onefile 模式下，--add-data 的文件解压到 _MEIPASS 临时目录。

    Returns:
        模型目录路径，如果不存在返回 None
    """
    candidates = []

    if getattr(sys, "frozen", False):
        # onefile 模式：_MEIPASS 临时目录
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(os.path.join(meipass, "model"))
        # onedir 模式：_internal/model
        exe_dir = os.path.dirname(sys.executable)
        candidates.append(os.path.join(exe_dir, "_internal", "model"))
        candidates.append(os.path.join(exe_dir, "model"))
    else:
        # 开发模式：脚本同级
        candidates.append(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "model")
        )

    for path in candidates:
        if os.path.isdir(path):
            if os.path.exists(os.path.join(path, "onnx", "model.onnx")):
                return path
            if os.path.exists(os.path.join(path, "model.onnx")):
                return path

    return None


def _find_onnx_file(model_dir: str) -> str:
    """在模型目录中查找 model.onnx 文件"""
    # 优先 onnx/ 子目录
    onnx_subdir = os.path.join(model_dir, "onnx", "model.onnx")
    if os.path.exists(onnx_subdir):
        return onnx_subdir
    # 直接在根目录
    onnx_root = os.path.join(model_dir, "model.onnx")
    if os.path.exists(onnx_root):
        return onnx_root
    raise FileNotFoundError(f"model.onnx not found in {model_dir}")


class EmbeddingEngine:
    """本地嵌入引擎（ONNX Runtime）

    模型: BAAI/bge-small-zh-v1.5（512 维，中文检索专精）
    推理: ONNX Runtime（无需 PyTorch）
    延迟加载：模型在首次调用时才加载。
    """

    MODEL_NAME = "BAAI/bge-small-zh-v1.5"
    VECTOR_DIM = 512

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
                onnx_path = _find_onnx_file(local_path)
                tokenizer_path = os.path.join(local_path, "tokenizer.json")
            else:
                # 开发模式：从 HuggingFace 下载
                logger.info("从 HuggingFace 下载模型: %s", self._model_name)
                from huggingface_hub import hf_hub_download

                onnx_path = hf_hub_download(
                    repo_id="onnx-community/bge-small-zh-v1.5-ONNX",
                    filename="onnx/model.onnx",
                )
                tokenizer_path = hf_hub_download(
                    repo_id=self._model_name,
                    filename="tokenizer.json",
                )

            if not os.path.exists(onnx_path):
                raise FileNotFoundError(f"ONNX 模型文件不存在: {onnx_path}")
            if not os.path.exists(tokenizer_path):
                raise FileNotFoundError(f"Tokenizer 文件不存在: {tokenizer_path}")

            # 加载 ONNX 模型
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            sess_options.intra_op_num_threads = os.cpu_count() or 4
            self._session = ort.InferenceSession(onnx_path, sess_options)

            # 加载 tokenizer
            self._tokenizer = Tokenizer.from_file(tokenizer_path)
            self._tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")
            self._tokenizer.enable_truncation(max_length=512)

            logger.info("ONNX 模型加载完成: %s, 向量维度: %d", self._model_name, self.VECTOR_DIM)
        except Exception as e:
            raise RuntimeError(f"Embedding 模型加载失败: {e}") from e

    def embed(self, text: str) -> np.ndarray:
        """单条文本向量化

        Args:
            text: 输入文本

        Returns:
            512 维归一化 numpy 数组
        """
        self._ensure_loaded()
        return self._encode_texts([text])[0]

    def embed_batch(self, texts: list) -> np.ndarray:
        """批量文本向量化

        Args:
            texts: 文本列表

        Returns:
            shape=(n, 512) 的归一化 numpy 数组
        """
        self._ensure_loaded()
        return self._encode_texts(texts)

    def _encode_texts(self, texts: list) -> np.ndarray:
        """内部编码方法：tokenize → ONNX 推理 → CLS pooling → normalize

        bge 模型使用 [CLS] token 的输出作为句子表示（不是 mean pooling）。
        """
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

        # 检查模型实际输入名
        input_names = {inp.name for inp in self._session.get_inputs()}
        feeds = {k: v for k, v in feeds.items() if k in input_names}

        outputs = self._session.run(None, feeds)

        # outputs[0] shape: (batch, seq_len, hidden_dim) — last_hidden_state
        # bge 使用 [CLS] token（第 0 个位置）作为句子表示
        embeddings = outputs[0][:, 0, :]  # CLS pooling

        # L2 归一化
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.clip(norms, a_min=1e-9, a_max=None)
        embeddings = embeddings / norms

        return embeddings.astype(np.float32)

    def get_tokenizer(self):
        """返回 tokenizer 实例供 TextChunker 使用"""
        self._ensure_loaded()
        return _TokenizerWrapper(self._tokenizer)


class _TokenizerWrapper:
    """Tokenizer 包装器，提供与 HuggingFace tokenizer 兼容的接口"""

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
