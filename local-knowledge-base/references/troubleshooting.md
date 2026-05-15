# 故障排除指南

## 常见问题

### 依赖安装失败

**问题**：`setup_env.py` 执行报错

**解决方案**：
1. 确认 Python 版本 >= 3.9：`python3 --version`
2. 确认 pip 可用：`python3 -m pip --version`
3. 如果网络问题，尝试使用镜像源：
   ```bash
   python3 -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

### 模型下载慢或失败

**问题**：首次运行时模型下载超时

**解决方案**：
1. 模型约 470MB，确保网络稳定
2. 可手动设置 HuggingFace 镜像：
   ```bash
   export HF_ENDPOINT=https://hf-mirror.com
   ```
3. 重新运行命令，会从断点续传

### 内存不足

**问题**：运行时报 MemoryError 或被系统 kill

**解决方案**：
- 模型加载需要约 1GB 内存
- 关闭其他大型应用释放内存
- 如果文档量很大，可以分批扫描不同子文件夹

### 文件未被索引

**问题**：scan 后某些文件没有出现在结果中

**解决方案**：
- 检查文件扩展名是否在支持列表中（.txt .md .doc .docx .xls .xlsx .pdf）
- 确认文件不是空文件
- 确认文件编码为 UTF-8（TXT/MD 文件）
- 检查文件是否损坏（Word/Excel/PDF）

### 查询结果不相关

**问题**：查询返回的内容与问题不相关

**解决方案**：
1. 尝试用不同措辞重新提问
2. 使用更具体的关键词
3. 添加 FQA 纠错记录来覆盖不准确的结果
4. 如果文档刚更新，确认已执行 `scan` 同步

### ChromaDB 数据损坏

**问题**：查询或扫描时报 ChromaDB 相关错误

**解决方案**：
```bash
# 删除向量数据库目录并重建
rm -rf ./chroma_data
python3 <SKILL_PATH>/scripts/kb.py rebuild --folder <文件夹路径>
```

### Windows 兼容性

**问题**：Windows 上运行报错

**解决方案**：
- 使用 `python` 而非 `python3`
- 路径使用反斜杠或原始字符串：`--folder .\my_docs`
- 如果 pip 安装 chromadb 失败，尝试安装 Visual C++ Build Tools

## 性能参考

| 文档数量 | 首次索引时间 | 增量同步时间 | 查询响应时间 |
|----------|-------------|-------------|-------------|
| 10 个文件 | ~30 秒 | ~2 秒 | ~1 秒 |
| 100 个文件 | ~5 分钟 | ~5 秒 | ~1 秒 |
| 1000 个文件 | ~50 分钟 | ~10 秒 | ~1 秒 |

注：首次索引包含模型加载时间（约 10 秒），后续操作模型已缓存在内存中。
