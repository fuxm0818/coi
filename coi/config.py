"""COI 数据目录管理

所有程序数据统一存放于程序同级目录 coi_data/ 文件夹：
- config.json: 用户 init 时绑定的本地文档文件夹路径
- fqa.json: 用户通过 add-fqa 录入的所有自定义标准答案
- vector_db/: 向量数据库完整存储目录

禁止使用系统隐藏路径、用户主目录或任何 coi_data/ 之外的位置。
"""

import json
import os
import sys
from typing import Optional


def _get_program_dir() -> str:
    """获取程序所在目录

    支持两种模式：
    - PyInstaller 打包后：使用可执行文件所在目录
    - 开发模式：使用脚本所在目录
    """
    if getattr(sys, "frozen", False):
        # PyInstaller 打包后的可执行文件
        return os.path.dirname(sys.executable)
    else:
        # 开发模式：脚本所在目录
        return os.path.dirname(os.path.abspath(__file__))


def get_data_dir() -> str:
    """获取 coi_data/ 数据目录绝对路径（程序同级）"""
    return os.path.join(_get_program_dir(), "coi_data")


def get_config_path() -> str:
    """获取 config.json 绝对路径"""
    return os.path.join(get_data_dir(), "config.json")


def get_fqa_path() -> str:
    """获取 fqa.json 绝对路径"""
    return os.path.join(get_data_dir(), "fqa.json")


def get_vector_db_path() -> str:
    """获取 vector_db/ 目录绝对路径"""
    return os.path.join(get_data_dir(), "vector_db")


def load_config() -> Optional[dict]:
    """加载配置文件

    Returns:
        配置字典，如果配置文件不存在或解析失败则返回 None
    """
    config_path = get_config_path()
    if not os.path.exists(config_path):
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def save_config(config: dict) -> None:
    """保存配置文件（自动创建父目录）

    Args:
        config: 配置字典
    """
    config_path = get_config_path()
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
