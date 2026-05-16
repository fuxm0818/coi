"""共享测试 fixtures"""

import os
import sys
import tempfile
import shutil

import pytest

# 确保 coi/ 目录在 path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def tmp_dir():
    """创建临时目录，测试结束后自动清理"""
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sample_docs_dir(tmp_dir):
    """创建包含各种格式示例文档的临时目录"""
    # TXT
    with open(os.path.join(tmp_dir, "hello.txt"), "w", encoding="utf-8") as f:
        f.write("这是一个测试文档。\n包含中文内容，用于验证文本提取功能。")

    # MD
    with open(os.path.join(tmp_dir, "readme.md"), "w", encoding="utf-8") as f:
        f.write("# 标题\n\n这是 Markdown 文档的正文内容。\n\n## 二级标题\n\n列表项内容。")

    # CSV
    with open(os.path.join(tmp_dir, "data.csv"), "w", encoding="utf-8") as f:
        f.write("姓名,年龄,城市\n张三,25,北京\n李四,30,上海\n")

    # 子目录
    sub_dir = os.path.join(tmp_dir, "subdir")
    os.makedirs(sub_dir)
    with open(os.path.join(sub_dir, "nested.txt"), "w", encoding="utf-8") as f:
        f.write("子目录中的文档内容。")

    # 隐藏文件（应被排除）
    with open(os.path.join(tmp_dir, ".hidden.txt"), "w", encoding="utf-8") as f:
        f.write("隐藏文件不应被扫描。")

    # 隐藏目录（应被排除）
    hidden_dir = os.path.join(tmp_dir, ".hidden_dir")
    os.makedirs(hidden_dir)
    with open(os.path.join(hidden_dir, "secret.txt"), "w", encoding="utf-8") as f:
        f.write("隐藏目录中的文件不应被扫描。")

    # 不支持的格式（应被排除）
    with open(os.path.join(tmp_dir, "image.png"), "wb") as f:
        f.write(b"\x89PNG\r\n")

    return tmp_dir


@pytest.fixture
def empty_docs_dir(tmp_dir):
    """创建空的文档目录（无支持格式文件）"""
    with open(os.path.join(tmp_dir, "image.png"), "wb") as f:
        f.write(b"\x89PNG\r\n")
    with open(os.path.join(tmp_dir, "video.mp4"), "wb") as f:
        f.write(b"\x00\x00")
    return tmp_dir
