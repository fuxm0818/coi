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

按以下顺序执行：

### 第 1 步：检查是否已安装

```bash
coi --help
```

- 输出帮助信息 → 已安装，跳到第 3 步
- command not found → 执行第 2 步

### 第 2 步：下载安装

GitHub 仓库：https://github.com/fuxm0818/coi

先用 GitHub API 获取最新版本的下载地址：

```bash
curl -s https://api.github.com/repos/fuxm0818/coi/releases/latest | grep "browser_download_url"
```

然后根据当前平台下载对应文件：

**Linux：**
```bash
curl -L "https://github.com/fuxm0818/coi/releases/latest/download/coi-linux" -o ./coi
chmod +x ./coi
./coi --help
```

**macOS：**
```bash
curl -L "https://github.com/fuxm0818/coi/releases/latest/download/coi-macos" -o ./coi
chmod +x ./coi
xattr -d com.apple.quarantine ./coi 2>/dev/null
./coi --help
```

**Windows（PowerShell）：**
```powershell
Invoke-WebRequest -Uri "https://github.com/fuxm0818/coi/releases/latest/download/coi-windows.exe" -OutFile ".\coi.exe"
.\coi.exe --help
```

注意事项：
- 优先下载到当前工作目录（避免权限问题）
- 下载后必须验证 `./coi --help` 输出正常
- 如果下载失败（404 或网络错误），告诉用户手动从 https://github.com/fuxm0818/coi/releases 下载
- 使用 `-L` 参数跟随重定向（GitHub 下载链接会 302 跳转）

### 第 3 步：询问文档路径

对用户说：**「请告诉我你的文档文件夹路径，我来帮你构建知识库。」**

等待用户回复。

### 第 4 步：初始化知识库

```bash
./coi init <用户提供的路径>
```

将输出展示给用户，确认成功。如果报错「路径不存在」，请用户重新确认路径。

### 第 5 步：问答

用户每次提问时执行：

```bash
./coi ask "用户的问题"
```

将结果展示给用户。

---

## 其他操作

| 用户意图 | 执行命令 | 说明 |
| -------- | -------- | ---- |
| 补充标准答案 | `./coi add-fqa "问题" "答案"` | 下次相似提问会优先返回此答案 |
| 清空重来 | `./coi clear --yes` | 清空后需重新 init |
| 文档有更新 | `./coi init <路径>` | 重新执行 init 覆盖旧库 |

---

## 关键规则

- `ask` 只读缓存，不扫描不重建，所以很快
- 所有数据在 coi 同级的 `coi_data/` 目录
- 安装完成后完全离线，不需要网络
- 用户没有明确要使用时，不要自动开始安装流程
