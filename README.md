# COI（我问你答）

本地离线文档问答工具。全程不调用任何外部大模型、不上网、无网络请求，纯本地独立运行，所有数据本地化存储，保障隐私与离线可用性。

## 核心特性

- **纯离线运行**：零网络依赖、零外部大模型调用、零数据上传
- **多格式支持**：TXT、MD、PDF、DOCX、XLSX、CSV、PPTX、PPT、RTF
- **极速问答**：init 一次性建库，ask 直接复用缓存秒级返回
- **双源合并**：向量检索 + FQA 标准答案联合输出
- **绿色免安装**：单文件可执行程序（~150MB），双击即用

## 快速开始

### 使用打包好的可执行文件（推荐）

从 [Releases](../../releases) 下载对应平台的文件，直接运行：

```bash
# macOS 首次需解除安全限制
xattr -d com.apple.quarantine ./coi

# 初始化知识库
./coi init /path/to/your/docs

# 提问
./coi ask "公司的退货政策是什么"

# 补充标准答案
./coi add-fqa "退货期限" "收货后7天内可申请退货"

# 清空数据
./coi clear --yes
```

### 使用源码运行（开发模式）

```bash
cd coi
python3 setup.py                          # 安装依赖
python3 main.py init /path/to/your/docs   # 初始化
python3 main.py ask "你的问题"             # 提问
python3 main.py add-fqa "问题" "答案"      # 补充标准答案
python3 main.py clear --yes               # 清空
```

## 四大命令

| 命令      | 功能         | 说明                                    |
| --------- | ------------ | --------------------------------------- |
| `init`    | 初始化       | 唯一建库入口，全量扫描+一次性构建向量库 |
| `ask`     | 提问查询     | 直接复用缓存向量库，不扫描不重建        |
| `add-fqa` | 补充标准答案 | 自定义问答对，精准纠错兜底              |
| `clear`   | 一键清空     | 删除所有数据，恢复初始状态              |

## 业务流程

```text
首次使用: coi init <文档目录> → 全量扫描 → 一次性建库
日常使用: coi ask "问题"    → 读取缓存 → 秒级返回
精准补全: coi add-fqa       → 自定义标准答案兜底
重置清空: coi clear         → 全部数据清零
```

## 数据存储

所有数据统一存放于程序同级 `coi_data/` 目录，结构透明：

```text
coi_data/
├── config.json     # 配置（绑定的文档路径）
├── fqa.json        # FQA 标准答案
└── vector_db/      # 向量数据库
```

- 不使用系统隐藏路径或用户主目录
- 手动删除 `coi_data/` 等同于执行 `clear`

## 核心约束

- 向量库仅由 `init` 一次性构建，`ask` 全程复用缓存，禁止自动重建
- `clear` 仅执行数据删除，禁止触发任何扫描/解析/向量化
- 问答输出固定双源合并：文档向量检索 + FQA 标准答案
- 所有数据强制存放在 `coi_data/` 目录
- 文档变更后需重新执行 `init` 更新向量库

## 打包

### 本地打包（测试用）

```bash
cd coi
pip install -r requirements.txt pyinstaller
python3 download_model.py    # 下载 ONNX 模型（~95MB，一次性）
python3 build.py             # 打包（约 1-2 分钟）
./dist/coi --help            # 验证
```

### GitHub Actions 自动打包（发布用）

推送 tag 自动在三平台打包并创建 Release：

```bash
git tag v1.0.0
git push origin v1.0.0
```

也可在 Actions 页面手动触发 Run workflow 测试打包。

### 打包产物

| 平台              | 文件名    | 大小   |
| ----------------- | --------- | ------ |
| Linux x64         | `coi`     | ~150MB |
| macOS (ARM/Intel) | `coi`     | ~150MB |
| Windows x64       | `coi.exe` | ~150MB |

单文件，内含 ONNX 模型 + 所有依赖，完全离线运行。

### macOS 安全提示

首次运行可能提示"无法验证开发者"，执行：

```bash
xattr -d com.apple.quarantine ./coi
```

## 运行测试

```bash
cd coi
pip install pytest
python -m pytest tests/ -v
```

79 个测试用例，覆盖：配置管理、文件扫描、文本提取、切块逻辑、FQA 管理、CLI 命令行为、数据目录约束、端到端流程。

## 技术栈

| 组件       | 技术                                                  |
| ---------- | ----------------------------------------------------- |
| Embedding  | BAAI/bge-small-zh-v1.5（512 维，中文检索专精）        |
| 推理引擎   | ONNX Runtime（无 PyTorch，体积小速度快）              |
| 向量数据库 | ChromaDB（本地持久化，cosine 距离）                   |
| CLI        | Click                                                 |
| 打包       | PyInstaller（--onefile）                              |
| 语言       | Python 3.9+                                           |

## 环境要求

**源码运行：** Python 3.9+，首次需联网下载模型（~95MB）

**打包后：** 无需 Python，无需联网，单文件约 150MB

## 项目结构

```text
question-and-answer/
├── README.md
├── .gitignore
├── .github/workflows/
│   └── build.yml              # CI 三平台自动打包
└── coi/                       # 程序源码
    ├── main.py                # CLI 入口
    ├── config.py              # 数据目录管理
    ├── models.py              # 数据模型
    ├── scanner.py             # 文件扫描器
    ├── chunker.py             # 文本提取与切块
    ├── embedding.py           # ONNX 向量化引擎
    ├── store.py               # ChromaDB 向量存储
    ├── fqa.py                 # FQA 标准答案管理
    ├── query.py               # 双源查询引擎
    ├── build.py               # 打包脚本
    ├── download_model.py      # 模型下载脚本
    ├── setup.py               # 依赖安装脚本
    └── requirements.txt       # 运行时依赖

```
