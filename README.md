# local-knowledge-skill

本地知识库 RAG Skill —— 对本地文档进行向量化索引与语义检索问答。

## 功能

- 多格式文档支持（TXT、Markdown、Word、Excel、PDF）
- 增量同步，只处理变化的文件
- 基于语义的中文问答检索
- FQA 人工纠错优先级机制
- 纯本地运行，不依赖在线大模型

## 使用方式

将 `local-knowledge-skill/` 目录作为 skill 安装到支持 skill 的智能体中（如 Claude Code、LobeHub 等）。

智能体会自动根据用户意图触发此 skill，并通过内置脚本完成文档索引和查询操作。

## 目录结构

```
local-knowledge-skill/
├── SKILL.md              # Skill 说明文档
├── scripts/              # 可执行脚本
│   ├── kb.py             # 主入口（scan/query/rebuild/fqa）
│   ├── setup_env.py      # 依赖安装脚本
│   ├── requirements.txt  # Python 依赖
│   └── ...               # 各功能模块
└── references/
    └── troubleshooting.md
```

## 环境要求

- Python 3.9+

## License

MIT
