#!/usr/bin/env python3
"""预下载 Embedding 模型到本地目录

用于 CI 打包前预先下载模型，确保打包后的可执行文件完全离线运行。
模型保存到 coi/model/ 目录，PyInstaller 打包时会将其一起打入。

使用方式：
    python3 download_model.py

模型信息：
    名称: paraphrase-multilingual-MiniLM-L12-v2
    大小: ~470MB
    维度: 384
"""

import os
import sys


def main():
    model_name = "paraphrase-multilingual-MiniLM-L12-v2"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_dir = os.path.join(script_dir, "model")

    print(f"[COI] 正在下载 Embedding 模型: {model_name}")
    print(f"  保存目录: {model_dir}")
    print()

    try:
        from sentence_transformers import SentenceTransformer

        # 下载并保存到本地目录
        model = SentenceTransformer(model_name)
        model.save(model_dir)

        print(f"\n[COI] 模型下载完成！")
        print(f"  目录: {model_dir}")
        print(f"  大小: {_get_dir_size(model_dir):.1f} MB")
    except Exception as e:
        print(f"\n[COI] 模型下载失败: {e}", file=sys.stderr)
        sys.exit(1)


def _get_dir_size(path: str) -> float:
    """计算目录大小（MB）"""
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total += os.path.getsize(fp)
    return total / (1024 * 1024)


if __name__ == "__main__":
    main()
