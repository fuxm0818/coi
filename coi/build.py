#!/usr/bin/env python3
"""COI 打包脚本

使用 PyInstaller --onefile 模式打包为单个可执行文件。
模型通过 --add-data 内嵌，最终产物就是一个文件：coi（或 coi.exe）。

由于使用 ONNX Runtime + bge-small-zh-v1.5（无 PyTorch），
单文件体积约 200MB，不会再出现之前 PyTorch 方案磁盘爆满的问题。

打包前必须先执行 download_model.py 下载模型到 model/ 目录。
"""

import os
import platform
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

    has_onnx = (
        os.path.exists(os.path.join(model_dir, "onnx", "model.onnx"))
        or os.path.exists(os.path.join(model_dir, "model.onnx"))
    )
    if not has_onnx:
        print("[COI Build] Error: model.onnx not found.")
        print("  Please re-run: python download_model.py")
        sys.exit(1)

    system = platform.system().lower()
    machine = platform.machine().lower()
    sep = ";" if system == "windows" else ":"
    output_name = "coi.exe" if system == "windows" else "coi"

    # macOS 交叉编译支持
    # 设置 ARCHFLAGS 环境变量来指定目标架构
    env = os.environ.copy()
    if system == "darwin":
        # 检查是否需要交叉编译
        target_arch = os.environ.get("COI_TARGET_ARCH", machine)
        if target_arch != machine:
            env["ARCHFLAGS"] = f"-arch {target_arch}"
            print(f"[COI Build] Cross-compiling for {target_arch} on {machine}")

    # PyInstaller 参数 - onefile 模式，单文件分发
    args = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "coi",
        "--clean",
        "--noconfirm",
        # 模型内嵌
        "--add-data", f"{model_dir}{sep}model",
        # 隐式导入
        "--collect-submodules", "chromadb",
        "--hidden-import", "chromadb",
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
    print(f"[COI Build] Model: {model_dir} (bundled)")
    print(f"[COI Build] Mode: --onefile (single executable)")
    print(f"[COI Build] Output: dist/{output_name}")
    print()

    result = subprocess.run(args, cwd=script_dir, env=env)

    if result.returncode != 0:
        print(f"\n[COI Build] Failed, exit code: {result.returncode}")
        sys.exit(1)

    dist_path = os.path.join(script_dir, "dist", output_name)
    size_mb = os.path.getsize(dist_path) / (1024 * 1024)

    print(f"\n[COI Build] Success!")
    print(f"  File: {dist_path}")
    print(f"  Size: {size_mb:.0f} MB")
    print(f"\n  Usage:")
    if system == "windows":
        print(f"    .\\coi.exe init C:\\path\\to\\docs")
        print(f'    .\\coi.exe ask "your question"')
    else:
        print(f"    ./coi init /path/to/docs")
        print(f'    ./coi ask "your question"')


if __name__ == "__main__":
    build()
