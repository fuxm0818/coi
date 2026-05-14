# Implementation Plan: 本地知识库系统 (Local Knowledge Base)

## Overview

基于 Python 实现本地 RAG CLI 工具，采用一次性进程模式运行。使用 Click 作为 CLI 框架，ChromaDB PersistentClient 进行本地向量持久化存储，sentence-transformers 加载多语言嵌入模型，支持多格式文档解析、增量同步和 FQA 优先级查询策略。

## Tasks

- [x] 1. 搭建项目结构与核心接口
  - [x] 1.1 初始化 Python 项目结构与依赖配置
    - 创建 `src/` 目录结构：`src/__init__.py`、`src/cli.py`、`src/scanner.py`、`src/chunker.py`、`src/embedding.py`、`src/store.py`、`src/fqa.py`、`src/query.py`、`src/sync.py`
    - 创建 `tests/` 目录结构：`tests/__init__.py`、`tests/conftest.py`
    - 创建 `pyproject.toml`，声明依赖：click、chromadb、sentence-transformers、python-docx、openpyxl、PyPDF2、markdown-it-py、pytest、hypothesis
    - 创建 `README.md` 说明项目用途和使用方式
    - _Requirements: 1.1, 1.4, 1.5_

  - [x] 1.2 定义核心数据模型与类型
    - 创建 `src/models.py`，定义 `FileChange`（dataclass，含 file_path、absolute_path、status、last_modified）
    - 定义 `ScanResult`（dataclass，含 changes、unchanged、errors）
    - 定义 `Chunk`（dataclass，含 text、index、token_count）
    - 定义 `ChunkMetadata`（dataclass，含 file_path、file_hash、chunk_index、last_modified）
    - 定义 `SearchResult`（dataclass，含 text、metadata、distance）
    - 定义 `FQAPair`（dataclass，含 question、answer）
    - 定义 `QueryResult`（dataclass，含 source、answer、chunks、similarity）
    - 定义 `CLIConfig`（dataclass，含所有配置项及默认值）
    - _Requirements: 1.1, 2.1, 3.6, 4.3, 4.4, 7.2, 8.1_

- [x] 2. 实现文件扫描与变更检测模块
  - [x] 2.1 实现 FileScanner 类
    - 在 `src/scanner.py` 中实现 `FileScanner` 类
    - 实现 `scan(folder_path, existing_records)` 方法：递归遍历文件夹，对比向量库记录，生成变更清单
    - 支持的扩展名集合：`.txt`、`.md`、`.doc`、`.docx`、`.xls`、`.xlsx`、`.pdf`
    - 实现变更检测逻辑：新文件标记为 `added`，修改时间不一致标记为 `modified`，向量库有记录但文件不存在标记为 `deleted`
    - 路径不存在时抛出明确错误信息
    - 跳过不支持的文件扩展名
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [ ]* 2.2 编写 FileScanner 单元测试
    - 在 `tests/test_scanner.py` 中编写测试
    - 测试新增文件检测、修改文件检测、删除文件检测
    - 测试不支持扩展名的跳过逻辑
    - 测试路径不存在时的错误处理
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

- [x] 3. 实现文本提取与切块模块
  - [x] 3.1 实现多格式文本提取
    - 在 `src/chunker.py` 中实现 `TextChunker` 类
    - 实现 `extract_text(file_path)` 方法，根据文件扩展名分发到对应提取器
    - TXT：直接 UTF-8 读取
    - Markdown：使用 markdown-it-py 解析后提取纯文本，移除语法标记保留结构换行
    - Word (.doc/.docx)：使用 python-docx 按段落顺序提取
    - Excel (.xls/.xlsx)：使用 openpyxl 按工作表→行→单元格拼接，制表符分隔单元格，换行分隔行
    - PDF：使用 PyPDF2 按页码顺序提取文本
    - 空文件或提取后为空白时记录警告并跳过
    - 文件损坏或编码错误时记录错误日志并跳过
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.9, 3.10_

  - [x] 3.2 实现基于 token 的文本切块逻辑
    - 在 `TextChunker` 中实现 `chunk(text)` 方法
    - 使用 sentence-transformers tokenizer 进行 token 计数
    - 按 512 token 切分，相邻块保留 64 token 重叠
    - 实现 `find_sentence_boundary(tokens, max_pos)` 方法，以中文标点（。！？；\n）为优先分割边界
    - 最后一块不足 64 token 时合并到前一块
    - 中英文混合内容统一处理，不因语言切换强制断开
    - _Requirements: 3.6, 3.7, 3.8, 9.1, 9.4_

  - [ ]* 3.3 编写 TextChunker 单元测试
    - 在 `tests/test_chunker.py` 中编写测试
    - 测试各格式文件的文本提取
    - 测试切块大小和重叠逻辑
    - 测试中文句子边界切分
    - 测试空文件和损坏文件的处理
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 9.1_

- [x] 4. 实现向量化引擎模块
  - [x] 4.1 实现 EmbeddingEngine 类
    - 在 `src/embedding.py` 中实现 `EmbeddingEngine` 类
    - 使用 sentence-transformers 加载 `paraphrase-multilingual-MiniLM-L12-v2` 模型（384 维）
    - 实现延迟加载：首次调用时才加载模型
    - 实现 `embed(text)` 方法：单条文本向量化，返回 384 维向量
    - 实现 `embed_batch(texts)` 方法：批量文本向量化
    - 实现 `get_tokenizer()` 方法：返回 tokenizer 实例供 TextChunker 使用
    - 确保纯本地运行，不依赖任何在线服务
    - _Requirements: 4.1, 4.2, 9.2_

  - [ ]* 4.2 编写 EmbeddingEngine 单元测试
    - 在 `tests/test_embedding.py` 中编写测试
    - 测试向量维度为 384
    - 测试中文文本向量化
    - 测试同义词相似度（如"购买"与"买入"余弦相似度 >= 0.7）
    - _Requirements: 4.1, 4.2, 9.2, 9.3_

- [x] 5. Checkpoint - 确保核心模块测试通过
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. 实现向量存储模块
  - [x] 6.1 实现 VectorStore 类
    - 在 `src/store.py` 中实现 `VectorStore` 类
    - 使用 ChromaDB `PersistentClient` 进行本地持久化（无需启动独立服务）
    - 实现 `initialize()` 方法：创建或获取 collection，使用 cosine 距离度量
    - 实现 `upsert(id, vector, text, metadata)` 方法：ID 格式为 `{file_path}::{chunk_index}`
    - 实现 `delete_by_file_path(file_path)` 方法：删除指定文件的所有向量记录
    - 实现 `delete_all()` 方法：删除所有向量记录
    - 实现 `search(vector, top_k)` 方法：语义检索
    - 实现 `get_existing_files()` 方法：返回 file_path -> last_modified 映射
    - 实现 `get_record_count()` 方法：返回当前向量记录总数
    - _Requirements: 4.3, 4.4, 4.5, 5.1, 5.2, 5.4, 5.5_

  - [ ]* 6.2 编写 VectorStore 单元测试
    - 在 `tests/test_store.py` 中编写测试
    - 使用临时目录创建测试用 PersistentClient
    - 测试 upsert、delete、search 操作
    - 测试持久化：关闭后重新打开能查询到数据
    - _Requirements: 4.3, 4.4, 4.5, 5.1, 5.4, 5.5_

- [x] 7. 实现 FQA 文件管理模块
  - [x] 7.1 实现 FQAManager 类
    - 在 `src/fqa.py` 中实现 `FQAManager` 类
    - 实现 `load()` 方法：解析 FQA 文件，每行以第一个 `=` 分隔问题和答案
    - 跳过空行和不含 `=` 的行
    - 实现 `append(pair)` 方法：追加写入一条问答对
    - FQA 文件不存在时自动创建文件及父目录
    - 实现 `semantic_match(query_vector, embed_engine)` 方法：对所有 FQA 问题向量化后计算余弦相似度，返回最高匹配
    - I/O 错误时显示包含失败原因的错误信息
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_

  - [ ]* 7.2 编写 FQAManager 单元测试
    - 在 `tests/test_fqa.py` 中编写测试
    - 测试文件解析（正常行、空行、无等号行）
    - 测试追加写入
    - 测试文件不存在时自动创建
    - _Requirements: 7.1, 7.2, 7.3, 7.5, 7.6_

- [x] 8. 实现查询引擎模块
  - [x] 8.1 实现 QueryEngine 类
    - 在 `src/query.py` 中实现 `QueryEngine` 类
    - 实现 `query(question, top_k=5)` 方法
    - 实现 FQA 优先级策略：先语义匹配 FQA，相似度 > 0.85 时直接返回 FQA 答案
    - FQA 未命中时回退到 Vector_Store 语义检索，返回 top_k 条结果
    - 实现 `validate_question(question)` 方法：拒绝空字符串或纯空白查询
    - Vector_Store 无结果时返回"未找到相关内容"提示
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 9.3_

  - [ ]* 8.2 编写 QueryEngine 单元测试
    - 在 `tests/test_query.py` 中编写测试
    - 测试 FQA 优先级策略（相似度 > 0.85 返回 FQA）
    - 测试回退到向量检索
    - 测试空查询拒绝
    - 测试无结果提示
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 9. Checkpoint - 确保所有模块测试通过
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. 实现增量同步协调模块
  - [x] 10.1 实现 SyncManager 类
    - 在 `src/sync.py` 中实现 `SyncManager` 类
    - 协调 FileScanner、TextChunker、EmbeddingEngine、VectorStore 完成增量同步
    - 新增文件：提取文本 → 切块 → 向量化 → 存储
    - 修改文件：删除旧记录 → 重新提取切块向量化 → 存储新记录
    - 删除文件：删除对应向量记录
    - 修改文件更新失败时回滚（保留原有记录）
    - 单个文件处理失败时跳过并记录错误，继续处理剩余文件
    - 完成后输出统计摘要（新增数、修改数、删除数、未变更数）
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 4.6_

  - [ ]* 10.2 编写 SyncManager 单元测试
    - 在 `tests/test_sync.py` 中编写测试
    - 使用 mock 模拟各模块，测试协调逻辑
    - 测试回滚机制
    - 测试统计摘要输出
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

- [x] 11. 实现 CLI 命令层
  - [x] 11.1 实现 CLI 入口与 scan 命令
    - 在 `src/cli.py` 中使用 Click 框架定义 CLI 组
    - 实现 `kb` 命令组，支持 `--chroma-path`、`--collection`、`--fqa-path`、`--model`、`--chunk-size`、`--chunk-overlap`、`--fqa-threshold`、`--top-k` 全局选项
    - 实现 `scan` 子命令：接收 `--folder` 参数，调用 SyncManager 执行增量同步
    - 输出同步摘要
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 5.6_

  - [x] 11.2 实现 query 命令
    - 实现 `query` 子命令：接收位置参数 `question`
    - 调用 QueryEngine 执行查询
    - FQA 命中时输出答案来源标记和答案内容
    - 向量检索时输出各片段的来源文件和相关文本
    - _Requirements: 1.1, 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 11.3 实现 rebuild 命令
    - 实现 `rebuild` 子命令：接收 `--folder` 参数
    - 显示确认提示（包含当前向量记录总数）
    - 用户确认后删除所有记录并全量重建
    - 用户拒绝时输出"操作已取消"
    - 输出重建结果摘要（成功文件数、向量块数、失败文件数及路径）
    - _Requirements: 1.1, 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 11.4 实现 fqa 命令
    - 实现 `fqa` 子命令：接收 `--add` 参数（格式为"问题=答案"）
    - 调用 FQAManager 追加写入
    - 输出写入成功确认
    - _Requirements: 1.1, 7.3, 7.4_

- [x] 12. 集成与端到端连接
  - [x] 12.1 实现模块初始化与依赖注入
    - 在 `src/cli.py` 中实现各模块的初始化逻辑
    - 根据 CLI 配置参数创建 EmbeddingEngine、VectorStore、FQAManager、QueryEngine、SyncManager 实例
    - 确保 TextChunker 使用 EmbeddingEngine 的 tokenizer
    - 添加 `pyproject.toml` 中的 `[project.scripts]` 入口点配置：`kb = "src.cli:cli"`
    - _Requirements: 1.1, 1.4, 1.5_

  - [ ]* 12.2 编写端到端集成测试
    - 在 `tests/test_integration.py` 中编写集成测试
    - 使用临时目录和测试文件，测试完整的 scan → query 流程
    - 测试 FQA 优先级策略的端到端行为
    - 测试 rebuild 命令的完整流程
    - _Requirements: 1.1, 5.6, 6.4, 8.1, 8.2, 8.3_

- [x] 13. Final checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- 每个任务引用了具体的需求条目以确保可追溯性
- Checkpoints 确保增量验证
- 使用 ChromaDB PersistentClient 无需启动独立服务，简化部署
- sentence-transformers 的 `paraphrase-multilingual-MiniLM-L12-v2` 模型支持中文，384 维向量
- 所有计算均在本地完成，不依赖任何在线外部服务

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["2.1", "4.1"] },
    { "id": 2, "tasks": ["2.2", "3.1", "4.2"] },
    { "id": 3, "tasks": ["3.2"] },
    { "id": 4, "tasks": ["3.3", "6.1"] },
    { "id": 5, "tasks": ["6.2", "7.1"] },
    { "id": 6, "tasks": ["7.2", "8.1"] },
    { "id": 7, "tasks": ["8.2", "10.1"] },
    { "id": 8, "tasks": ["10.2", "11.1"] },
    { "id": 9, "tasks": ["11.2", "11.3", "11.4"] },
    { "id": 10, "tasks": ["12.1"] },
    { "id": 11, "tasks": ["12.2"] }
  ]
}
```
