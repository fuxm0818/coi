"""文件扫描与变更检测"""

import os
from typing import Dict

from src.models import FileChange, ScanResult

# 支持的文件扩展名集合
SUPPORTED_EXTENSIONS = {".txt", ".md", ".doc", ".docx", ".xls", ".xlsx", ".pdf"}


class FileScanner:
    """文件扫描器，递归遍历知识库文件夹并检测文件变更。

    通过对比文件系统状态与向量库已有记录，生成包含新增、修改、删除的变更清单。
    """

    def scan(self, folder_path: str, existing_records: Dict[str, int]) -> ScanResult:
        """递归遍历文件夹，对比向量库记录，生成变更清单。

        Args:
            folder_path: 知识库文件夹路径（绝对路径或相对路径）
            existing_records: 向量库已索引文件的映射，key 为相对路径，value 为 last_modified 时间戳（毫秒）

        Returns:
            ScanResult: 包含变更列表、未变更文件数和错误列表

        Raises:
            FileNotFoundError: 当 folder_path 不存在时
            NotADirectoryError: 当 folder_path 不是目录时
        """
        # 验证路径有效性
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"知识库路径不存在: {folder_path}")
        if not os.path.isdir(folder_path):
            raise NotADirectoryError(f"知识库路径不是目录: {folder_path}")

        result = ScanResult()
        # 跟踪在文件系统中找到的已支持文件（相对路径集合）
        found_files = set()

        # 递归遍历文件夹
        for root, _dirs, files in os.walk(folder_path):
            for filename in files:
                # 检查文件扩展名是否支持
                ext = os.path.splitext(filename)[1].lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    continue

                absolute_path = os.path.join(root, filename)
                relative_path = os.path.relpath(absolute_path, folder_path)
                found_files.add(relative_path)

                # 获取文件最后修改时间（毫秒）
                try:
                    last_modified = int(os.path.getmtime(absolute_path) * 1000)
                except OSError as e:
                    result.errors.append({
                        "path": relative_path,
                        "reason": str(e),
                    })
                    continue

                if relative_path not in existing_records:
                    # 新文件：向量库中无匹配记录
                    result.changes.append(FileChange(
                        file_path=relative_path,
                        absolute_path=absolute_path,
                        status="added",
                        last_modified=last_modified,
                    ))
                elif existing_records[relative_path] != last_modified:
                    # 修改文件：时间戳不一致
                    result.changes.append(FileChange(
                        file_path=relative_path,
                        absolute_path=absolute_path,
                        status="modified",
                        last_modified=last_modified,
                    ))
                else:
                    # 未变更
                    result.unchanged += 1

        # 检测已删除文件：向量库有记录但文件系统中不存在
        for file_path in existing_records:
            if file_path not in found_files:
                absolute_path = os.path.join(folder_path, file_path)
                result.changes.append(FileChange(
                    file_path=file_path,
                    absolute_path=absolute_path,
                    status="deleted",
                    last_modified=None,
                ))

        return result
