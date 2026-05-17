"""文件扫描器

递归遍历文档文件夹，收集所有支持格式的文件。
排除隐藏文件和隐藏目录（名称以 . 开头）。
"""

import os

from models import FileChange, ScanResult

# 支持的文件扩展名（小写）
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".xlsx", ".csv", ".pptx", ".ppt"}


class FileScanner:
    """文件扫描器

    递归遍历指定目录，收集所有支持格式的非隐藏文件。
    """

    def scan(self, folder_path: str) -> ScanResult:
        """递归扫描目录，返回所有支持格式的文件列表。

        - 排除隐藏文件和隐藏目录（名称以 . 开头）
        - 扩展名匹配不区分大小写
        - 遇到文件系统错误时跳过并记录

        Args:
            folder_path: 文档文件夹绝对路径

        Returns:
            ScanResult 包含发现的文件列表和错误列表

        Raises:
            FileNotFoundError: 路径不存在
            NotADirectoryError: 路径不是目录
        """
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"文档路径不存在: {folder_path}")
        if not os.path.isdir(folder_path):
            raise NotADirectoryError(f"路径不是目录: {folder_path}")

        result = ScanResult()

        for root, dirs, files in os.walk(folder_path):
            # 排除隐藏目录：修改 dirs 列表以阻止 os.walk 进入
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            for filename in files:
                # 排除隐藏文件
                if filename.startswith("."):
                    continue

                # 检查扩展名（不区分大小写）
                ext = os.path.splitext(filename)[1].lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    continue

                absolute_path = os.path.join(root, filename)
                relative_path = os.path.relpath(absolute_path, folder_path)

                # 获取文件修改时间
                try:
                    last_modified = int(os.path.getmtime(absolute_path) * 1000)
                except OSError as e:
                    result.errors.append({
                        "path": relative_path,
                        "reason": str(e),
                    })
                    continue

                result.changes.append(FileChange(
                    file_path=relative_path,
                    absolute_path=absolute_path,
                    status="added",
                    last_modified=last_modified,
                ))

        return result
