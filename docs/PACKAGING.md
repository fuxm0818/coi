# COI 跨平台打包指南

本文档说明如何通过 GitHub Actions 自动打包 COI 为 Windows / macOS / Linux 三平台独立可执行文件。

---

## 前置条件

1. 项目已推送到 GitHub 仓库
2. 仓库中包含 `.github/workflows/build.yml` 文件（项目已自带）
3. 你有仓库的 push 权限

---

## 方式一：推送 Tag 自动触发（推荐）

### 步骤

```bash
# 1. 确保所有代码已提交
git add .
git commit -m "feat: COI v1.0.0"

# 2. 创建版本 tag
git tag v1.0.0

# 3. 推送代码和 tag 到 GitHub
git push origin main
git push origin v1.0.0
```

### 触发后会发生什么

1. GitHub Actions 检测到 `v*` 格式的 tag 推送
2. 自动在三个平台的 runner 上并行执行打包：
   - `ubuntu-latest` → 生成 `coi-linux.tar.gz`
   - `macos-latest` → 生成 `coi-macos.tar.gz`
   - `windows-latest` → 生成 `coi-windows.zip`
3. 每个平台的打包流程：
   - 安装 Python 3.11
   - 安装运行时依赖 + PyInstaller
   - 下载 Embedding 模型（~470MB）
   - 执行 PyInstaller 打包（模型内嵌到可执行文件）
   - 压缩为发布包
4. 三平台全部完成后，自动创建 GitHub Release
5. Release 页面附带三个下载文件

### 下载产物

打包完成后，进入仓库的 **Releases** 页面：

```
https://github.com/<你的用户名>/<仓库名>/releases
```

可下载：
- `coi-linux.tar.gz` — Linux x64 可执行文件
- `coi-macos.tar.gz` — macOS 可执行文件
- `coi-windows.zip` — Windows x64 可执行文件

---

## 方式二：手动触发（无需创建 Tag）

适用于测试打包流程，不创建 Release。

### 步骤

1. 打开 GitHub 仓库页面
2. 点击顶部 **Actions** 标签
3. 左侧选择 **Build COI Executables** workflow
4. 点击右侧 **Run workflow** 按钮
5. 选择分支（默认 main），点击 **Run workflow** 确认

### 下载产物

手动触发不会创建 Release，但可以从 Actions 运行记录中下载 Artifacts：

1. 进入 Actions → 点击对应的运行记录
2. 页面底部 **Artifacts** 区域可下载：
   - `coi-linux`
   - `coi-macos`
   - `coi-windows`

Artifacts 保留 7 天后自动删除。

---

## 打包产物说明

| 文件 | 平台 | 解压后 | 大小（约） |
|------|------|--------|-----------|
| `coi-linux.tar.gz` | Linux x64 | `coi` | ~800MB |
| `coi-macos.tar.gz` | macOS (Apple Silicon/Intel) | `coi` | ~800MB |
| `coi-windows.zip` | Windows x64 | `coi.exe` | ~800MB |

> 文件较大是因为内嵌了 Embedding 模型（~470MB）+ PyTorch 运行时。
> 这确保了完全离线运行，用户无需安装任何依赖。

---

## 用户使用方式

### Linux

```bash
tar -xzf coi-linux.tar.gz
chmod +x coi
./coi init /path/to/docs
./coi ask "你的问题"
```

### macOS

```bash
tar -xzf coi-macos.tar.gz
chmod +x coi
./coi init /path/to/docs
./coi ask "你的问题"
```

> macOS 首次运行可能提示"无法验证开发者"，需要在 系统设置 → 隐私与安全性 中点击"仍要打开"。

### Windows

```powershell
# 解压 coi-windows.zip，得到 coi.exe
.\coi.exe init C:\path\to\docs
.\coi.exe ask "你的问题"
```

---

## CI 流程详解

```
┌─────────────────────────────────────────────────────────┐
│                    push tag v*                           │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ ubuntu-latest│ │ macos-latest │ │windows-latest│
├──────────────┤ ├──────────────┤ ├──────────────┤
│ pip install  │ │ pip install  │ │ pip install  │
│ download_model│ │ download_model│ │ download_model│
│ build.py     │ │ build.py     │ │ build.py     │
│ tar -czf     │ │ tar -czf     │ │ Compress-Arch│
├──────────────┤ ├──────────────┤ ├──────────────┤
│ upload       │ │ upload       │ │ upload       │
│ artifact     │ │ artifact     │ │ artifact     │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┼────────────────┘
                        ▼
              ┌──────────────────┐
              │  release job     │
              ├──────────────────┤
              │ download all     │
              │ create Release   │
              │ attach 3 files   │
              └──────────────────┘
```

---

## 常见问题

### Q: 打包需要多长时间？

约 15-30 分钟（主要耗时在下载模型和 PyInstaller 打包）。三平台并行执行，总耗时取决于最慢的那个。

### Q: 打包失败怎么办？

1. 进入 Actions → 点击失败的运行记录
2. 展开失败的 step 查看日志
3. 常见原因：
   - 模型下载超时 → 重新触发即可
   - 依赖安装失败 → 检查 requirements.txt 版本兼容性
   - PyInstaller 打包失败 → 检查 hidden-import 是否遗漏

### Q: 如何更新版本？

```bash
# 修改代码后
git add .
git commit -m "feat: 新功能描述"
git tag v1.1.0
git push origin main
git push origin v1.1.0
```

每次推送新 tag 都会自动触发打包并创建新 Release。

### Q: 可以只打包某一个平台吗？

当前 workflow 固定三平台并行。如需单平台打包，可以手动在本地执行：

```bash
cd coi
pip install -r requirements.txt
pip install pyinstaller
python download_model.py
python build.py
```

这只会生成当前操作系统的可执行文件。

### Q: 打包后的文件为什么这么大？

因为内嵌了：
- Embedding 模型文件（~470MB）
- PyTorch 运行时（~200MB）
- ChromaDB + 其他依赖（~100MB）

这是"完全离线、绿色免安装"的代价。用户拿到文件后无需任何额外操作即可使用。

### Q: macOS 提示"无法打开，因为无法验证开发者"？

这是 macOS Gatekeeper 安全机制。解决方法：

1. 系统设置 → 隐私与安全性 → 找到被阻止的 `coi` → 点击"仍要打开"
2. 或者在终端执行：`xattr -d com.apple.quarantine ./coi`

---

## 相关文件

| 文件 | 作用 |
|------|------|
| `.github/workflows/build.yml` | CI 打包流程定义 |
| `coi/build.py` | PyInstaller 打包脚本 |
| `coi/download_model.py` | 模型预下载脚本 |
| `coi/requirements.txt` | 运行时依赖清单 |
