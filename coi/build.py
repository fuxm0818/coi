#!/usr/bin/env python3
"""COI 打包脚本

使用 PyInstaller 将 COI 打包为独立可执行文件。
支持 Windows / Mac / Linux 三平台。

打包前必须先执行 download_model.py 下载模型到 model/ 目录。
打包会将模型文件一起打入可执行文件，确保完全离线运行。

注意：由于内嵌 ~470MB 模型，首次启动需要解压到临时目录，
可能需要 10-30 秒。后续启动会利用系统缓存加速。
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
        print("[COI Build] 错误: model/ 目录不存在。")
        print("  请先执行: python download_model.py")
        sys.exit(1)

    if not os.path.exists(os.path.join(model_dir, "config.json")):
        print("[COI Build] 错误: model/ 目录内容不完整。")
        print("  请重新执行: python download_model.py")
        sys.exit(1)

    # 确定输出名称
    system = platform.system().lower()
    if system == "windows":
        output_name = "coi.exe"
    else:
        output_name = "coi"

    # --add-data 分隔符：Windows 用 ;，Linux/macOS 用 :
    sep = ";" if system == "windows" else ":"
    add_data_arg = f"{model_dir}{sep}model"

    # PyInstaller 参数
    args = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "coi",
        "--clean",
        "--noconfirm",
        # 将模型目录打入可执行文件
        "--add-data", add_data_arg,
        # 隐式导入 - 核心依赖
        "--hidden-import", "chromadb",
        "--hidden-import", "chromadb.config",
        "--hidden-import", "chromadb.api",
        "--hidden-import", "chromadb.api.segment",
        "--hidden-import", "chromadb.db",
        "--hidden-import", "chromadb.db.impl",
        "--hidden-import", "chromadb.segment",
        "--hidden-import", "chromadb.segment.impl",
        # 隐式导入 - ML 依赖
        "--hidden-import", "sentence_transformers",
        "--hidden-import", "torch",
        "--hidden-import", "torch.nn",
        "--hidden-import", "torch.nn.functional",
        "--hidden-import", "transformers",
        "--hidden-import", "transformers.models",
        "--hidden-import", "tokenizers",
        # 隐式导入 - 文档处理
        "--hidden-import", "numpy",
        "--hidden-import", "openpyxl",
        "--hidden-import", "docx",
        "--hidden-import", "PyPDF2",
        "--hidden-import", "markdown_it",
        # 隐式导入 - 其他
        "--hidden-import", "click",
        "--hidden-import", "tqdm",
        "--hidden-import", "huggingface_hub",
        "--hidden-import", "safetensors",
        # 排除不需要的大型包（减小体积）
        "--exclude-module", "matplotlib",
        "--exclude-module", "scipy",
        "--exclude-module", "pandas",
        "--exclude-module", "PIL",
        "--exclude-module", "cv2",
        "--exclude-module", "IPython",
        "--exclude-module", "jupyter",
        "--exclude-module", "notebook",
        "--exclude-module", "tensorboard",
        "--exclude-module", "triton",
        "--exclude-module", "nvidia",
        "--exclude-module", "cuda",
        "--exclude-module", "cupti",
        "--exclude-module", "onnxruntime",
        "--exclude-module", "sklearn",
        "--exclude-module", "sympy",
        # 入口脚本
        main_script,
    ]

    print(f"[COI Build] 目标平台: {platform.system()} {platform.machine()}")
    print(f"[COI Build] 入口脚本: {main_script}")
    print(f"[COI Build] 模型目录: {model_dir}")
    print(f"[COI Build] add-data: {add_data_arg}")
    print(f"[COI Build] 输出文件: dist/{output_name}")
    print()

    result = subprocess.run(args, cwd=script_dir)

    if result.returncode == 0:
        dist_path = os.path.join(script_dir, "dist", output_name)
        size_mb = os.path.getsize(dist_path) / (1024 * 1024)
        print(f"\n[COI Build] 打包成功！")
        print(f"  可执行文件: {dist_path}")
        print(f"  文件大小: {size_mb:.1f} MB")
        print(f"\n  使用方式:")
        print(f"    ./dist/coi init /path/to/docs")
        print(f'    ./dist/coi ask "你的问题"')
        print(f"\n  注意: 首次启动需解压模型，可能需要 10-30 秒。")
    else:
        print(f"\n[COI Build] 打包失败，退出码: {result.returncode}")
        sys.exit(1)


if __name__ == "__main__":
    build()
