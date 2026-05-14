"""pytest 共享 fixtures"""

import os
import tempfile

import pytest


@pytest.fixture
def tmp_dir():
    """创建临时目录，测试结束后自动清理"""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def sample_fqa_file(tmp_dir):
    """创建示例 FQA 文件"""
    fqa_path = os.path.join(tmp_dir, "fqa.txt")
    with open(fqa_path, "w", encoding="utf-8") as f:
        f.write("如何退货=请联系客服400-xxx-xxxx，提供订单号即可申请退货\n")
        f.write("退货运费谁承担=质量问题由我方承担运费，非质量问题由买家承担\n")
    return fqa_path
