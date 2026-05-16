# Implementation Plan: COI Refactor

## Overview

将 COI（我问你答）本地离线文档问答工具按照新架构进行完整重构。核心变更：移除旧版「每次提问重建向量库」逻辑，改为 init 一次性全量建库 + ask 纯读取缓存的架构。实现基于 Python + Click CLI + ChromaDB + sentence-transformers，所有数据存储于程序同级 coi_data/ 目录。

## Tasks

- [x] 1. 搭建项目基础结构与核心数据模型
  - [x] 1.1 创建 models.py 数据模型
    - 定义 FileChange、ScanResult、Chunk、ChunkMetadata、SearchResult、FQAPair、QueryResult 数据类
    - 使用 Python dataclass 实现，确保所有字段类型注解完整
    - _Requirements: 3.3, 5.1, 6.3_
  - [x] 1.2 创建 requirements.txt 依赖清单
    - 列出所有运行时依赖：click, chromadb, sentence-transformers, python-docx, openpyxl, PyPDF2, markdown-it-py, numpy
    - 列出开发依赖：pytest, hypothesis, pyinstaller
    - _Requirements: 9.1, 9.2_
  - [x] 1.3 创建 config.py 数据目录管理模块
    - 实现 get_data_dir()、get_config_path()、get_fqa_path()、get_vector_db_path()
    - 实现 load_config()、save_config() 函数
    - 支持 PyInstaller 打包后的路径检测（sys.frozen）
    - _Requirements: 1.3, 1.4, 1.5, 8.1, 8.2, 8.3_
  - [ ]* 1.4 编写 config.py 属性测试
    - **Property 2: Path resolution to absolute** - 验证任意有效目录路径经 save_config 后 load_config 返回绝对路径
    - **Property 3: Config overwrite on re-init** - 验证多次 save_config 后仅保留最后一次的值
    - **Validates: Requirements 1.3, 1.6**
  - [x] 1.5 创建 setup.py 环境安装脚本
    - 实现自动安装 requirements.txt 中所有依赖的脚本
    - 安装完成后显示使用说明
    - _Requirements: 9.3_

- [x] 2. Checkpoint - 确保基础结构正确
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. 实现文件扫描器 scanner.py
  - [x] 3.1 实现 FileScanner.scan() 方法
    - 递归遍历目录，收集所有支持格式文件（.txt, .md, .pdf, .docx, .xlsx, .csv）
    - 排除隐藏文件和隐藏目录（名称以 . 开头）
    - 扩展名匹配不区分大小写
    - 遇到文件系统错误时跳过并记录到 ScanResult.errors
    - _Requirements: 2.1, 2.2, 2.3_
  - [ ]* 3.2 编写 scanner.py 属性测试
    - **Property 4: Scanner returns exactly supported non-hidden files** - 验证对任意目录树，扫描结果恰好包含所有非隐藏的支持格式文件
    - **Validates: Requirements 2.1, 2.2**

- [x] 4. 实现文本提取与切块 chunker.py
  - [x] 4.1 实现 TextChunker 文本提取方法
    - 实现 _extract_txt、_extract_markdown、_extract_word、_extract_excel、_extract_pdf、_extract_csv 六种格式提取
    - extract_text() 统一入口，根据扩展名分发到对应提取方法
    - 提取失败返回 None 并记录日志
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8_
  - [x] 4.2 实现 TextChunker.chunk() 切块方法
    - 使用 tokenizer 进行 token 计数，按 chunk_size=512 切分
    - 相邻块保留 chunk_overlap=64 token 重叠
    - 以中文句子边界（。！？；\n）为优先分割点
    - 处理尾部不足 overlap 的合并逻辑
    - _Requirements: 3.1_
  - [ ]* 4.3 编写 chunker.py 属性测试
    - **Property 5: Chunk size invariant** - 验证任意超过 512 token 的文本，每个 chunk 的 token_count ≤ 512
    - **Property 14: TXT extraction round-trip** - 验证任意 UTF-8 文本写入 .txt 后提取结果等价
    - **Property 15: CSV extraction format** - 验证任意 CSV 文件提取后行数和列分隔符正确
    - **Validates: Requirements 3.1, 10.1, 10.6**

- [x] 5. 实现向量化引擎 embedding.py
  - [x] 5.1 实现 EmbeddingEngine 类
    - 延迟加载 paraphrase-multilingual-MiniLM-L12-v2 模型
    - 实现 embed() 单条文本向量化，返回 384 维归一化向量
    - 实现 embed_batch() 批量向量化
    - 实现 get_tokenizer() 返回 tokenizer 供 TextChunker 使用
    - _Requirements: 3.2, 9.1, 9.4_
  - [ ]* 5.2 编写 embedding.py 属性测试
    - **Property 6: Embedding dimension and normalization invariant** - 验证任意非空文本的向量为 384 维且 L2 范数在 [0.99, 1.01]
    - **Validates: Requirements 3.2**

- [x] 6. 实现 ChromaDB 向量存储 store.py
  - [x] 6.1 实现 VectorStore 类
    - 使用 ChromaDB PersistentClient，cosine 距离度量
    - 实现 initialize()、upsert()、delete_all()、search()、get_record_count() 方法
    - search() 返回按距离升序排列的 SearchResult 列表
    - _Requirements: 3.3, 3.4, 5.1_
  - [ ]* 6.2 编写 store.py 属性测试
    - **Property 7: Vector store round-trip** - 验证 upsert 后 search 能返回原始文本和完整元数据
    - **Property 10: Vector search results ordering and limit** - 验证搜索结果按相似度降序排列且数量不超过 top_k
    - **Validates: Requirements 3.3, 5.1**

- [x] 7. Checkpoint - 确保核心模块正确
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. 实现 FQA 标准答案管理 fqa.py
  - [x] 8.1 实现 FQAManager 类
    - 实现 load() 从 fqa.json 加载所有条目
    - 实现 append() 追加问答对（自动创建文件和目录）
    - 实现 semantic_match() 语义匹配，计算余弦相似度返回最高匹配
    - JSON 解析失败时返回空列表不中断
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 5.2, 5.3_
  - [ ]* 8.2 编写 fqa.py 属性测试
    - **Property 12: FQA append preserves all entries** - 验证 N 次 append 后 load 返回 N 条按插入顺序排列的记录
    - **Validates: Requirements 6.3**

- [x] 9. 实现双源查询引擎 query.py
  - [x] 9.1 实现 QueryEngine 类
    - 实现 query() 方法：向量化问题 → 向量库检索 top-5 → FQA 语义匹配 → 合并结果
    - FQA 阈值 0.85：仅当最高相似度严格大于 0.85 时包含 FQA 答案
    - 返回 QueryResult 包含双源结果
    - _Requirements: 5.1, 5.2, 5.3, 5.5, 5.6_
  - [ ]* 9.2 编写 query.py 属性测试
    - **Property 11: FQA threshold matching** - 验证仅当最大余弦相似度 > 0.85 时 QueryResult 包含 FQA 答案
    - **Validates: Requirements 5.2, 5.3**

- [x] 10. 实现 CLI 命令入口 main.py
  - [x] 10.1 实现 init 命令
    - 使用 Click 框架，接收 folder 参数
    - 验证路径存在且为目录，解析为绝对路径
    - 保存配置 → 扫描文档 → 全量向量化 → 输出统计摘要
    - 已有旧向量库时先清空再重建
    - 零文件时显示支持格式列表并终止
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.4, 2.5, 3.4, 3.5, 3.6_
  - [x] 10.2 实现 ask 命令
    - 验证已初始化（config.json + vector_db/ 存在）
    - 验证问题非空
    - 调用 QueryEngine 执行双源查询
    - 输出格式：FQA 标准答案（相似度 + 答案）+ 文档检索结果（来源文件 + 相似度 + 200 字预览）
    - 无结果时提示重新 init
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.4, 5.5, 5.6_
  - [x] 10.3 实现 add-fqa 命令
    - 验证 question 和 answer 非空
    - 自动创建 coi_data/ 目录
    - 调用 FQAManager.append() 追加记录
    - 显示确认信息
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_
  - [x] 10.4 实现 clear 命令
    - 使用 Click confirmation_option 确认
    - 删除整个 coi_data/ 目录
    - 目录不存在时提示无需清空
    - 删除失败时输出错误到 stderr
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_
  - [ ]* 10.5 编写 main.py CLI 集成测试
    - **Property 1: Path validation correctness** - 验证 init 命令对不存在路径和非目录路径拒绝
    - **Property 9: Whitespace input rejection** - 验证 ask 和 add-fqa 对纯空白输入拒绝
    - **Property 8: Ask command is read-only** - 验证 ask 命令执行后 coi_data/ 内容不变
    - **Validates: Requirements 1.1, 1.2, 4.1, 4.4, 6.1**

- [x] 11. Checkpoint - 确保所有命令功能正确
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. 实现打包与收尾
  - [x] 12.1 实现 build.py PyInstaller 打包脚本
    - 使用 --onefile 模式打包为单文件可执行程序
    - 配置所有 hidden-import（chromadb, sentence_transformers, torch 等）
    - 支持 Windows/macOS/Linux 三平台
    - _Requirements: 9.2, 9.3, 9.4_
  - [ ]* 12.2 编写 Data_Directory 约束属性测试
    - **Property 13: Data directory containment** - 验证所有命令的文件写入操作仅发生在 coi_data/ 内
    - **Validates: Requirements 8.1, 8.2, 8.3**
  - [ ]* 12.3 创建 tests/conftest.py 共享测试 fixtures
    - 配置临时目录 fixture、mock embedding engine、mock vector store
    - 配置 hypothesis settings（max_examples=100）
    - _Requirements: All_

- [x] 13. Final checkpoint - 确保所有测试通过
  - 所有必需实现任务已完成并通过验证。可选属性测试（标记 *）可后续补充。

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- 实现语言：Python 3.9+
- 测试框架：pytest + hypothesis

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3", "1.5"] },
    { "id": 2, "tasks": ["1.4", "3.1"] },
    { "id": 3, "tasks": ["3.2", "4.1"] },
    { "id": 4, "tasks": ["4.2", "5.1"] },
    { "id": 5, "tasks": ["4.3", "5.2", "6.1"] },
    { "id": 6, "tasks": ["6.2", "8.1"] },
    { "id": 7, "tasks": ["8.2", "9.1"] },
    { "id": 8, "tasks": ["9.2", "10.1"] },
    { "id": 9, "tasks": ["10.2", "10.3", "10.4"] },
    { "id": 10, "tasks": ["10.5", "12.1", "12.3"] },
    { "id": 11, "tasks": ["12.2"] }
  ]
}
```
