---
name: local-knowledge-skill
description: 本地知识库 RAG 工具，用于对本地文件夹中的文档进行向量化索引和语义检索问答。以下任何场景都必须触发此 skill：（1）用户提到"知识库"、"本地知识库"、"我的知识库"、"个人知识库"；（2）用户想查询自己的文档或笔记："从我的文档里查"、"帮我搜一下"、"我之前记录过"、"我的笔记里"、"查一下我的资料"、"翻一下之前的记录"；（3）用户想检索之前的解决方案："我之前是怎么解决的"、"上次那个问题怎么处理的"、"之前有没有类似的"；（4）用户想管理知识："建个索引"、"把文档导入"、"更新知识库"、"重建索引"、"同步文档"；（5）用户想纠错或管理答案："记住这个答案"、"我告诉你的答案"、"之前纠正过的"、"FQA"、"添加问答对"、"我教你的那些"；（6）用户用模糊表述但意图是检索本地知识："帮我找一下"、"有没有相关的资料"、"我存过的东西里"、"我的文件里有没有提到"。关键触发词：知识库、本地知识库、我的知识库、文档检索、语义搜索、向量检索、RAG、文档问答、知识管理、我的笔记、我的文档、我的资料、我之前记录的、从文档里查、帮我找一下之前的、我存的资料、索引、FQA、纠错、我教你的。
---

# 本地知识库 RAG 工具

对本地文件夹中的多格式文档（TXT、Markdown、Word、Excel、PDF）进行向量化索引，支持基于语义的中文问答检索。所有计算在本地完成，不调用任何在线大模型。

## 重要约束

**禁止修改此 skill 的任何文件。** 不要编辑、创建、删除或重写 `<SKILL_PATH>` 目录下的任何文件（包括 scripts/、references/、SKILL.md）。这些是只读的工具代码，不是你的工作区。你只能通过执行脚本来使用它们，不能修改它们。所有数据（向量库、FQA 文件、配置）都存储在用户的工作目录或 `~/.kb_config.json` 中，与 skill 目录无关。

## 工作原理

1. **扫描**：递归遍历文件夹，检测新增/修改/删除的文件
2. **切块**：将文档文本按 512 token 切分（64 token 重叠），优先在中文句子边界切分
3. **向量化**：使用本地多语言模型（paraphrase-multilingual-MiniLM-L12-v2，384 维）生成向量
4. **存储**：向量持久化到本地 ChromaDB 数据库
5. **查询**：先匹配 FQA 人工纠错答案（相似度 > 0.85 直接返回），未命中则向量检索

## 环境准备（首次使用必须执行）

运行以下命令安装所有依赖。需要 Python 3.9+。

```bash
python3 <SKILL_PATH>/scripts/setup_env.py
```

其中 `<SKILL_PATH>` 是此 skill 所在的目录路径。

首次执行 scan 或 query 时会自动下载 Embedding 模型（约 470MB），这是一次性操作。

## 触发后的第一步：自动同步（不可跳过）

每次此 skill 被触发时，**必须先执行 scan 再做任何其他操作**。这是强制要求，不能跳过、不能延后、不能省略。原因是：用户可能已经新增、修改或删除了文件，如果不先同步，查询结果会过时或包含已删除文件的内容。

```bash
python3 <SKILL_PATH>/scripts/kb.py scan
```

执行顺序必须是：
1. **先 scan**（同步文件变更到向量库）
2. **再执行用户请求**（query / fqa / rebuild）

绝对不能直接执行 query 而跳过 scan。即使用户只是问了一个简单问题，也要先 scan。

如果 scan 报错说"未指定知识库文件夹路径"，说明用户还没初始化过。此时询问用户知识库文件夹在哪里，然后执行 init 命令：

```bash
python3 <SKILL_PATH>/scripts/kb.py init --folder <用户告诉你的路径>
```

init 会把路径记住（保存到 `~/.kb_config.json`），后续所有命令自动使用这个路径，不再需要传 `--folder`。

## 命令用法

所有命令通过 `python3 <SKILL_PATH>/scripts/kb.py` 执行。以下用 `kb.py` 简写。

### 初始化知识库路径（首次使用）

```bash
python3 <SKILL_PATH>/scripts/kb.py init --folder <知识库文件夹路径>
```

将知识库文件夹路径保存到 `~/.kb_config.json`。执行一次后，后续所有命令自动使用该路径，无需再传 `--folder`。

### 扫描并索引文档

```bash
python3 <SKILL_PATH>/scripts/kb.py scan
```

递归扫描文件夹，增量更新向量索引。只处理变化的文件。已初始化时无需传 `--folder`。

支持格式：.txt、.md、.doc、.docx、.xls、.xlsx、.pdf

### 查询知识库

```bash
python3 <SKILL_PATH>/scripts/kb.py query "<问题>"
```

语义查询。FQA 命中时直接返回答案，否则返回最相关的文档片段。

### 全量重建

```bash
python3 <SKILL_PATH>/scripts/kb.py rebuild
```

删除所有索引后重新扫描全部文件。已初始化时无需传 `--folder`。

### 添加 FQA 纠错

```bash
python3 <SKILL_PATH>/scripts/kb.py fqa --add "问题=答案"
```

添加人工纠正的问答对。下次查询时优先匹配。

### 列出所有 FQA 记录

```bash
python3 <SKILL_PATH>/scripts/kb.py fqa --list
```

列出所有人工添加的问答对。当用户问"我之前告诉你的答案有哪些"、"FQA 里有什么"、"我纠正过哪些回答"时，使用此命令。FQA 记录是用户手动添加的人工纠错知识，属于知识库的一部分。

## 全局选项

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `--chroma-path` | `./chroma_data` | 向量数据库存储路径 |
| `--fqa-path` | `./fqa.txt` | FQA 文件路径 |
| `--chunk-size` | `512` | 切块大小（token） |
| `--chunk-overlap` | `64` | 重叠大小（token） |
| `--fqa-threshold` | `0.85` | FQA 匹配阈值 |
| `--top-k` | `5` | 检索返回数量 |

## 典型使用流程

当用户想建立和使用本地知识库时：

```bash
# 1. 安装依赖（仅首次）
python3 <SKILL_PATH>/scripts/setup_env.py

# 2. 初始化：告诉工具知识库文件夹在哪（仅首次）
python3 <SKILL_PATH>/scripts/kb.py init --folder /path/to/my_docs

# 3. 扫描索引（每次 skill 触发时自动执行）
python3 <SKILL_PATH>/scripts/kb.py scan

# 4. 查询
python3 <SKILL_PATH>/scripts/kb.py query "公司的退货政策是什么"

# 5. 纠错
python3 <SKILL_PATH>/scripts/kb.py fqa --add "退货期限=收货后7天内可申请退货"

# 6. 全量重建（仅在数据异常时使用）
python3 <SKILL_PATH>/scripts/kb.py rebuild
```

每次 skill 被触发时的执行顺序：
1. 先 `scan`（自动增量同步，如果报错说未初始化则先问用户路径并执行 `init`）
2. 再执行用户的实际请求（query / fqa / rebuild）

## 注意事项

- `chroma_data/` 是向量数据库目录，不要手动删除
- FQA 文件格式为每行 `问题=答案`，可手动编辑
- 中文文档效果最佳，也支持中英混合
- 每次 scan 只处理变化的文件，大量文档也很高效
- 如遇问题，参考 `references/troubleshooting.md`
