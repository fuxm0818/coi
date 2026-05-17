# COI 跨平台打包指南

## 概述

COI 使用 PyInstaller `--onefile` 模式打包为单个可执行文件，内嵌 ONNX 模型。
产物约 150-200MB，用户下载后直接运行，无需安装 Python 或任何依赖。

---

## 本地打包测试

**推荐在本地先打包验证，确认无误后再推 GitHub 自动打包。**

### 一次性准备

```bash
cd coi
pip install -r requirements.txt pyinstaller
python3 download_model.py    # 下载 ONNX 模型（~95MB）
```

### 打包 + 测试

```bash
python3 build.py             # 打包（约 1-2 分钟）
./dist/coi --help            # 验证帮助信息
./dist/coi init ~/docs       # 测试初始化
./dist/coi ask "测试问题"     # 测试查询
./dist/coi add-fqa "Q" "A"  # 测试 FQA
./dist/coi clear --yes       # 测试清空
```

### 确认后推送

```bash
git add .
git commit -m "your message"
git push origin main
```

---

## GitHub Actions 自动打包

### 方式一：推送 Tag（创建 Release）

```bash
git tag v1.0.0
git push origin v1.0.0
```

CI 自动在三平台打包，完成后创建 Release 附带下载文件。

### 方式二：手动触发（仅测试）

1. GitHub 仓库 → Actions → Build COI Executables
2. 点击 Run workflow → 确认

从 Artifacts 区域下载产物（保留 7 天）。

---

## 打包产物

| 平台              | 文件名   | 大小（约） |
| ----------------- | -------- | ---------- |
| Linux x64         | `coi`    | ~150MB     |
| macOS (ARM/Intel) | `coi`    | ~150MB     |
| Windows x64       | `coi.exe`| ~150MB     |

产物是单个可执行文件，内含：

- ONNX Runtime 推理引擎
- bge-small-zh-v1.5 模型（~95MB）
- ChromaDB、Click 等所有依赖

---

## 用户使用方式

### macOS

```bash
# 解除安全限制（首次）
xattr -d com.apple.quarantine ./coi

# 使用
./coi init /path/to/docs
./coi ask "你的问题"
```

### Linux

```bash
chmod +x ./coi
./coi init /path/to/docs
./coi ask "你的问题"
```

### Windows

```powershell
.\coi.exe init C:\path\to\docs
.\coi.exe ask "你的问题"
```

---

## CI 流程

```text
push tag v* → GitHub Actions 触发
  ├── ubuntu-latest:  pip install → download model → pyinstaller → upload coi
  ├── macos-latest:   pip install → download model → pyinstaller → upload coi
  └── windows-latest: pip install → download model → pyinstaller → upload coi.exe
                                          ↓
                              create Release + attach files
```

---

## 常见问题

### macOS 提示"无法验证开发者"

```bash
xattr -d com.apple.quarantine ./coi
```

或：系统设置 → 隐私与安全性 → 点击"仍要打开"

### 打包失败：磁盘空间不足

不应再出现此问题。ONNX Runtime 方案总依赖约 200MB，远小于 GitHub runner 的 14GB 可用空间。

### 如何更新版本

```bash
git tag v1.1.0
git push origin v1.1.0
```

每次新 tag 自动触发打包并创建新 Release。
