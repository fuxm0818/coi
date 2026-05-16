"""config.py 单元测试"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import save_config, load_config, get_data_dir, get_config_path, get_fqa_path, get_vector_db_path


class TestConfigPaths:
    """测试路径函数"""

    def test_get_data_dir_returns_coi_data(self):
        data_dir = get_data_dir()
        assert data_dir.endswith("coi_data")

    def test_get_config_path_in_data_dir(self):
        config_path = get_config_path()
        assert config_path.endswith(os.path.join("coi_data", "config.json"))

    def test_get_fqa_path_in_data_dir(self):
        fqa_path = get_fqa_path()
        assert fqa_path.endswith(os.path.join("coi_data", "fqa.json"))

    def test_get_vector_db_path_in_data_dir(self):
        vector_db_path = get_vector_db_path()
        assert vector_db_path.endswith(os.path.join("coi_data", "vector_db"))

    def test_all_paths_under_same_parent(self):
        """所有路径必须在同一个 coi_data/ 目录下"""
        data_dir = get_data_dir()
        assert get_config_path().startswith(data_dir)
        assert get_fqa_path().startswith(data_dir)
        assert get_vector_db_path().startswith(data_dir)


class TestSaveLoadConfig:
    """测试配置保存和加载"""

    def test_save_and_load(self, tmp_dir, monkeypatch):
        """保存后能正确加载"""
        monkeypatch.setattr("config._get_program_dir", lambda: tmp_dir)

        save_config({"knowledge_folder": "/tmp/docs"})
        result = load_config()
        assert result == {"knowledge_folder": "/tmp/docs"}

    def test_load_nonexistent_returns_none(self, tmp_dir, monkeypatch):
        """配置文件不存在时返回 None"""
        monkeypatch.setattr("config._get_program_dir", lambda: tmp_dir)
        result = load_config()
        assert result is None

    def test_overwrite_on_second_save(self, tmp_dir, monkeypatch):
        """第二次保存覆盖第一次"""
        monkeypatch.setattr("config._get_program_dir", lambda: tmp_dir)

        save_config({"knowledge_folder": "/path/a"})
        save_config({"knowledge_folder": "/path/b"})
        result = load_config()
        assert result == {"knowledge_folder": "/path/b"}

    def test_auto_creates_directory(self, tmp_dir, monkeypatch):
        """保存时自动创建 coi_data/ 目录"""
        monkeypatch.setattr("config._get_program_dir", lambda: tmp_dir)

        data_dir = os.path.join(tmp_dir, "coi_data")
        assert not os.path.exists(data_dir)

        save_config({"knowledge_folder": "/tmp/test"})
        assert os.path.exists(data_dir)

    def test_load_corrupted_json_returns_none(self, tmp_dir, monkeypatch):
        """JSON 损坏时返回 None"""
        monkeypatch.setattr("config._get_program_dir", lambda: tmp_dir)

        config_path = os.path.join(tmp_dir, "coi_data", "config.json")
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w") as f:
            f.write("{invalid json")

        result = load_config()
        assert result is None
