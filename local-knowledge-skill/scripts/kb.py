#!/usr/bin/env python3
"""CLI 入口与命令定义

使用 Click 框架定义 CLI 命令组，支持 init、scan、query、rebuild、fqa 子命令。
所有模块根据全局选项初始化，通过 Click context 传递配置。
支持通过 ~/.kb_config.json 持久化用户配置（知识库路径等）。
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import click

from chunker import TextChunker
from embedding import EmbeddingEngine
from fqa import FQAManager
from models import CLIConfig
from query import QueryEngine
from scanner import FileScanner
from store import VectorStore
from sync import SyncManager

# 用户配置文件路径
CONFIG_FILE = os.path.expanduser("~/.kb_config.json")


def _load_user_config() -> dict:
    """加载用户持久化配置"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_user_config(config: dict) -> None:
    """保存用户持久化配置"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def _get_folder(folder_option: str = None) -> str:
    """获取知识库文件夹路径：优先使用命令行参数，其次读取配置文件。

    Args:
        folder_option: 命令行传入的 --folder 值（可能为 None）

    Returns:
        知识库文件夹的绝对路径

    Raises:
        click.UsageError: 既没有传参也没有配置时
    """
    if folder_option:
        return os.path.abspath(folder_option)

    user_config = _load_user_config()
    if "knowledge_folder" in user_config:
        return user_config["knowledge_folder"]

    raise click.UsageError(
        "未指定知识库文件夹路径。请先运行 'kb.py init --folder <路径>' 初始化，"
        "或使用 --folder 参数指定路径。"
    )


@click.group()
@click.option(
    "--chroma-path",
    envvar="CHROMA_PATH",
    default="./chroma_data",
    help="ChromaDB 本地持久化路径",
)
@click.option(
    "--collection",
    envvar="CHROMA_COLLECTION",
    default="knowledge_base",
    help="ChromaDB collection 名称",
)
@click.option(
    "--fqa-path",
    envvar="FQA_PATH",
    default="./fqa.txt",
    help="FQA 问答对文件路径",
)
@click.option(
    "--model",
    envvar="EMBEDDING_MODEL",
    default="paraphrase-multilingual-MiniLM-L12-v2",
    help="Embedding 模型名称",
)
@click.option(
    "--chunk-size",
    envvar="CHUNK_SIZE",
    default=512,
    type=int,
    help="切块大小（token）",
)
@click.option(
    "--chunk-overlap",
    envvar="CHUNK_OVERLAP",
    default=64,
    type=int,
    help="相邻块重叠大小（token）",
)
@click.option(
    "--fqa-threshold",
    envvar="FQA_THRESHOLD",
    default=0.85,
    type=float,
    help="FQA 匹配相似度阈值",
)
@click.option(
    "--top-k",
    envvar="TOP_K",
    default=5,
    type=int,
    help="向量检索返回数量",
)
@click.pass_context
def cli(ctx, chroma_path, collection, fqa_path, model, chunk_size, chunk_overlap, fqa_threshold, top_k):
    """本地知识库 RAG CLI 工具 - 支持多格式文档向量化索引与语义检索"""
    ctx.ensure_object(dict)
    ctx.obj["config"] = CLIConfig(
        chroma_path=chroma_path,
        chroma_collection=collection,
        fqa_file_path=fqa_path,
        embedding_model=model,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        fqa_threshold=fqa_threshold,
        top_k=top_k,
    )


def _init_modules(config: CLIConfig):
    """根据配置初始化所有模块实例。

    Args:
        config: CLI 配置对象

    Returns:
        包含所有模块实例的字典
    """
    embedding_engine = EmbeddingEngine(model_name=config.embedding_model)
    vector_store = VectorStore(
        chroma_path=config.chroma_path,
        collection_name=config.chroma_collection,
    )
    vector_store.initialize()

    text_chunker = TextChunker(
        tokenizer=embedding_engine.get_tokenizer(),
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
    )
    fqa_manager = FQAManager(fqa_file_path=config.fqa_file_path)
    query_engine = QueryEngine(
        embedding_engine=embedding_engine,
        vector_store=vector_store,
        fqa_manager=fqa_manager,
        fqa_threshold=config.fqa_threshold,
    )
    file_scanner = FileScanner()
    sync_manager = SyncManager(
        file_scanner=file_scanner,
        text_chunker=text_chunker,
        embedding_engine=embedding_engine,
        vector_store=vector_store,
    )

    return {
        "embedding_engine": embedding_engine,
        "vector_store": vector_store,
        "text_chunker": text_chunker,
        "fqa_manager": fqa_manager,
        "query_engine": query_engine,
        "file_scanner": file_scanner,
        "sync_manager": sync_manager,
    }


@cli.command()
@click.option("--folder", required=True, help="知识库文件夹路径")
@click.pass_context
def init(ctx, folder):
    """初始化知识库配置，记住文件夹路径。后续命令无需再指定 --folder。"""
    folder_path = os.path.abspath(folder)

    if not os.path.exists(folder_path):
        click.echo(f"错误: 路径不存在: {folder_path}", err=True)
        ctx.exit(1)
        return

    if not os.path.isdir(folder_path):
        click.echo(f"错误: 路径不是目录: {folder_path}", err=True)
        ctx.exit(1)
        return

    user_config = _load_user_config()
    user_config["knowledge_folder"] = folder_path
    _save_user_config(user_config)

    click.echo(f"知识库配置已保存：")
    click.echo(f"  文件夹路径: {folder_path}")
    click.echo(f"  配置文件: {CONFIG_FILE}")
    click.echo(f"\n后续使用 scan/query/rebuild 时无需再指定 --folder。")


@cli.command()
@click.option("--folder", default=None, help="知识库文件夹路径（已初始化时可省略）")
@click.pass_context
def scan(ctx, folder):
    """扫描知识库文件夹，检测文件变更并增量更新向量索引。"""
    config = ctx.obj["config"]

    try:
        folder_path = _get_folder(folder)
    except click.UsageError as e:
        click.echo(f"错误: {e}", err=True)
        ctx.exit(1)
        return

    try:
        modules = _init_modules(config)
    except Exception as e:
        click.echo(f"错误: 初始化失败 - {e}", err=True)
        ctx.exit(1)
        return

    sync_manager = modules["sync_manager"]

    try:
        stats = sync_manager.incremental_sync(folder_path)
    except (FileNotFoundError, NotADirectoryError) as e:
        click.echo(f"错误: {e}", err=True)
        ctx.exit(1)
        return

    click.echo("扫描完成：")
    click.echo(f"  新增文件: {stats['added']}")
    click.echo(f"  修改文件: {stats['modified']}")
    click.echo(f"  删除文件: {stats['deleted']}")
    click.echo(f"  未变更: {stats['unchanged']}")

    if stats["failed"] > 0:
        click.echo(f"  失败文件: {stats['failed']}")
        for error in stats["errors"]:
            click.echo(f"    - {error['path']}: {error['reason']}")


@cli.command()
@click.argument("question")
@click.pass_context
def query(ctx, question):
    """对知识库进行语义查询。"""
    config = ctx.obj["config"]

    try:
        modules = _init_modules(config)
    except Exception as e:
        click.echo(f"错误: 初始化失败 - {e}", err=True)
        ctx.exit(1)
        return

    query_engine = modules["query_engine"]

    try:
        result = query_engine.query(question, top_k=config.top_k)
    except ValueError as e:
        click.echo(f"错误: {e}", err=True)
        ctx.exit(1)
        return

    if result.source == "fqa":
        click.echo(f"[FQA 匹配] 相似度: {result.similarity:.2f}")
        click.echo(f"答案: {result.answer}")
    else:
        if not result.chunks:
            click.echo(result.answer)
        else:
            click.echo(f"[向量检索] 找到 {len(result.chunks)} 条相关结果：")
            click.echo()
            for i, chunk in enumerate(result.chunks, 1):
                similarity = 1.0 - chunk.distance
                click.echo(f"{i}. [来源: {chunk.metadata.file_path}] (相似度: {similarity:.2f})")
                # 截取前 100 字符作为预览
                preview = chunk.text[:100].replace("\n", " ")
                if len(chunk.text) > 100:
                    preview += "..."
                click.echo(f"   {preview}")
                click.echo()


@cli.command()
@click.option("--folder", default=None, help="知识库文件夹路径（已初始化时可省略）")
@click.pass_context
def rebuild(ctx, folder):
    """删除所有现有向量记录，重新扫描并索引知识库文件夹中的所有文件。"""
    config = ctx.obj["config"]

    try:
        folder_path = _get_folder(folder)
    except click.UsageError as e:
        click.echo(f"错误: {e}", err=True)
        ctx.exit(1)
        return

    try:
        modules = _init_modules(config)
    except Exception as e:
        click.echo(f"错误: 初始化失败 - {e}", err=True)
        ctx.exit(1)
        return

    vector_store = modules["vector_store"]
    sync_manager = modules["sync_manager"]

    record_count = vector_store.get_record_count()
    click.echo(f"当前知识库包含 {record_count} 条向量记录。")

    if not click.confirm("确认要删除所有记录并重建吗？"):
        click.echo("操作已取消")
        return

    try:
        stats = sync_manager.full_rebuild(folder_path)
    except (FileNotFoundError, NotADirectoryError) as e:
        click.echo(f"错误: {e}", err=True)
        ctx.exit(1)
        return

    click.echo("\n重建完成：")
    click.echo(f"  成功处理文件: {stats['added']}")
    click.echo(f"  生成向量块: {stats['total_chunks']}")
    click.echo(f"  失败文件: {stats['failed']}")

    if stats["failed"] > 0:
        for error in stats["errors"]:
            click.echo(f"    - {error['path']}: {error['reason']}")


@cli.command()
@click.option("--add", default=None, help='添加问答对，格式为"问题=答案"')
@click.option("--list", "list_all", is_flag=True, default=False, help="列出所有 FQA 记录")
@click.pass_context
def fqa(ctx, add, list_all):
    """管理 FQA 问答对：添加或列出人工纠错记录。"""
    config = ctx.obj["config"]
    fqa_manager = FQAManager(fqa_file_path=config.fqa_file_path)

    if list_all:
        try:
            pairs = fqa_manager.load()
        except RuntimeError as e:
            click.echo(f"错误: {e}", err=True)
            ctx.exit(1)
            return

        if not pairs:
            click.echo("FQA 记录为空，尚未添加任何人工纠错答案。")
            return

        click.echo(f"共 {len(pairs)} 条 FQA 记录：")
        click.echo()
        for i, pair in enumerate(pairs, 1):
            click.echo(f"{i}. 问: {pair.question}")
            click.echo(f"   答: {pair.answer}")
            click.echo()
        return

    if not add:
        click.echo("错误: 请使用 --add 添加记录或 --list 列出所有记录", err=True)
        ctx.exit(1)
        return

    if "=" not in add:
        click.echo('错误: 格式不正确，请使用"问题=答案"格式', err=True)
        ctx.exit(1)
        return

    question, answer = add.split("=", 1)

    if not question.strip():
        click.echo("错误: 问题不能为空", err=True)
        ctx.exit(1)
        return

    if not answer.strip():
        click.echo("错误: 答案不能为空", err=True)
        ctx.exit(1)
        return

    try:
        fqa_manager.append(question, answer)
    except RuntimeError as e:
        click.echo(f"错误: {e}", err=True)
        ctx.exit(1)
        return

    click.echo("已添加 FQA 记录：")
    click.echo(f"  问题: {question}")
    click.echo(f"  答案: {answer}")


if __name__ == "__main__":
    cli()
