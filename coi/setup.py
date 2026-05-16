#!/usr/bin/env python3
"""COI 环境安装脚本

自动安装所有 Python 运行时依赖。
"""

import os
import subprocess
import sys


def main():
    requirements_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "requirements.txt"
    )

    print("[COI] 正在安装依赖...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", requirements_path, "-q"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("[COI] 依赖安装完成！")
        print()
        print("使用方式:")
        print("  python main.py init <文档文件夹路径>   # 初始化知识库")
        print('  python main.py ask "你的问题"          # 提问')
        print('  python main.py add-fqa "问题" "答案"   # 添加标准答案')
        print("  python main.py clear                  # 清空所有数据")
    else:
        print(f"[COI] 安装失败：{result.stderr}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
