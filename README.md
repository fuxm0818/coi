# COI（我问你答）

本地离线文档问答工具。全程不调用任何外部大模型、不上网、无网络请求，纯本地独立运行，所有数据本地化存储，保障隐私与离线可用性。

## 核心特性

- **纯离线运行**：零网络依赖、零外部大模型调用、零数据上传
- **多格式支持**：TXT、MD、PDF、DOCX、XLSX、CSV
- **极速问答**：init 一次性建库，ask 直接复用缓存秒级返回
- **双源合并**：向量检索 + FQA 标准答案联合输出
- **绿色免安装**：可打包为独立可执行文件，双击即用

## 四大核心命令

| 命令      | 功能         | 说明                                     |
| --------- | ------------ | ---------------------------------------- |
| `init`    | 初始化       | 唯一建库入口，全量扫描+一次性构建向量库  |
| `ask`     | 提问查询     | 直接复用缓存向量库，不扫描不重建         |
| `add-fqa` | 补充标准答案 | 自定义问答对，精准纠错兜底               |
| `clear`   | 一键清空     | 删除所有数据，恢复初始状态               |

## 快速开始

### 1. 安装依赖

```bash
cd coi
python3 setup.py
```

### 2. 初始化知识库

```bash
python3 main.py init /path/to/your/docs
```

### 3. 提问

```bash
python3 main.py ask "公司的退货政策是什么"
```

### 4. 补充标准答案

```bash
python3 main.py add-fqa "退货期限" "收货后7天内可申请退货"
```

### 5. 清空数据

```bash
python3 main.py clear --yes
```

## 项目结构

```text
question-and-answer/
├── README.md
├── .gitignore
├── .github/workflows/
│   └── build.yml           # CI 三平台自动打包
├── coi/                    # 程序源码
│   ├── main.py             # CLI 入口（init/ask/add-fqa/clear）
│   ├── config.py           # 数据目录管理
│   ├── models.py           # 数据模型
│   ├── scanner.py          # 文件扫描器
│   ├── chunker.py          # 文本提取与切块
│   ├── embedding.py        # 向量化引擎（支持离线模型）
│   ├── store.py            # ChromaDB 向量存储
│   ├── fqa.py              # FQA 标准答案管理
│   ├── query.py            # 双源查询引擎
│   ├── build.py            # PyInstaller 打包脚本
│   ├── download_model.py   # 模型预下载脚本
│   ├── setup.py            # 依赖安装脚本
│   ├── requirements.txt    # Python 运行时依赖
│   ├── tests/              # 测试套件（79 个测试用例）
│   │   ├── conftest.py     # 共享 fixtures
│   │   ├── test_config.py  # 配置模块测试
│   │   ├── test_scanner.py # 扫描器测试
│   │   ├── test_chunker.py # 文本提取与切块测试
│   │   ├── test_fqa.py     # FQA 管理测试
│   │   └── test_cli.py     # CLI 命令集成测试
│   └── coi_data/           # 数据目录（运行时自动生成）
│       ├── config.json     # 配置（文档路径）
│       ├── fqa.json        # FQA 标准答案
│       └── vector_db/      # 向量数据库
└── .kiro/specs/            # 需求与设计文档
    └── coi-refactor/
        ├── requirements.md
        ├── design.md
        └── tasks.md
```

## 数据存储

所有程序数据统一存放于 `coi/coi_data/` 目录，不使用系统隐藏路径或用户主目录。用户可直接手动删除 `coi_data/` 文件夹实现全部数据重置。

## 打包为可执行文件

### 自动打包（推荐）

项目配置了 GitHub Actions CI，推送 tag 时自动在三平台打包：

```bash
git tag v1.0.0
git push origin v1.0.0
```

CI 会自动：

1. 在 Windows / macOS / Linux 三个 runner 上分别打包
2. 下载 Embedding 模型并打入可执行文件
3. 生成 Release 并上传三平台可执行文件

### 手动打包（当前平台）

```bash
cd coi
pip install -r requirements.txt
python3 download_model.py   # 预下载模型（~470MB，一次性）
python3 build.py            # 打包
```

打包后在 `dist/` 目录生成独立可执行文件，内含模型，完全离线运行。

## 业务流程

```text
首次使用: coi init <文档目录> → 全量扫描 → 一次性建库
日常使用: coi ask "问题"    → 读取缓存 → 秒级返回
精准补全: coi add-fqa       → 自定义标准答案兜底
重置清空: coi clear         → 全部数据清零
```

## 核心约束

- 向量库仅由 init 命令一次性构建，ask 全程复用缓存，禁止自动重建
- clear 命令仅执行数据删除，禁止触发任何扫描/解析/向量化
- 问答输出固定双源合并：文档向量检索 + FQA 标准答案
- 所有数据强制存放在 coi_data/ 目录，禁止使用系统隐藏路径
- 本版本不做文档实时监听，文档变更后需重新执行 init

## 技术栈

- **Embedding 模型**: paraphrase-multilingual-MiniLM-L12-v2（384 维，多语言）
- **向量数据库**: ChromaDB（本地持久化，cosine 距离）
- **CLI 框架**: Click
- **打包工具**: PyInstaller
- **语言**: Python 3.9+

## 环境要求

**开发模式（源码运行）：**

- Python 3.9+
- 约 1GB 可用内存（模型加载）
- 首次运行需联网下载模型（约 470MB，一次性缓存到本地）

**打包后（可执行文件）：**

- 无需 Python 环境
- 无需联网（模型已内嵌）
- 约 1GB 可用内存

## 运行测试

```bash
cd coi
pip install pytest
python -m pytest tests/ -v
```

测试套件包含 79 个用例，覆盖：配置管理、文件扫描、文本提取、切块逻辑、FQA 管理、CLI 四大命令行为断言、数据目录约束、端到端流程。
