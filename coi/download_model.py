#!/usr/bin/env python3
"""预下载 ONNX Embedding 模型到本地目录

用于打包前预先下载模型，确保打包后的可执行文件完全离线运行。
模型保存到 coi/model/ 目录。

使用方式：
    python3 download_model.py

模型信息：
    名称: BAAI/bge-small-zh-v1.5 (ONNX)
    大小: ~95MB
    维度: 512
    特点: 中文检索专精，C-MTEB 中文 Retrieval 顶级
"""

import os
import sys


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_dir = os.path.join(script_dir, "model")

    print("[COI] Downloading ONNX Embedding model: BAAI/bge-small-zh-v1.5")
    print(f"  Save directory: {model_dir}")
    print()

    os.makedirs(model_dir, exist_ok=True)

    try:
        from huggingface_hub import hf_hub_download

        onnx_repo = "onnx-community/bge-small-zh-v1.5-ONNX"
        source_repo = "BAAI/bge-small-zh-v1.5"

        # 下载 ONNX 模型文件
        print("  Downloading onnx/model.onnx...")
        hf_hub_download(
            repo_id=onnx_repo,
            filename="onnx/model.onnx",
            local_dir=model_dir,
        )

        # 下载 ONNX 外部数据文件（模型权重）
        print("  Downloading onnx/model.onnx_data...")
        hf_hub_download(
            repo_id=onnx_repo,
            filename="onnx/model.onnx_data",
            local_dir=model_dir,
        )

        # 下载 tokenizer 文件
        print("  Downloading tokenizer.json...")
        hf_hub_download(
            repo_id=source_repo,
            filename="tokenizer.json",
            local_dir=model_dir,
        )

        # 下载 config 文件
        print("  Downloading config.json...")
        hf_hub_download(
            repo_id=source_repo,
            filename="config.json",
            local_dir=model_dir,
        )

        # 验证关键文件存在
        onnx_path = os.path.join(model_dir, "onnx", "model.onnx")
        data_path = os.path.join(model_dir, "onnx", "model.onnx_data")
        tokenizer_path = os.path.join(model_dir, "tokenizer.json")

        assert os.path.exists(onnx_path), f"Missing: {onnx_path}"
        assert os.path.exists(data_path), f"Missing: {data_path}"
        assert os.path.exists(tokenizer_path), f"Missing: {tokenizer_path}"

        print(f"\n[COI] Model download complete!")
        print(f"  Directory: {model_dir}")
        print(f"  Size: {_get_dir_size(model_dir):.1f} MB")
        print(f"  Files:")
        print(f"    - onnx/model.onnx ({os.path.getsize(onnx_path) / 1024:.0f} KB)")
        print(f"    - onnx/model.onnx_data ({os.path.getsize(data_path) / (1024*1024):.1f} MB)")
        print(f"    - tokenizer.json")
        print(f"    - config.json")
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
