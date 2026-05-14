# 本地知识库 RAG CLI 工具

基于本地向量化的知识库检索系统，支持多格式文档的增量索引与语义查询。所有计算均在本地完成，不依赖任何在线外部大模型服务。

## 项目简介

本系统是一个基于 CLI 的本地 RAG（检索增强生成）解决方案，主要功能包括：

- **多格式文档支持**：自动解析 TXT、Markdown、Word、Excel、PDF 格式文件
- **增量同步**：智能检测文件变更（新增、修改、删除），仅处理变化的文件
- **语义检索**：使用本地多语言嵌入模型进行向量化，支持中文语义匹配
- **FQA 优先级机制**：支持人工纠错问答对，查询时优先匹配 FQA 答案
- **全量重建**：支持一键重建整个知识库索引
- **纯本地运行**：使用 ChromaDB 本地持久化存储，sentence-transformers 本地模型

## 安装方法

### 环境要求

- Python >= 3.9

### 安装步骤

```bash
# 克隆项目
git clone <repository-url>
cd question-and-answer

# 以开发模式安装（包含测试依赖）
pip install -e ".[dev]"
```

安装完成后，`kb` 命令将可在终端中直接使用。

## CLI 命令使用方法

### 全局选项

所有子命令共享以下全局选项：

| 选项 | 环境变量 | 默认值 | 说明 |
|------|----------|--------|------|
| `--chroma-path` | `CHROMA_PATH` | `./chroma_data` | ChromaDB 本地持久化路径 |
| `--collection` | `CHROMA_COLLECTION` | `knowledge_base` | ChromaDB collection 名称 |
| `--fqa-path` | `FQA_PATH` | `./fqa.txt` | FQA 问答对文件路径 |
| `--model` | `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Embedding 模型名称 |
| `--chunk-size` | `CHUNK_SIZE` | `512` | 切块大小（token） |
| `--chunk-overlap` | `CHUNK_OVERLAP` | `64` | 相邻块重叠大小（token） |
| `--fqa-threshold` | `FQA_THRESHOLD` | `0.85` | FQA 匹配相似度阈值 |
| `--top-k` | `TOP_K` | `5` | 向量检索返回数量 |

### scan - 扫描并增量同步

扫描知识库文件夹，检测文件变更并增量更新向量索引。

```bash
kb scan --folder <知识库文件夹路径>
```

**参数说明：**
- `--folder`：知识库文件夹路径（必需）

**示例：**

```bash
# 扫描 docs 文件夹并同步
kb scan --folder ./docs

# 指定自定义 ChromaDB 存储路径
kb scan --folder ./docs --chroma-path ./my_vectors
```

**输出示例：**

```
扫描完成：
  新增文件: 3
  修改文件: 1
  删除文件: 0
  未变更: 10
```

### query - 查询知识库

对知识库进行语义查询。系统会优先匹配 FQA 中的人工纠正答案，未命中时回退到向量检索。

```bash
kb query "<查询问题>"
```

**参数说明：**
- `question`：查询问题（位置参数，必需）

**示例：**

```bash
# 基本查询
kb query "如何退货"

# 指定返回更多结果
kb query "退货流程" --top-k 10

# 调整 FQA 匹配阈值
kb query "运费问题" --fqa-threshold 0.9
```

**输出示例（FQA 命中）：**

```
[FQA 匹配] 相似度: 0.92
答案: 请联系客服400-xxx-xxxx，提供订单号即可申请退货
```

**输出示例（向量检索）：**

```
[向量检索] 找到 5 条相关结果：

1. [来源: 售后政策.md] (相似度: 0.82)
   退货流程：用户可在收货后7天内申请退货...

2. [来源: FAQ.docx] (相似度: 0.78)
   关于退货运费的说明...
```

### rebuild - 全量重建知识库

删除所有现有向量记录，重新扫描并索引知识库文件夹中的所有文件。

```bash
kb rebuild --folder <知识库文件夹路径>
```

**参数说明：**
- `--folder`：知识库文件夹路径（必需）

**示例：**

```bash
# 全量重建
kb rebuild --folder ./docs
```

**交互流程：**

```
当前知识库包含 156 条向量记录。
确认要删除所有记录并重建吗？[y/N]: y

重建完成：
  成功处理文件: 14
  生成向量块: 156
  失败文件: 0
```

### fqa - 管理 FQA 问答对

添加人工纠错的问答对到 FQA 文件。

```bash
kb fqa --add "问题=答案"
```

**参数说明：**
- `--add`：要添加的问答对，格式为 `问题=答案`（问题部分不得包含等号）

**示例：**

```bash
# 添加一条 FQA 记录
kb fqa --add "如何退货=请联系客服400-xxx-xxxx，提供订单号即可申请退货"

# 添加另一条记录
kb fqa --add "退货运费谁承担=质量问题由我方承担运费，非质量问题由买家承担"
```

**输出示例：**

```
已添加 FQA 记录：
  问题: 如何退货
  答案: 请联系客服400-xxx-xxxx，提供订单号即可申请退货
```

## 配置说明

### 环境变量配置

可通过环境变量设置默认配置，避免每次命令都传递参数：

```bash
export CHROMA_PATH="./chroma_data"
export CHROMA_COLLECTION="knowledge_base"
export FQA_PATH="./fqa.txt"
export EMBEDDING_MODEL="paraphrase-multilingual-MiniLM-L12-v2"
export CHUNK_SIZE="512"
export CHUNK_OVERLAP="64"
export FQA_THRESHOLD="0.85"
export TOP_K="5"
```

### FQA 文件格式

FQA 文件为 UTF-8 编码的纯文本文件，每行一个问答对，使用第一个 `=` 作为分隔符：

```text
如何退货=请联系客服400-xxx-xxxx，提供订单号即可申请退货
退货运费谁承担=质量问题由我方承担运费，非质量问题由买家承担
发货时间=下单后48小时内发货，节假日顺延
```

- 空行和不含 `=` 的行会被自动跳过
- 问题部分不得包含 `=` 字符

### 支持的文件格式

| 格式 | 扩展名 | 提取方式 |
|------|--------|----------|
| 纯文本 | .txt | UTF-8 直接读取 |
| Markdown | .md | 移除语法标记，保留结构 |
| Word | .doc, .docx | 按段落顺序提取 |
| Excel | .xls, .xlsx | 按工作表→行→单元格拼接 |
| PDF | .pdf | 按页码顺序提取 |

## 示例用法

### 典型工作流

```bash
# 1. 安装项目
pip install -e ".[dev]"

# 2. 首次扫描知识库
kb scan --folder ./my_docs

# 3. 查询知识库
kb query "公司的退货政策是什么"

# 4. 添加人工纠错答案
kb fqa --add "退货期限=收货后7天内可申请退货"

# 5. 再次查询（会优先匹配 FQA）
kb query "退货期限是多久"

# 6. 文档更新后增量同步
kb scan --folder ./my_docs

# 7. 数据异常时全量重建
kb rebuild --folder ./my_docs
```

### 中文文档处理

系统使用多语言嵌入模型（paraphrase-multilingual-MiniLM-L12-v2），对中文有良好支持：

- 中文文本按句子边界（。！？；）优先切分
- 支持中英文混合文档
- 语义相似的中文查询能正确匹配（如"怎么退货"与"退货流程"）

## 开发

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_scanner.py

# 显示详细输出
pytest -v
```

## 项目结构

```
question-and-answer/
├── src/
│   ├── __init__.py         # 包初始化
│   ├── cli.py              # CLI 入口与命令定义
│   ├── scanner.py          # 文件扫描与变更检测
│   ├── chunker.py          # 文本提取与切块
│   ├── embedding.py        # 本地 Embedding 引擎
│   ├── store.py            # ChromaDB 向量存储
│   ├── fqa.py              # FQA 文件管理
│   ├── query.py            # 查询引擎
│   └── sync.py             # 增量同步协调
├── tests/
│   ├── __init__.py         # 测试包
│   └── conftest.py         # pytest 共享 fixtures
├── docs/
│   └── 我的需求.md
├── pyproject.toml          # 项目配置与依赖声明
├── package.json
└── README.md               # 本文件
```
