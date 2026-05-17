#!/usr/bin/env python3
"""COI（我问你答）- 本地离线文档问答工具

纯本地独立运行，不调用任何外部大模型、不上网、无网络请求。
所有数据本地化存储于程序同级 coi_data/ 目录。

四大核心命令：
- init: 初始化（唯一建库入口，全量扫描+一次性构建向量库）
- ask: 提问查询（直接复用缓存向量库，不扫描不重建）
- add-fqa: 补充标准答案
- clear: 一键清空所有数据
"""

import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import click

from config import (
    get_data_dir,
    get_config_path,
    get_fqa_path,
    get_vector_db_path,
    load_config,
    save_config,
)
from models import ChunkMetadata


@click.group(invoke_without_command=True)
@click.version_option(version="1.0.0", prog_name="COI（我问你答）")
@click.pass_context
def cli(ctx):
    """COI（我问你答）- 本地离线文档问答工具

    纯本地独立运行，不调用任何外部大模型、不上网、无网络请求。
    所有数据存储于程序同级 coi_data/ 目录，结构透明可管理。

    \b
    支持文档格式：TXT、MD、PDF、DOCX、XLSX、CSV

    \b
    使用流程：
      1. coi init <文档目录>     首次初始化，全量构建向量库
      2. coi ask "你的问题"      提问（秒级响应，不重建）
      3. coi add-fqa "问题" "答案"  补充标准答案
      4. coi clear               清空所有数据

    \b
    示例：
      coi init ~/Documents/公司文档
      coi ask "报销流程是什么"
      coi add-fqa "报销期限" "费用发生后30天内提交"
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.argument("folder", type=click.Path(resolve_path=True))
def init(folder):
    """初始化知识库：指定文档文件夹，一次性全量构建向量库。

    FOLDER: 本地文档文件夹路径

    这是程序唯一可以新建/重建向量库的命令。
    """
    # 1. 验证路径
    folder_path = os.path.abspath(folder)

    if not os.path.exists(folder_path):
        click.echo(f"[COI] 错误: 路径不存在: {folder_path}", err=True)
        sys.exit(1)

    if not os.path.isdir(folder_path):
        click.echo(f"[COI] 错误: 路径不是目录: {folder_path}", err=True)
        sys.exit(1)

    click.echo(f"[COI] 正在初始化知识库...")
    click.echo(f"  文档目录: {folder_path}")

    # 2. 保存配置（自动创建 coi_data/）
    data_dir = get_data_dir()
    os.makedirs(data_dir, exist_ok=True)
    save_config({"knowledge_folder": folder_path})
    click.echo(f"  数据目录: {data_dir}")

    # 3. 加载 Embedding 模型
    click.echo(f"\n[COI] 正在加载 Embedding 模型...")
    try:
        from embedding import EmbeddingEngine

        embedding_engine = EmbeddingEngine()
        embedding_engine._ensure_loaded()
    except RuntimeError as e:
        click.echo(f"[COI] 错误: {e}", err=True)
        sys.exit(1)

    # 4. 初始化向量存储
    from store import VectorStore

    vector_db_path = get_vector_db_path()
    vector_store = VectorStore(chroma_path=vector_db_path)
    vector_store.initialize()

    # 清空旧数据
    old_count = vector_store.get_record_count()
    if old_count > 0:
        click.echo(f"  检测到旧向量库（{old_count} 条记录），正在清空...")
        vector_store.delete_all()

    # 5. 扫描文档
    click.echo(f"\n[COI] 正在扫描文档...")
    from scanner import FileScanner

    scanner = FileScanner()
    try:
        scan_result = scanner.scan(folder_path)
    except (FileNotFoundError, NotADirectoryError) as e:
        click.echo(f"[COI] 错误: {e}", err=True)
        sys.exit(1)

    total_files = len(scan_result.changes)
    if total_files == 0:
        click.echo("  未找到支持格式的文档文件。")
        click.echo("  支持格式: .txt, .md, .pdf, .docx, .xlsx, .csv")
        return

    click.echo(f"  发现 {total_files} 个文档文件")

    # 6. 全量向量化
    click.echo(f"\n[COI] 正在构建向量库...")
    from chunker import TextChunker

    text_chunker = TextChunker(
        tokenizer=embedding_engine.get_tokenizer(),
        chunk_size=512,
        chunk_overlap=128,
    )

    success_count = 0
    chunk_count = 0
    failed_files = []

    for i, change in enumerate(scan_result.changes, 1):
        click.echo(f"  [{i}/{total_files}] {change.file_path}", nl=False)

        try:
            # 提取文本
            text = text_chunker.extract_text(change.absolute_path)
            if text is None:
                click.echo(" - 跳过（内容为空）")
                failed_files.append({"path": change.file_path, "reason": "内容为空"})
                continue

            # 切块
            chunks = text_chunker.chunk(text)
            if not chunks:
                click.echo(" - 跳过（切块为空）")
                failed_files.append({"path": change.file_path, "reason": "切块为空"})
                continue

            # 计算文件哈希
            sha256 = hashlib.sha256()
            with open(change.absolute_path, "rb") as f:
                for block in iter(lambda: f.read(8192), b""):
                    sha256.update(block)
            file_hash = sha256.hexdigest()

            # 向量化并存储
            file_chunks = 0
            for chunk in chunks:
                vector = embedding_engine.embed(chunk.text)
                metadata = ChunkMetadata(
                    file_path=change.file_path,
                    file_hash=file_hash,
                    chunk_index=chunk.index,
                    last_modified=change.last_modified,
                )
                record_id = f"{change.file_path}::{chunk.index}"
                vector_store.upsert(record_id, vector, chunk.text, metadata)
                file_chunks += 1

            click.echo(f" - {file_chunks} 个文本块")
            success_count += 1
            chunk_count += file_chunks

        except Exception as e:
            click.echo(f" - 失败: {e}")
            failed_files.append({"path": change.file_path, "reason": str(e)})

    # 7. 输出统计摘要
    click.echo(f"\n[COI] 初始化完成！")
    click.echo(f"  成功处理: {success_count} 个文件")
    click.echo(f"  生成向量块: {chunk_count} 条")
    if failed_files:
        click.echo(f"  失败文件: {len(failed_files)} 个")
        for f in failed_files:
            click.echo(f"    - {f['path']}: {f['reason']}")

    if scan_result.errors:
        click.echo(f"  扫描错误: {len(scan_result.errors)} 个")
        for err in scan_result.errors:
            click.echo(f"    - {err['path']}: {err['reason']}")

    click.echo(f"\n  提示: 使用 'coi ask \"你的问题\"' 开始提问")


@cli.command()
@click.argument("question")
def ask(question):
    """提问查询：基于已构建的向量库 + FQA 标准答案库联合检索。

    QUESTION: 自然语言问题

    直接读取本地缓存，不扫描文档、不重建向量库。
    """
    # 验证问题非空
    if not question or not question.strip():
        click.echo("[COI] 错误: 问题不能为空。", err=True)
        sys.exit(1)

    # 验证已初始化
    config = load_config()
    if config is None:
        click.echo("[COI] 错误: 尚未初始化知识库。", err=True)
        click.echo("  请先执行: coi init <文档文件夹路径>", err=True)
        sys.exit(1)

    vector_db_path = get_vector_db_path()
    if not os.path.exists(vector_db_path):
        click.echo("[COI] 错误: 向量库不存在，请先执行 init 初始化。", err=True)
        sys.exit(1)

    # 加载模块
    try:
        from embedding import EmbeddingEngine

        embedding_engine = EmbeddingEngine()
    except Exception as e:
        click.echo(f"[COI] 错误: 模型加载失败 - {e}", err=True)
        sys.exit(1)

    from store import VectorStore
    from fqa import FQAManager
    from query import QueryEngine

    vector_store = VectorStore(chroma_path=vector_db_path)
    vector_store.initialize()

    fqa_path = get_fqa_path()
    fqa_manager = FQAManager(fqa_file_path=fqa_path)

    query_engine = QueryEngine(
        embedding_engine=embedding_engine,
        vector_store=vector_store,
        fqa_manager=fqa_manager,
        fqa_threshold=0.85,
    )

    # 执行查询
    try:
        result = query_engine.query(question, top_k=5)
    except ValueError as e:
        click.echo(f"[COI] 错误: {e}", err=True)
        sys.exit(1)
    except RuntimeError as e:
        click.echo(f"[COI] 错误: {e}", err=True)
        sys.exit(1)

    # 输出结果：双源合并
    click.echo()

    has_output = False

    # FQA 部分
    if result.fqa_answer:
        has_output = True
        click.echo("═══ 标准答案（FQA）═══")
        click.echo(f"  相似度: {result.fqa_similarity:.2f}")
        click.echo(f"  答案: {result.fqa_answer}")
        click.echo()

    # 向量检索部分
    if result.vector_chunks:
        has_output = True
        click.echo("═══ 文档检索结果 ═══")
        for i, chunk in enumerate(result.vector_chunks, 1):
            similarity = 1.0 - chunk.distance
            click.echo(f"  [{i}] 来源: {chunk.metadata.file_path} (相似度: {similarity:.2f})")
            preview = chunk.text[:500].replace("\n", " ")
            if len(chunk.text) > 500:
                preview += "..."
            click.echo(f"      {preview}")
            click.echo()

    # 无结果
    if not has_output:
        click.echo("[COI] 未找到相关内容。")
        click.echo("  提示: 可能需要重新执行 'coi init' 更新向量库。")


@cli.command("add-fqa")
@click.argument("question")
@click.argument("answer")
def add_fqa(question, answer):
    """补充标准答案：手动录入问题和对应标准答案。

    QUESTION: 问题内容
    ANSWER: 标准答案内容
    """
    # 验证非空
    if not question or not question.strip():
        click.echo("[COI] 错误: 问题不能为空。", err=True)
        sys.exit(1)

    if not answer or not answer.strip():
        click.echo("[COI] 错误: 答案不能为空。", err=True)
        sys.exit(1)

    # 确保 coi_data/ 存在
    data_dir = get_data_dir()
    os.makedirs(data_dir, exist_ok=True)

    # 追加记录
    from fqa import FQAManager

    fqa_path = get_fqa_path()
    fqa_manager = FQAManager(fqa_file_path=fqa_path)

    try:
        fqa_manager.append(question, answer)
    except RuntimeError as e:
        click.echo(f"[COI] 错误: {e}", err=True)
        sys.exit(1)

    click.echo("[COI] 标准答案已添加：")
    click.echo(f"  问题: {question}")
    click.echo(f"  答案: {answer}")


@cli.command()
@click.confirmation_option(prompt="确认要清空所有 COI 数据吗？此操作不可恢复")
def clear():
    """一键清空：删除所有程序生成数据，恢复纯净初始状态。

    删除内容：向量数据库、FQA 标准答案文件、全局配置文件。
    只做文件删除，不扫描、不解析、不执行任何向量化操作。
    """
    import shutil

    data_dir = get_data_dir()

    if not os.path.exists(data_dir):
        click.echo("[COI] 数据目录不存在，无需清空。")
        return

    try:
        shutil.rmtree(data_dir)
        click.echo("[COI] 已清空所有数据：")
        click.echo(f"  已删除: {data_dir}")
        click.echo("  程序已恢复初始状态。")
        click.echo("\n  如需重新使用，请执行: coi init <文档文件夹路径>")
    except OSError as e:
        click.echo(f"[COI] 错误: 清空失败 - {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
