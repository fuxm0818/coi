# Requirements Document

## Introduction

本地知识库系统是一个基于 CLI 的本地 RAG（检索增强生成）解决方案。系统采用一次性进程模式，按需触发文件扫描与向量库更新，不依赖后台服务或在线外部大模型。系统支持对本地文件夹中的文档进行向量化索引，并提供基于语义匹配的问答能力，同时支持人工纠错的 FQA 优先级机制。

## Glossary

- **CLI_Engine**: 命令行引擎，系统的主入口程序，负责解析用户命令并调度各模块执行
- **File_Scanner**: 文件扫描器，负责递归遍历知识库文件夹，检测文件的新增、修改和删除
- **Vector_Store**: 向量存储模块，基于 ChromaDB 实现的本地持久化向量数据库
- **Text_Chunker**: 文本切块器，负责将文档内容按固定 token 长度切分为向量块
- **Embedding_Engine**: 嵌入引擎，使用本地模型将文本块转换为向量表示
- **FQA_Manager**: FQA 管理器，负责读取、写入和查询 FQA 问答对文件
- **Query_Engine**: 查询引擎，负责接收用户问题并按优先级策略返回匹配结果
- **Knowledge_Folder**: 知识库文件夹，用户指定的存放知识文档的根目录
- **FQA_File**: FQA 文件，独立于知识库文件夹的纯文本问答对文件
- **Chunk**: 向量块，文档经切分后的文本片段及其对应的向量表示和元数据

## Requirements

### Requirement 1: CLI 命令解析与调度

**User Story:** 作为用户，我希望通过命令行执行知识库操作，以便按需触发扫描、查询和重建等功能。

#### Acceptance Criteria

1. WHEN 用户执行 CLI 程序并提供有效命令（scan、query、rebuild 之一）及其所需参数时，THE CLI_Engine SHALL 解析命令参数、调度对应模块执行，并在模块执行完成后以退出码 0 退出
2. IF 用户执行 CLI 程序时未提供命令或提供了不在有效命令列表中的命令，THEN THE CLI_Engine SHALL 输出帮助信息（包含可用命令列表及各命令的用途说明）并以退出码 1 退出
3. IF 用户提供了有效命令但缺少该命令所需的必要参数或参数格式不合法，THEN THE CLI_Engine SHALL 输出该命令的参数用法说明并以退出码 1 退出
4. THE CLI_Engine SHALL 在单次进程中完成所有操作后自动退出，不保持后台运行状态
5. THE CLI_Engine SHALL 在执行过程中不调用任何在线外部大模型服务

### Requirement 2: 文件扫描与变更检测

**User Story:** 作为用户，我希望系统能自动检测知识库文件夹中的文件变更，以便增量更新向量库。

#### Acceptance Criteria

1. WHEN 执行扫描命令时，THE File_Scanner SHALL 递归遍历 Knowledge_Folder 及其所有子文件夹中的文件，并输出一份变更清单，包含所有标记为"新增"、"已修改"或"已删除"的文件条目
2. WHEN File_Scanner 发现 Knowledge_Folder 中存在新文件（向量库中无匹配 file_path 的记录）时，THE File_Scanner SHALL 将该文件标记为"新增"
3. WHEN File_Scanner 检测到文件的最后修改时间戳与向量库中记录的 last_modified 不一致时，THE File_Scanner SHALL 将该文件标记为"已修改"
4. WHEN File_Scanner 发现向量库中存在记录但 Knowledge_Folder 中对应文件已不存在时，THE File_Scanner SHALL 将该文件标记为"已删除"
5. THE File_Scanner SHALL 仅处理以下扩展名的文件：.txt、.md、.doc、.docx、.xls、.xlsx、.pdf
6. IF File_Scanner 在 Knowledge_Folder 中遇到不属于支持扩展名列表的文件，THEN THE File_Scanner SHALL 跳过该文件且不将其纳入变更清单
7. IF Knowledge_Folder 路径不存在或不可访问，THEN THE File_Scanner SHALL 终止扫描并返回错误信息指明该路径无效

### Requirement 3: 文本提取与切块

**User Story:** 作为用户，我希望系统能从多种格式的文档中提取文本并切分为合适的块，以便进行向量化处理。

#### Acceptance Criteria

1. WHEN 处理 TXT 格式文件时，THE Text_Chunker SHALL 以 UTF-8 编码直接读取文件内容作为原始文本
2. WHEN 处理 Markdown 格式文件时，THE Text_Chunker SHALL 移除 Markdown 语法标记并提取纯文本内容，同时将标题、列表、代码块等结构元素以换行符分隔保留其层级关系
3. WHEN 处理 Word 格式文件时，THE Text_Chunker SHALL 按段落顺序提取文档中的所有文本内容
4. WHEN 处理 Excel 格式文件时，THE Text_Chunker SHALL 按工作表顺序依次处理每个工作表，逐行拼接单元格文本内容，单元格之间以制表符分隔，行之间以换行符分隔
5. WHEN 处理 PDF 格式文件时，THE Text_Chunker SHALL 按页码顺序提取文档中的文本内容
6. THE Text_Chunker SHALL 使用与 Embedding 模型一致的 tokenizer 将提取的文本按 512 token 长度切分为多个 Chunk
7. THE Text_Chunker SHALL 在相邻 Chunk 之间保留 64 token 的重叠区域，使得前一个 Chunk 的末尾 64 token 与后一个 Chunk 的开头 64 token 相同
8. IF 最后一个 Chunk 的有效内容不足 64 token，THEN THE Text_Chunker SHALL 将其合并至前一个 Chunk 而非单独生成
9. IF 文件内容为空或提取后文本去除空白字符后长度为 0，THEN THE Text_Chunker SHALL 记录警告日志并跳过该文件
10. IF 文件编码无法识别或文件损坏导致提取失败，THEN THE Text_Chunker SHALL 记录错误日志（包含文件路径与失败原因）并跳过该文件，继续处理剩余文件

### Requirement 4: 向量化与存储

**User Story:** 作为用户，我希望文档切块能被转换为向量并持久化存储，以便后续进行语义检索。

#### Acceptance Criteria

1. WHEN 接收到新的 Chunk 时，THE Embedding_Engine SHALL 使用本地嵌入模型将 Chunk 文本转换为固定维度的向量表示，并将生成的向量与 Chunk 关联传递给 Vector_Store
2. THE Embedding_Engine SHALL 在本地运行，不依赖任何在线外部服务
3. WHEN 向量生成完成时，THE Vector_Store SHALL 将向量及其元数据持久化存储到本地 ChromaDB 数据库，并以 file_path 与 chunk_index 的组合作为唯一标识，若该标识已存在则覆盖更新对应记录
4. THE Vector_Store SHALL 为每个 Chunk 记录以下元数据字段：file_path（源文件相对路径）、file_hash（源文件内容哈希值）、chunk_index（该 Chunk 在源文件中的序号，从 0 开始）、last_modified（源文件最后修改时间戳）
5. THE Vector_Store SHALL 将数据持久化到本地磁盘，确保程序退出并重新启动后，之前存储的向量及元数据可被正常查询返回
6. IF Embedding_Engine 对某个 Chunk 的向量生成失败，THEN THE System SHALL 跳过该 Chunk 并记录错误日志（包含 file_path 和 chunk_index），继续处理剩余 Chunk，不中断整体流程

### Requirement 5: 增量同步

**User Story:** 作为用户，我希望系统只处理变更的文件，以便节省处理时间和计算资源。

#### Acceptance Criteria

1. WHEN File_Scanner 将文件标记为"新增"时，THE Vector_Store SHALL 为该文件的所有 Chunk 创建新的向量记录，每条记录包含 file_path、file_hash、chunk_index、last_modified 元数据字段
2. WHEN File_Scanner 将文件标记为"已修改"时，THE Vector_Store SHALL 删除该文件的所有旧向量记录，并为重新切块后的 Chunk 创建新的向量记录
3. IF 已修改文件在删除旧向量记录后、创建新向量记录过程中发生失败，THEN THE Vector_Store SHALL 回滚本次操作，保留该文件原有的向量记录不变，并输出错误信息指明失败的文件路径及原因
4. WHEN File_Scanner 将文件标记为"已删除"时，THE Vector_Store SHALL 删除该文件对应的所有向量记录
5. WHEN 文件未发生变更时，THE Vector_Store SHALL 保留该文件的现有向量记录不做任何处理
6. WHEN 一次增量同步执行完成后，THE System SHALL 输出本次同步的统计摘要，包含新增文件数、修改文件数、删除文件数和未变更文件数

### Requirement 6: 全量重建

**User Story:** 作为用户，我希望能通过明确指令触发知识库的全量重建，以便在数据异常时恢复一致性。

#### Acceptance Criteria

1. WHEN 用户执行"重建知识库"命令时，THE CLI_Engine SHALL 显示确认提示（包含当前向量记录总数），并等待用户确认后再执行删除操作
2. WHEN 用户确认重建操作后，THE Vector_Store SHALL 删除所有现有向量记录，删除完成后再由 File_Scanner 重新扫描 Knowledge_Folder 中所有支持格式（TXT、Markdown、Word、Excel、PDF）的文件并触发全量索引
3. IF 全量重建过程中某个文件处理失败，THEN THE File_Scanner SHALL 跳过该文件、记录失败原因，并继续处理剩余文件
4. WHEN 全量重建完成时，THE CLI_Engine SHALL 输出重建结果摘要，包含：成功处理文件数、生成向量块数、失败文件数及各失败文件路径与失败原因
5. IF 用户在确认提示中拒绝操作，THEN THE CLI_Engine SHALL 取消重建并输出"操作已取消"提示，不删除任何现有向量记录

### Requirement 7: FQA 文件管理

**User Story:** 作为用户，我希望能通过纯文本文件管理问答对，以便手动纠正 AI 的错误回答。

#### Acceptance Criteria

1. THE FQA_Manager SHALL 从独立于 Knowledge_Folder 的可配置路径读取 FQA_File，该路径通过 CLI 配置项指定
2. THE FQA_File SHALL 采用 UTF-8 编码的纯文本格式存储，每行包含一个问答对，使用等号（=）作为分隔符分隔问题和答案，问题部分不得包含等号字符
3. WHEN 用户通过 CLI 提交纠错记录时，THE FQA_Manager SHALL 将问答对以一行"问题=答案"的格式追加写入 FQA_File 末尾
4. THE FQA_Manager SHALL 作为 FQA_File 的唯一程序写入入口，确保写入一致性
5. IF FQA_File 不存在，THEN THE FQA_Manager SHALL 自动创建该文件及其所需的父级目录
6. IF FQA_File 中存在不包含分隔符的行或空行，THEN THE FQA_Manager SHALL 跳过该行并继续处理后续行
7. IF 写入 FQA_File 时发生 I/O 错误，THEN THE FQA_Manager SHALL 向用户显示包含失败原因的错误信息，并保留文件中已有的内容不变

### Requirement 8: 查询与优先级策略

**User Story:** 作为用户，我希望查询时优先匹配 FQA 中的人工纠正答案，以便获得更准确的回答。

#### Acceptance Criteria

1. WHEN 用户提交查询问题时，THE Query_Engine SHALL 首先对 FQA_File 中的问题进行语义匹配，并将相似度最高的结果作为候选答案
2. WHEN FQA 语义匹配的最高相似度大于 0.85 时，THE Query_Engine SHALL 直接返回该最高相似度对应的 FQA 答案，不再查询 Vector_Store
3. WHEN FQA 语义匹配的最高相似度不大于 0.85 时，THE Query_Engine SHALL 对 Vector_Store 进行语义检索，返回相似度最高的前 5 条相关文档片段
4. IF 用户提交的查询为空字符串或仅包含空白字符，THEN THE Query_Engine SHALL 拒绝查询并返回提示信息，指示用户输入有效的查询内容
5. IF Vector_Store 语义检索无任何结果返回，THEN THE Query_Engine SHALL 返回提示信息，指示未找到相关内容
6. THE Query_Engine SHALL 使用支持中文语义理解的 Embedding 模型进行匹配，确保中文分词和语义相似度计算能区分同义词与无关词

### Requirement 9: 中文文档处理

**User Story:** 作为用户，我的文档以中文为主，我希望系统能正确处理中文文本的切分和语义匹配。

#### Acceptance Criteria

1. THE Text_Chunker SHALL 以完整中文字符为最小单位进行 token 切分，不在多字节字符的字节中间断开，并以中文标点符号（。！？；\n）作为优先分割边界，在 512 token 块大小限制内选择最近的句子边界进行切分
2. THE Embedding_Engine SHALL 使用支持中文文本输入的本地嵌入模型，对纯中文文本生成的向量维度与对英文文本生成的向量维度一致，且同义中文词语（如"购买"与"买入"）之间的余弦相似度不低于 0.7
3. THE Query_Engine SHALL 对中文查询问题生成语义向量表示，使得语义相同但措辞不同的中文查询（如"怎么退货"与"退货流程是什么"）之间的余弦相似度不低于 0.75
4. WHEN 文档中包含中英文混合内容时，THE Text_Chunker SHALL 将中英文文本统一处理，不因语言切换而强制断开当前文本块
