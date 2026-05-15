#!/usr/bin/env python3
"""自动安装知识库工具所需的 Python 依赖"""
import subprocess
import sys
import os

def main():
    requirements_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
    print("正在安装本地知识库工具依赖...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", requirements_path, "-q"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("依赖安装完成！")
    else:
        print(f"安装失败：{result.stderr}")
        sys.exit(1)

if __name__ == "__main__":
    main()
