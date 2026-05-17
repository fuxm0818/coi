---
name: coi-qa
description: "我问你答（COI）本地离线文档问答工具。当用户提到「我问你答」、「COI」、「本地文档问答」、「离线问答」、「知识库问答」、「文档检索」时必须触发此 skill。即使用户只是随口提到「我问你答」四个字，也应该立即触发。"
---

# 我问你答（COI）

一个本地离线文档问答工具。用户指定文档文件夹，程序一次性构建向量知识库，之后可反复提问获得秒级响应。纯本地运行，不调用任何外部大模型，不上网。

支持文档格式：TXT、MD、PDF、DOCX、XLSX、CSV

---

## 当用户询问这个技能是什么时

直接告诉用户：

> 「我问你答」是一个本地离线文档问答工具。你只需要指定一个文档文件夹，它会自动构建知识库。之后你随时可以用自然语言提问，秒级返回答案。全程离线运行，不上传任何数据。
>
> 如果你想开始使用，请告诉我你的文档文件夹路径。

不要在用户只是询问时就开始安装。等用户明确表示要使用时再执行安装流程。

---

## 当用户要使用此工具时

### 第 1 步：检查是否已安装（按顺序尝试以下路径）

COI 可能已经安装在以下位置之一，按顺序检查：

```bash
# 检查是否在 PATH 中
which coi 2>/dev/null || where coi 2>/dev/null

# 检查常见安装位置
ls /usr/local/bin/coi 2>/dev/null
ls ~/.local/bin/coi 2>/dev/null
ls ~/coi 2>/dev/null
ls ./coi 2>/dev/null
```

**只要在任何位置找到了 coi 可执行文件，就不需要重新下载。** 记住找到的路径，后续直接用该路径执行。

如果所有位置都找不到 → 执行第 2 步下载安装。

### 第 2 步：下载安装（仅在第 1 步确认不存在时执行）

GitHub 仓库：https://github.com/fuxm0818/coi

**安装到固定位置（避免每次会话重复下载）：**

**Linux：**
```bash
mkdir -p ~/.local/bin
curl -L "https://github.com/fuxm0818/coi/releases/latest/download/coi-linux" -o ~/.local/bin/coi
chmod +x ~/.local/bin/coi
~/.local/bin/coi --help
```

**macOS：**
```bash
mkdir -p ~/.local/bin
curl -L "https://github.com/fuxm0818/coi/releases/latest/download/coi-macos" -o ~/.local/bin/coi
chmod +x ~/.local/bin/coi
xattr -d com.apple.quarantine ~/.local/bin/coi 2>/dev/null
~/.local/bin/coi --help
```

**Windows（PowerShell）：**
```powershell
$coiDir = "$env:LOCALAPPDATA\coi"
New-Item -ItemType Directory -Force -Path $coiDir | Out-Null
Invoke-WebRequest -Uri "https://github.com/fuxm0818/coi/releases/latest/download/coi-windows.exe" -OutFile "$coiDir\coi.exe"
& "$coiDir\coi.exe" --help
```

安装完成后验证 `--help` 输出正常。

### 第 3 步：检查是否已有知识库

```bash
coi ask "测试"
```

- 如果返回检索结果 → 知识库已存在，直接跳到第 5 步回答用户问题
- 如果报错「尚未初始化」→ 执行第 4 步

### 第 4 步：初始化知识库（仅在没有知识库时执行）

询问用户：**「请告诉我你的文档文件夹路径，我来帮你构建知识库。」**

等待用户提供路径后执行：

```bash
coi init <用户提供的路径>
```

### 第 5 步：回答用户问题

```bash
coi ask "用户的问题"
```

将结果展示给用户。每次用户提新问题，重复执行此命令。

---

## 执行流程总结

```
触发 skill
  → 找到 coi 可执行文件了吗？
     是 → 知识库存在吗？（试执行 coi ask "测试"）
            是 → 直接回答用户问题
            否 → 问用户要文档路径 → init → 回答问题
     否 → 下载安装到 ~/.local/bin → 问用户要文档路径 → init → 回答问题
```

**核心原则：不要重复做已经做过的事。已安装就不下载，已初始化就不重新 init。**

---

## 其他操作

| 用户意图 | 执行命令 | 说明 |
| -------- | -------- | ---- |
| 补充标准答案 | `coi add-fqa "问题" "答案"` | 下次相似提问会优先返回此答案 |
| 清空重来 | `coi clear --yes` | 清空后需重新 init |
| 文档有更新 | `coi init <路径>` | 重新执行 init 覆盖旧库 |

---

## 关键规则

- `coi ask` 只读缓存，不扫描不重建，所以很快
- 所有数据在 coi 同级的 `coi_data/` 目录
- 安装完成后完全离线，不需要网络
- **不要每次会话都重新下载安装，先检查是否已存在**
- **不要每次都重新 init，先检查知识库是否已存在**
