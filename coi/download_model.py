#!/usr/bin/env python3
"""预下载 ONNX Embedding 模型到本地目录

用于 CI 打包前预先下载模型，确保打包后的可执行文件完全离线运行。
模型保存到 coi/model/ 目录。

使用方式：
    python3 download_model.py

模型信息：
    名称: paraphrase-multilingual-MiniLM-L12-v2 (ONNX)
    大小: ~90MB
    维度: 384
"""

import os
import sys


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_dir = os.path.join(script_dir, "model")

    print(f"[COI] Downloading ONNX Embedding model...")
    print(f"  Save directory: {model_dir}")
    print()

    os.makedirs(model_dir, exist_ok=True)

    try:
        from huggingface_hub import hf_hub_download

        # 下载 ONNX 模型文件
        print("  Downloading model.onnx...")
        onnx_path = hf_hub_download(
            repo_id="onnx-models/paraphrase-multilingual-MiniLM-L12-v2-onnx",
            filename="model.onnx",
            local_dir=model_dir,
        )

        # 下载 tokenizer 文件
        print("  Downloading tokenizer.json...")
        tokenizer_path = hf_hub_download(
            repo_id="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            filename="tokenizer.json",
            local_dir=model_dir,
        )

        # 下载 config 文件
        print("  Downloading config.json...")
        config_path = hf_hub_download(
            repo_id="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            filename="config.json",
            local_dir=model_dir,
        )

        print(f"\n[COI] Model download complete!")
        print(f"  Directory: {model_dir}")
        print(f"  Size: {_get_dir_size(model_dir):.1f} MB")
    except Exception as e:
        print(f"\n[COI] Model download failed: {e}", file=sys.stderr)
        sys.exit(1)


def _get_dir_size(path: str) -> float:
    """Calculate directory size in MB"""
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.isfile(fp):
                total += os.path.getsize(fp)
    return total / (1024 * 1024)


if __name__ == "__main__":
    main()
