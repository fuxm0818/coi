---
name: local-knowledge-base
description: 本地知识库 RAG 工具，用于对本地文件夹中的文档进行向量化索引和语义检索问答。当用户提到知识库、文档索引、语义搜索、向量检索、RAG、文档问答、知识管理，或者想要对一批本地文件建立可搜索的索引，或者想通过自然语言查询本地文档内容时，使用此 skill。也适用于用户想要纠正 AI 回答、管理 FAQ/FQA 问答对、增量更新文档索引、重建知识库等场景。即使用户没有明确说"知识库"，只要涉及"帮我从这些文档里找答案"、"把这个文件夹的内容建个索引"、"我想问一下文档里的内容"等意图，都应该触发此 skill。
---

# 本地知识库 RAG 工具

对本地文件夹中的多格式文档（TXT、Markdown、Word、Excel、PDF）进行向量化索引，支持基于语义的中文问答检索。所有计算在本地完成，不调用任何在线大模型。

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

## 命令用法

所有命令通过 `python3 <SKILL_PATH>/scripts/kb.py` 执行。以下用 `kb.py` 简写。

### 扫描并索引文档

```bash
python3 <SKILL_PATH>/scripts/kb.py scan --folder <知识库文件夹路径>
```

递归扫描文件夹，增量更新向量索引。只处理变化的文件。

支持格式：.txt、.md、.doc、.docx、.xls、.xlsx、.pdf

### 查询知识库

```bash
python3 <SKILL_PATH>/scripts/kb.py query "<问题>"
```

语义查询。FQA 命中时直接返回答案，否则返回最相关的文档片段。

### 全量重建

```bash
python3 <SKILL_PATH>/scripts/kb.py rebuild --folder <知识库文件夹路径>
```

删除所有索引后重新扫描全部文件。会要求确认（传 `--yes` 跳过确认）。

### 添加 FQA 纠错

```bash
python3 <SKILL_PATH>/scripts/kb.py fqa --add "问题=答案"
```

添加人工纠正的问答对。下次查询时优先匹配。

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

# 2. 索引文档
python3 <SKILL_PATH>/scripts/kb.py scan --folder ./my_docs

# 3. 查询
python3 <SKILL_PATH>/scripts/kb.py query "公司的退货政策是什么"

# 4. 纠错
python3 <SKILL_PATH>/scripts/kb.py fqa --add "退货期限=收货后7天内可申请退货"

# 5. 文档更新后增量同步
python3 <SKILL_PATH>/scripts/kb.py scan --folder ./my_docs
```

## 注意事项

- `chroma_data/` 是向量数据库目录，不要手动删除
- FQA 文件格式为每行 `问题=答案`，可手动编辑
- 中文文档效果最佳，也支持中英混合
- 每次 scan 只处理变化的文件，大量文档也很高效
- 如遇问题，参考 `references/troubleshooting.md`
