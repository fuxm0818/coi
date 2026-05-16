# Requirements Document

## Introduction

COI（我问你答）是一个纯本地离线文档问答工具的重构项目。核心目标是彻底移除旧版「每次提问重建向量库」的低效逻辑，采用全新架构：仅 `init` 初始化时全量扫描文档并一次性构建向量库，日常 `ask` 提问直接复用已有向量缓存，大幅提升问答响应速度。程序全程不调用任何外部大模型、不上网、无网络请求，所有数据本地化存储于程序同级 `coi_data/` 目录，保障隐私与离线可用性。

## Glossary

- **COI_System**: COI（我问你答）本地离线文档问答工具的完整程序系统
- **Init_Command**: 初始化命令，唯一可以新建或重建向量库的命令入口
- **Ask_Command**: 提问查询命令，基于已构建的缓存向量库和 FQA 标准答案库联合检索
- **AddFQA_Command**: 补充标准答案命令，用户手动录入问题与对应标准答案
- **Clear_Command**: 一键清空命令，删除所有程序生成数据恢复初始状态
- **Vector_Store**: 本地向量数据库，存储文档文本块的向量化表示，用于语义检索
- **FQA_Store**: 标准答案知识库，存储用户自定义的问答对（fqa.json 文件）
- **Config_Store**: 全局配置文件（config.json），存储用户绑定的文档文件夹路径
- **Data_Directory**: 程序同级 `coi_data/` 目录，统一存放所有程序自动生成数据
- **Document_Scanner**: 文档扫描器，递归扫描指定目录内所有支持格式的文档文件
- **Text_Chunker**: 文本切片器，将文档内容按 token 长度切分为适合向量化的文本块
- **Embedding_Engine**: 向量化引擎，使用本地 Embedding 模型将文本转换为向量表示
- **Query_Engine**: 查询引擎，执行双源合并查询策略（向量检索 + FQA 匹配）
- **Supported_Formats**: 支持的文档格式集合，包括 TXT、MD、PDF、DOCX、XLSX、CSV

## Requirements

### Requirement 1: Init 命令 - 文档目录校验与配置持久化

**User Story:** As a user, I want to specify a local document folder during initialization, so that the system knows where to find my documents for building the knowledge base.

#### Acceptance Criteria

1. WHEN the user executes Init_Command with a folder path argument, THE COI_System SHALL validate that the specified path exists and is a directory
2. IF the specified folder path does not exist or is not a directory, THEN THE COI_System SHALL display an error message indicating the path is invalid and terminate with a non-zero exit code without modifying any data
3. WHEN the folder path validation succeeds, THE COI_System SHALL resolve the path to an absolute path and persist it into Config_Store within Data_Directory
4. WHEN Init_Command completes successfully, THE Config_Store SHALL contain a JSON object with the key "knowledge_folder" set to the validated absolute path
5. IF Data_Directory does not exist when Init_Command is executed, THEN THE COI_System SHALL create the Data_Directory automatically before writing Config_Store
6. IF a previous Config_Store already exists, THEN THE Init_Command SHALL overwrite it with the new folder path

### Requirement 2: Init 命令 - 全量文档扫描

**User Story:** As a user, I want the init command to automatically discover all supported documents in my folder, so that I don't need to manually specify each file.

#### Acceptance Criteria

1. WHEN Init_Command executes after path validation, THE Document_Scanner SHALL recursively scan the specified directory (including all subdirectories at any depth) for all files matching Supported_Formats, excluding hidden files and hidden directories (names starting with ".")
2. THE Document_Scanner SHALL recognize files with extensions: .txt, .md, .pdf, .docx, .xlsx, .csv (case-insensitive matching on the file extension)
3. IF a file matches Supported_Formats but cannot be read due to a filesystem error during scanning, THEN THE Document_Scanner SHALL skip that file, record the file path and error reason, and continue scanning remaining files
4. WHEN the scan completes with zero supported files found, THE COI_System SHALL display a message listing the supported formats (.txt, .md, .pdf, .docx, .xlsx, .csv) and terminate the init process without creating Vector_Store
5. WHEN the scan completes with one or more supported files, THE COI_System SHALL display the total count of discovered files as an integer to the user before proceeding to the vectorization phase

### Requirement 3: Init 命令 - 一次性全量向量化建库

**User Story:** As a user, I want the init command to build a complete vector knowledge base from my documents in one pass, so that subsequent queries can be answered instantly.

#### Acceptance Criteria

1. WHEN documents are discovered by Document_Scanner, THE Text_Chunker SHALL extract text content from each document and split the content into chunks with a maximum size of 512 tokens and an overlap of 64 tokens, using Chinese sentence boundaries as preferred split points
2. WHEN text chunks are generated, THE Embedding_Engine SHALL compute 384-dimensional vector embeddings for each chunk using the local paraphrase-multilingual-MiniLM-L12-v2 model with normalized embeddings
3. WHEN embeddings are computed, THE Vector_Store SHALL persist each chunk with its vector, source text, file path (relative to the document folder), file hash (SHA-256), chunk index, and last-modified timestamp (milliseconds)
4. IF a pre-existing Vector_Store contains data, THEN THE Init_Command SHALL delete all existing records before inserting new data
5. WHEN Init_Command completes vector construction, THE COI_System SHALL display a summary including: number of successfully processed files, total generated vector chunks, and any failed files with failure reasons
6. IF a single file fails during text extraction or vectorization, THEN THE COI_System SHALL log the error, skip that file, and continue processing remaining files

### Requirement 4: Ask 命令 - 缓存复用与禁止重建

**User Story:** As a user, I want the ask command to answer my questions instantly by reusing the cached vector database, so that I don't experience slow response times.

#### Acceptance Criteria

1. THE Ask_Command SHALL read directly from the persisted Vector_Store and FQA_Store without triggering any document scanning, text extraction, or vector rebuilding operations
2. WHEN the user executes Ask_Command, THE COI_System SHALL validate that Config_Store exists and Vector_Store directory is present
3. IF Config_Store does not exist or Vector_Store directory is missing, THEN THE COI_System SHALL display an error message instructing the user to run Init_Command first and terminate with a non-zero exit code
4. IF the user provides an empty or whitespace-only question, THEN THE COI_System SHALL display an error message indicating the question cannot be empty and terminate with a non-zero exit code
5. IF the Embedding model fails to load during Ask_Command execution, THEN THE COI_System SHALL display an error message indicating the model loading failure and terminate with a non-zero exit code

### Requirement 5: Ask 命令 - 双源合并查询

**User Story:** As a user, I want my questions answered using both document search results and my custom standard answers, so that I get the most comprehensive and accurate response.

#### Acceptance Criteria

1. WHEN a valid question is received, THE Query_Engine SHALL vectorize the question using Embedding_Engine and search Vector_Store for the top-5 most similar chunks, returning results ordered by similarity from highest to lowest
2. WHEN a valid question is received, THE Query_Engine SHALL perform semantic matching against all entries in FQA_Store by computing cosine similarity between the question vector and each stored question vector
3. IF the highest FQA semantic match similarity is strictly greater than 0.85, THEN THE Query_Engine SHALL include the matched standard answer and its similarity score in the query result
4. WHEN the query completes, THE COI_System SHALL output the final answer displaying: each vector retrieval document fragment with its source file path, similarity score, and a text preview of up to 200 characters; and the FQA matched standard answer with its similarity score, with both sections shown when both sources return results
5. IF neither Vector_Store returns any search results nor FQA_Store produces a match above the 0.85 threshold, THEN THE COI_System SHALL display a message indicating no relevant content was found and suggest re-running init to update the vector store
6. WHEN only one of the two sources (Vector_Store or FQA_Store) returns results, THE COI_System SHALL output the available source results without requiring both sources to match

### Requirement 6: AddFQA 命令 - 标准答案管理

**User Story:** As a user, I want to manually add question-answer pairs as standard answers, so that the system can provide precise responses for specific questions I care about.

#### Acceptance Criteria

1. WHEN the user executes AddFQA_Command with a question and answer argument, THE COI_System SHALL validate that both the question and answer are non-empty strings after trimming whitespace
2. IF either the question or answer is empty or whitespace-only, THEN THE COI_System SHALL display an error message specifying which field is invalid and terminate with a non-zero exit code
3. WHEN validation passes, THE FQA_Store SHALL append the new question-answer pair as a JSON object with "question" and "answer" keys to the fqa.json array within Data_Directory
4. WHEN the fqa.json file does not exist, THE AddFQA_Command SHALL create the file and initialize it as a JSON array containing the first entry
5. WHEN the entry is successfully added, THE COI_System SHALL display a confirmation message showing the recorded question and answer
6. IF Data_Directory does not exist when AddFQA_Command is executed, THEN THE COI_System SHALL create the Data_Directory automatically before writing fqa.json

### Requirement 7: Clear 命令 - 数据清空

**User Story:** As a user, I want to completely reset all program data with a single command, so that I can start fresh or clean up when the tool is no longer needed.

#### Acceptance Criteria

1. WHEN the user executes Clear_Command, THE COI_System SHALL prompt the user for confirmation before performing any deletion
2. WHEN the user confirms the Clear_Command operation, THE COI_System SHALL delete the entire Data_Directory (coi_data/) and all its contents including config.json, fqa.json, and vector_db/
3. IF the user declines the confirmation prompt, THEN THE COI_System SHALL abort the operation without deleting any files and terminate with exit code 0
4. THE Clear_Command SHALL only perform file deletion operations and SHALL NOT trigger any document scanning, text parsing, or vectorization behavior
5. IF Data_Directory does not exist, THEN THE COI_System SHALL display a message indicating there is nothing to clear and terminate with exit code 0
6. IF the deletion operation fails due to filesystem errors, THEN THE COI_System SHALL display the error details to stderr and terminate with a non-zero exit code
7. WHEN deletion succeeds, THE COI_System SHALL display a confirmation message to stdout and instruct the user to run Init_Command to reinitialize

### Requirement 8: 数据存储规则

**User Story:** As a user, I want all program data stored in a transparent, predictable location next to the program, so that I can easily find, manage, or manually delete the data.

#### Acceptance Criteria

1. THE COI_System SHALL store all auto-generated data exclusively within the Data_Directory (coi_data/) located in the same directory as the program executable (or the main script directory in development mode)
2. THE Data_Directory SHALL contain at most three data items: config.json (configuration), fqa.json (standard answers), and vector_db/ (vector database directory)
3. THE COI_System SHALL NOT use system hidden paths, user home directories, temporary directories, or any location outside Data_Directory for storing program data
4. WHEN the user manually deletes the Data_Directory, THE COI_System SHALL treat this as equivalent to executing Clear_Command, where uninitialized state means: load_config returns no configuration, ask command refuses to execute with an error message directing the user to run init, and no fqa.json or vector_db/ exists
5. WHEN a command that writes data is executed and the Data_Directory does not yet exist, THE COI_System SHALL create the Data_Directory automatically before writing any files

### Requirement 9: 离线运行与打包

**User Story:** As a user, I want the tool to run completely offline as a standalone executable, so that I can use it without internet access or Python environment setup.

#### Acceptance Criteria

1. THE COI_System SHALL operate without any network requests, external API calls, or remote model invocations during execution of all commands (init, ask, add-fqa, clear)
2. THE COI_System SHALL support packaging into a single-file standalone executable for Windows, macOS, and Linux platforms using PyInstaller with the --onefile option
3. WHEN packaged as an executable, THE COI_System SHALL run without requiring Python installation or any third-party dependency installation on the target machine
4. THE Embedding_Engine SHALL use the paraphrase-multilingual-MiniLM-L12-v2 model stored locally on the filesystem, and the model files SHALL be available on the build machine prior to packaging
5. IF the locally stored model files are missing or corrupted at runtime, THEN THE COI_System SHALL display an error message indicating the model is unavailable and exit with a non-zero exit code without attempting any network download

### Requirement 10: 文档格式支持

**User Story:** As a user, I want the system to support common document formats, so that I can build a knowledge base from my existing files without format conversion.

#### Acceptance Criteria

1. THE Text_Chunker SHALL extract text content from plain text files (.txt) encoded in UTF-8
2. WHEN processing a Markdown file (.md), THE Text_Chunker SHALL extract text content with headings, list items, code blocks, and inline text preserved as plain text in their original reading order
3. THE Text_Chunker SHALL extract text content from PDF files (.pdf) by reading all pages sequentially from page 1 to the last page and concatenating the extracted text in page order
4. THE Text_Chunker SHALL extract text content from Word documents (.docx) including all paragraph text and table cell values read row by row
5. THE Text_Chunker SHALL extract text content from Excel files (.xlsx) by reading all sheets and converting each row's cell values to tab-separated text, one row per line
6. THE Text_Chunker SHALL extract text content from CSV files (.csv) encoded in UTF-8 by reading all rows and joining cell values with tab separators, one row per line
7. IF a document file cannot be parsed due to corruption, unsupported encoding, password protection, or any other read error, THEN THE COI_System SHALL log the error with the file path and failure reason, skip the file, and continue processing remaining files
8. IF text extraction from a supported file yields an empty result after trimming whitespace, THEN THE Text_Chunker SHALL log a warning with the file path, return no chunks for that file, and continue processing remaining files
