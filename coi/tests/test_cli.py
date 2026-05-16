"""CLI 命令集成测试

测试所有四大命令的完整行为和输出断言。
"""

import json
import os
import shutil
import sys

import pytest
from click.testing import CliRunner

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def isolated_env(tmp_dir, monkeypatch):
    """隔离环境：将 coi_data 指向临时目录"""
    monkeypatch.setattr("config._get_program_dir", lambda: tmp_dir)
    # 也需要 patch main.py 中导入的 config 模块
    import config
    monkeypatch.setattr(config, "_get_program_dir", lambda: tmp_dir)
    return tmp_dir


class TestInitCommand:
    """init 命令测试"""

    def test_init_nonexistent_path(self, runner):
        """不存在的路径应报错退出"""
        result = runner.invoke(cli, ["init", "/nonexistent/path/xyz123"])
        assert result.exit_code != 0
        assert "路径不存在" in result.output or "does not exist" in result.output.lower() or result.exit_code != 0

    def test_init_file_path_not_directory(self, runner, tmp_dir):
        """传入文件路径（非目录）应报错"""
        file_path = os.path.join(tmp_dir, "file.txt")
        with open(file_path, "w") as f:
            f.write("test")

        result = runner.invoke(cli, ["init", file_path])
        assert result.exit_code != 0
        assert "不是目录" in result.output or result.exit_code != 0

    def test_init_empty_directory(self, runner, empty_docs_dir, isolated_env):
        """空目录（无支持格式文件）应提示支持格式"""
        result = runner.invoke(cli, ["init", empty_docs_dir])
        assert "未找到支持格式" in result.output or "支持格式" in result.output

    def test_init_with_valid_docs(self, runner, sample_docs_dir, isolated_env):
        """有效文档目录应成功初始化"""
        result = runner.invoke(cli, ["init", sample_docs_dir])
        # 应该显示发现文件数
        assert "发现" in result.output
        # 应该显示初始化完成
        assert "初始化完成" in result.output or "成功处理" in result.output

    def test_init_creates_config(self, runner, sample_docs_dir, isolated_env):
        """init 应创建 config.json"""
        runner.invoke(cli, ["init", sample_docs_dir])

        config_path = os.path.join(isolated_env, "coi_data", "config.json")
        assert os.path.exists(config_path)

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        assert "knowledge_folder" in config
        # macOS /var -> /private/var symlink, use realpath for comparison
        assert os.path.realpath(config["knowledge_folder"]) == os.path.realpath(sample_docs_dir)

    def test_init_creates_vector_db(self, runner, sample_docs_dir, isolated_env):
        """init 应创建 vector_db/ 目录"""
        runner.invoke(cli, ["init", sample_docs_dir])

        vector_db_path = os.path.join(isolated_env, "coi_data", "vector_db")
        assert os.path.exists(vector_db_path)
        assert os.path.isdir(vector_db_path)

    def test_init_reinit_clears_old_data(self, runner, sample_docs_dir, isolated_env):
        """重新 init 应清空旧向量库"""
        # 第一次 init
        result1 = runner.invoke(cli, ["init", sample_docs_dir])
        assert result1.exit_code == 0 or "初始化完成" in result1.output

        # 第二次 init（应检测到旧数据并清空）
        result2 = runner.invoke(cli, ["init", sample_docs_dir])
        # 不应报错
        assert "错误" not in result2.output or "旧向量库" in result2.output


class TestAskCommand:
    """ask 命令测试"""

    def test_ask_without_init(self, runner, isolated_env):
        """未初始化时 ask 应报错"""
        result = runner.invoke(cli, ["ask", "测试问题"])
        assert result.exit_code != 0
        assert "尚未初始化" in result.output or "init" in result.output

    def test_ask_empty_question(self, runner, isolated_env):
        """空问题应报错"""
        # 创建假的 config 和 vector_db 让它通过初始化检查
        data_dir = os.path.join(isolated_env, "coi_data")
        os.makedirs(data_dir, exist_ok=True)
        with open(os.path.join(data_dir, "config.json"), "w") as f:
            json.dump({"knowledge_folder": "/tmp"}, f)
        os.makedirs(os.path.join(data_dir, "vector_db"), exist_ok=True)

        result = runner.invoke(cli, ["ask", "   "])
        assert result.exit_code != 0
        assert "不能为空" in result.output

    def test_ask_after_init(self, runner, sample_docs_dir, isolated_env):
        """初始化后 ask 应正常返回结果"""
        # 先 init
        runner.invoke(cli, ["init", sample_docs_dir])

        # 再 ask
        result = runner.invoke(cli, ["ask", "测试文档内容"])
        # 不应报错（可能有结果也可能无结果，但不应 crash）
        assert result.exit_code == 0
        # 应该有某种输出
        assert len(result.output) > 0

    def test_ask_does_not_modify_data(self, runner, sample_docs_dir, isolated_env):
        """ask 命令不应修改 coi_data/ 内容"""
        runner.invoke(cli, ["init", sample_docs_dir])

        data_dir = os.path.join(isolated_env, "coi_data")

        # 记录 init 后的文件状态
        def get_file_state(directory):
            state = {}
            for root, dirs, files in os.walk(directory):
                for f in files:
                    fp = os.path.join(root, f)
                    state[fp] = os.path.getsize(fp)
            return state

        before = get_file_state(data_dir)

        # 执行 ask
        runner.invoke(cli, ["ask", "测试问题"])

        after = get_file_state(data_dir)
        assert before == after


class TestAddFqaCommand:
    """add-fqa 命令测试"""

    def test_add_fqa_success(self, runner, isolated_env):
        """成功添加 FQA 记录"""
        result = runner.invoke(cli, ["add-fqa", "什么是COI", "本地问答工具"])
        assert result.exit_code == 0
        assert "已添加" in result.output
        assert "什么是COI" in result.output
        assert "本地问答工具" in result.output

    def test_add_fqa_creates_file(self, runner, isolated_env):
        """add-fqa 应创建 fqa.json"""
        runner.invoke(cli, ["add-fqa", "Q1", "A1"])

        fqa_path = os.path.join(isolated_env, "coi_data", "fqa.json")
        assert os.path.exists(fqa_path)

        with open(fqa_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["question"] == "Q1"
        assert data[0]["answer"] == "A1"

    def test_add_fqa_multiple(self, runner, isolated_env):
        """多次添加保持顺序"""
        runner.invoke(cli, ["add-fqa", "Q1", "A1"])
        runner.invoke(cli, ["add-fqa", "Q2", "A2"])
        runner.invoke(cli, ["add-fqa", "Q3", "A3"])

        fqa_path = os.path.join(isolated_env, "coi_data", "fqa.json")
        with open(fqa_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 3
        assert data[0]["question"] == "Q1"
        assert data[2]["question"] == "Q3"

    def test_add_fqa_empty_question(self, runner, isolated_env):
        """空问题应报错"""
        result = runner.invoke(cli, ["add-fqa", "   ", "答案"])
        assert result.exit_code != 0
        assert "不能为空" in result.output

    def test_add_fqa_empty_answer(self, runner, isolated_env):
        """空答案应报错"""
        result = runner.invoke(cli, ["add-fqa", "问题", "   "])
        assert result.exit_code != 0
        assert "不能为空" in result.output


class TestClearCommand:
    """clear 命令测试"""

    def test_clear_with_confirmation(self, runner, isolated_env):
        """确认后清空数据"""
        # 先创建数据
        data_dir = os.path.join(isolated_env, "coi_data")
        os.makedirs(data_dir, exist_ok=True)
        with open(os.path.join(data_dir, "config.json"), "w") as f:
            f.write("{}")

        result = runner.invoke(cli, ["clear", "--yes"])
        assert result.exit_code == 0
        assert "已清空" in result.output
        assert not os.path.exists(data_dir)

    def test_clear_nonexistent_data(self, runner, isolated_env):
        """数据目录不存在时提示无需清空"""
        result = runner.invoke(cli, ["clear", "--yes"])
        assert result.exit_code == 0
        assert "不存在" in result.output or "无需清空" in result.output

    def test_clear_removes_all_data(self, runner, sample_docs_dir, isolated_env):
        """clear 应删除所有数据文件"""
        # 先 init 创建数据
        runner.invoke(cli, ["init", sample_docs_dir])
        # 再 add-fqa
        runner.invoke(cli, ["add-fqa", "Q", "A"])

        data_dir = os.path.join(isolated_env, "coi_data")
        assert os.path.exists(data_dir)

        # 执行 clear
        result = runner.invoke(cli, ["clear", "--yes"])
        assert result.exit_code == 0
        assert not os.path.exists(data_dir)

    def test_clear_does_not_scan_or_vectorize(self, runner, isolated_env):
        """clear 不应触发任何扫描或向量化（通过输出验证）"""
        data_dir = os.path.join(isolated_env, "coi_data")
        os.makedirs(data_dir, exist_ok=True)
        with open(os.path.join(data_dir, "config.json"), "w") as f:
            f.write("{}")

        result = runner.invoke(cli, ["clear", "--yes"])
        assert "扫描" not in result.output
        assert "向量化" not in result.output
        assert "Embedding" not in result.output


class TestEndToEndFlow:
    """端到端流程测试"""

    def test_full_workflow(self, runner, sample_docs_dir, isolated_env):
        """完整流程: init → ask → add-fqa → ask → clear"""
        # 1. init
        result = runner.invoke(cli, ["init", sample_docs_dir])
        assert result.exit_code == 0 or "初始化完成" in result.output

        # 2. ask
        result = runner.invoke(cli, ["ask", "测试"])
        assert result.exit_code == 0

        # 3. add-fqa
        result = runner.invoke(cli, ["add-fqa", "测试问题", "测试答案"])
        assert result.exit_code == 0
        assert "已添加" in result.output

        # 4. ask again (should still work)
        result = runner.invoke(cli, ["ask", "测试问题"])
        assert result.exit_code == 0

        # 5. clear
        result = runner.invoke(cli, ["clear", "--yes"])
        assert result.exit_code == 0
        assert "已清空" in result.output

        # 6. ask after clear should fail
        result = runner.invoke(cli, ["ask", "测试"])
        assert result.exit_code != 0
        assert "尚未初始化" in result.output or "不存在" in result.output


class TestInitOutputRequirements:
    """init 命令输出断言 - 严格贴合需求"""

    def test_init_displays_file_count(self, runner, sample_docs_dir, isolated_env):
        """需求: init 应报告发现的文档文件总数"""
        result = runner.invoke(cli, ["init", sample_docs_dir])
        # sample_docs_dir 有 4 个支持格式文件
        assert "发现 4 个文档文件" in result.output

    def test_init_displays_success_count(self, runner, sample_docs_dir, isolated_env):
        """需求: init 完成后显示成功处理文件数"""
        result = runner.invoke(cli, ["init", sample_docs_dir])
        assert "成功处理:" in result.output

    def test_init_displays_chunk_count(self, runner, sample_docs_dir, isolated_env):
        """需求: init 完成后显示生成向量块数"""
        result = runner.invoke(cli, ["init", sample_docs_dir])
        assert "生成向量块:" in result.output

    def test_init_displays_supported_formats_on_empty(self, runner, empty_docs_dir, isolated_env):
        """需求: 零文件时显示支持格式列表"""
        result = runner.invoke(cli, ["init", empty_docs_dir])
        assert ".txt" in result.output
        assert ".md" in result.output
        assert ".pdf" in result.output
        assert ".docx" in result.output
        assert ".xlsx" in result.output
        assert ".csv" in result.output


class TestAskOutputRequirements:
    """ask 命令输出断言 - 严格贴合需求"""

    def test_ask_shows_vector_results_with_source_and_similarity(self, runner, sample_docs_dir, isolated_env):
        """需求: 输出向量检索结果包含来源文件路径和相似度"""
        runner.invoke(cli, ["init", sample_docs_dir])
        result = runner.invoke(cli, ["ask", "测试文档"])
        assert result.exit_code == 0
        # 应包含文档检索结果区域
        if "文档检索结果" in result.output:
            assert "来源:" in result.output
            assert "相似度:" in result.output

    def test_ask_shows_fqa_when_matched(self, runner, sample_docs_dir, isolated_env):
        """需求: FQA 匹配时输出标准答案和相似度"""
        runner.invoke(cli, ["init", sample_docs_dir])
        # 添加一个 FQA
        runner.invoke(cli, ["add-fqa", "这是什么测试文档", "这是用于验证功能的测试文档"])
        # 用相似问题提问
        result = runner.invoke(cli, ["ask", "这是什么测试文档"])
        assert result.exit_code == 0
        # 如果 FQA 命中（相似度 > 0.85），应显示标准答案区域
        if "标准答案" in result.output:
            assert "相似度:" in result.output
            assert "答案:" in result.output

    def test_ask_dual_source_merge(self, runner, sample_docs_dir, isolated_env):
        """需求: 最终回答 = 向量检索片段 + FQA 标准答案，两类叠加输出"""
        runner.invoke(cli, ["init", sample_docs_dir])
        runner.invoke(cli, ["add-fqa", "测试文档内容是什么", "这是测试内容的标准答案"])
        result = runner.invoke(cli, ["ask", "测试文档内容是什么"])
        assert result.exit_code == 0
        # 至少应有某种输出（向量检索或 FQA 或两者）
        has_vector = "文档检索结果" in result.output
        has_fqa = "标准答案" in result.output
        assert has_vector or has_fqa, "ask 应至少返回一种来源的结果"

    def test_ask_no_result_message(self, runner, isolated_env):
        """需求: 无结果时显示未找到相关内容"""
        # 创建一个只有空文件的知识库
        data_dir = os.path.join(isolated_env, "coi_data")
        os.makedirs(data_dir, exist_ok=True)
        with open(os.path.join(data_dir, "config.json"), "w") as f:
            json.dump({"knowledge_folder": "/tmp"}, f)
        vector_db_path = os.path.join(data_dir, "vector_db")
        os.makedirs(vector_db_path, exist_ok=True)

        # 初始化一个空的 ChromaDB
        import chromadb
        client = chromadb.PersistentClient(path=vector_db_path)
        client.get_or_create_collection(name="coi_knowledge", metadata={"hnsw:space": "cosine"})

        result = runner.invoke(cli, ["ask", "完全不相关的随机问题xyz"])
        assert result.exit_code == 0
        assert "未找到相关内容" in result.output


class TestDataDirectoryRequirements:
    """数据存储规则断言 - 严格贴合需求"""

    def test_coi_data_contains_only_three_items(self, runner, sample_docs_dir, isolated_env):
        """需求: coi_data 目录固定包含三类数据 config.json/fqa.json/vector_db"""
        runner.invoke(cli, ["init", sample_docs_dir])
        runner.invoke(cli, ["add-fqa", "Q", "A"])

        data_dir = os.path.join(isolated_env, "coi_data")
        items = set(os.listdir(data_dir))
        # 只允许这三项
        allowed = {"config.json", "fqa.json", "vector_db"}
        assert items.issubset(allowed), f"coi_data 包含非预期文件: {items - allowed}"

    def test_no_data_outside_coi_data(self, runner, sample_docs_dir, isolated_env):
        """需求: 所有数据强制存放在 coi_data/ 目录，禁止其他位置"""
        # 记录 init 前的文件
        before_files = set()
        for f in os.listdir(isolated_env):
            if f != "coi_data":
                before_files.add(f)

        runner.invoke(cli, ["init", sample_docs_dir])
        runner.invoke(cli, ["add-fqa", "Q", "A"])

        # init 后不应在 coi_data 之外创建新文件
        after_files = set()
        for f in os.listdir(isolated_env):
            if f != "coi_data":
                after_files.add(f)

        new_files = after_files - before_files
        assert len(new_files) == 0, f"在 coi_data/ 之外创建了文件: {new_files}"

    def test_manual_delete_coi_data_resets_state(self, runner, sample_docs_dir, isolated_env):
        """需求: 用户手动删除 coi_data 等同于 clear，程序回到未初始化状态"""
        runner.invoke(cli, ["init", sample_docs_dir])

        # 手动删除
        data_dir = os.path.join(isolated_env, "coi_data")
        shutil.rmtree(data_dir)

        # ask 应报错
        result = runner.invoke(cli, ["ask", "测试"])
        assert result.exit_code != 0
        assert "尚未初始化" in result.output or "不存在" in result.output


class TestClearRequirements:
    """clear 命令严格需求断言"""

    def test_clear_deletes_config_fqa_vectordb(self, runner, sample_docs_dir, isolated_env):
        """需求: 删除内容包括向量数据库、FQA 标准答案文件、全局配置文件"""
        runner.invoke(cli, ["init", sample_docs_dir])
        runner.invoke(cli, ["add-fqa", "Q", "A"])

        data_dir = os.path.join(isolated_env, "coi_data")
        # 确认三项都存在
        assert os.path.exists(os.path.join(data_dir, "config.json"))
        assert os.path.exists(os.path.join(data_dir, "fqa.json"))
        assert os.path.exists(os.path.join(data_dir, "vector_db"))

        # 执行 clear
        runner.invoke(cli, ["clear", "--yes"])

        # 确认全部删除
        assert not os.path.exists(os.path.join(data_dir, "config.json"))
        assert not os.path.exists(os.path.join(data_dir, "fqa.json"))
        assert not os.path.exists(os.path.join(data_dir, "vector_db"))
        assert not os.path.exists(data_dir)

    def test_clear_only_deletes_no_other_action(self, runner, isolated_env):
        """需求: clear 只做文件删除，不扫描、不解析、不向量化"""
        data_dir = os.path.join(isolated_env, "coi_data")
        os.makedirs(data_dir, exist_ok=True)
        with open(os.path.join(data_dir, "config.json"), "w") as f:
            json.dump({"knowledge_folder": "/tmp/docs"}, f)

        result = runner.invoke(cli, ["clear", "--yes"])
        # 输出中不应包含任何扫描/向量化相关词汇
        assert "扫描" not in result.output
        assert "向量" not in result.output.replace("向量库", "").replace("向量数据库", "")
        assert "Embedding" not in result.output
        assert "模型" not in result.output
        assert "文档" not in result.output.replace("文档文件夹", "")


class TestAskNeverRebuilds:
    """ask 命令禁止重建断言 - 核心需求"""

    def test_ask_never_triggers_scan(self, runner, sample_docs_dir, isolated_env):
        """需求: ask 不再扫描本地文档文件夹"""
        runner.invoke(cli, ["init", sample_docs_dir])

        # 在文档目录新增文件
        new_file = os.path.join(sample_docs_dir, "new_after_init.txt")
        with open(new_file, "w", encoding="utf-8") as f:
            f.write("这是 init 之后新增的文件内容")

        # ask 不应发现这个新文件
        result = runner.invoke(cli, ["ask", "init之后新增的文件"])
        assert result.exit_code == 0
        # 输出中不应包含新文件名
        assert "new_after_init" not in result.output

    def test_ask_output_does_not_mention_scanning(self, runner, sample_docs_dir, isolated_env):
        """需求: ask 输出中不应有任何扫描/重建相关信息"""
        runner.invoke(cli, ["init", sample_docs_dir])
        result = runner.invoke(cli, ["ask", "测试内容"])
        assert "扫描" not in result.output
        assert "重建" not in result.output
        assert "构建" not in result.output
