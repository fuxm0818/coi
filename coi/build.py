#!/usr/bin/env python3
"""COI 打包脚本

使用 PyInstaller 将 COI 打包为独立可执行文件。
支持 Windows / Mac / Linux 三平台。

由于使用 ONNX Runtime 替代 PyTorch，打包体积大幅缩小：
- 程序+依赖: ~100-150MB（无 PyTorch）
- 模型文件: ~90MB
- 总计: ~200-250MB（压缩后更小）

打包前必须先执行 download_model.py 下载模型到 model/ 目录。
"""

import os
import platform
import shutil
import subprocess
import sys


def build():
    """执行打包"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(script_dir, "main.py")
    model_dir = os.path.join(script_dir, "model")

    # 检查模型是否已下载
    if not os.path.isdir(model_dir):
        print("[COI Build] Error: model/ directory not found.")
        print("  Please run: python download_model.py")
        sys.exit(1)

    if not os.path.exists(os.path.join(model_dir, "model.onnx")):
        print("[COI Build] Error: model/model.onnx not found.")
        print("  Please re-run: python download_model.py")
        sys.exit(1)

    system = platform.system().lower()

    # PyInstaller 参数（不含模型，模型单独复制）
    args = [
        sys.executable, "-m", "PyInstaller",
        "--onedir",
        "--name", "coi",
        "--clean",
        "--noconfirm",
        # 隐式导入
        "--hidden-import", "chromadb",
        "--hidden-import", "chromadb.config",
        "--hidden-import", "chromadb.api",
        "--hidden-import", "chromadb.api.segment",
        "--hidden-import", "chromadb.db",
        "--hidden-import", "chromadb.db.impl",
        "--hidden-import", "chromadb.segment",
        "--hidden-import", "chromadb.segment.impl",
        "--hidden-import", "onnxruntime",
        "--hidden-import", "tokenizers",
        "--hidden-import", "numpy",
        "--hidden-import", "openpyxl",
        "--hidden-import", "docx",
        "--hidden-import", "PyPDF2",
        "--hidden-import", "markdown_it",
        "--hidden-import", "click",
        "--hidden-import", "tqdm",
        "--hidden-import", "huggingface_hub",
        # 排除不需要的包
        "--exclude-module", "matplotlib",
        "--exclude-module", "pandas",
        "--exclude-module", "PIL",
        "--exclude-module", "cv2",
        "--exclude-module", "IPython",
        "--exclude-module", "jupyter",
        "--exclude-module", "tensorboard",
        "--exclude-module", "torch",
        "--exclude-module", "torchvision",
        "--exclude-module", "tensorflow",
        "--exclude-module", "keras",
        # 入口脚本
        main_script,
    ]

    print(f"[COI Build] Platform: {platform.system()} {platform.machine()}")
    print(f"[COI Build] Entry: {main_script}")
    print(f"[COI Build] Model: {model_dir}")
    print(f"[COI Build] Mode: onedir (ONNX Runtime, no PyTorch)")
    print()

    result = subprocess.run(args, cwd=script_dir)

    if result.returncode != 0:
        print(f"\n[COI Build] PyInstaller failed, exit code: {result.returncode}")
        sys.exit(1)

    # 将模型目录复制到 dist/coi/model/
    dist_coi_dir = os.path.join(script_dir, "dist", "coi")
    dist_model_dir = os.path.join(dist_coi_dir, "model")

    print(f"\n[COI Build] Copying model files...")
    if os.path.exists(dist_model_dir):
        shutil.rmtree(dist_model_dir)
    shutil.copytree(model_dir, dist_model_dir)

    # 计算最终大小
    total_size = _get_dir_size(dist_coi_dir)
    model_size = _get_dir_size(dist_model_dir)

    print(f"\n[COI Build] Success!")
    print(f"  Output: {dist_coi_dir}")
    print(f"  Total size: {total_size:.0f} MB")
    print(f"    - Program + deps: {total_size - model_size:.0f} MB")
    print(f"    - Model files: {model_size:.0f} MB")
    print(f"\n  Usage:")
    if system == "windows":
        print(f"    .\\dist\\coi\\coi.exe init C:\\path\\to\\docs")
        print(f'    .\\dist\\coi\\coi.exe ask "your question"')
    else:
        print(f"    ./dist/coi/coi init /path/to/docs")
        print(f'    ./dist/coi/coi ask "your question"')


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
    build()
