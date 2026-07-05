"""文件系统工具：读写改列，限制在用户沙箱内。"""

from __future__ import annotations

from core.tools.policy import MAX_LIST_ENTRIES, MAX_READ_CHARS, MAX_WRITE_BYTES, is_sensitive_path
from core.tools.quota import check_workspace_quota
from core.tools.registry import ToolRegistry
from core.tools.sandbox import WorkspaceSandbox


class FileSystemTools:
    def __init__(self, user_id: str) -> None:
        self.sandbox = WorkspaceSandbox(user_id)

    def read_file(self, file_path: str) -> dict:
        resolved = self.sandbox.resolve(file_path, check_sensitive=True)
        if isinstance(resolved, dict):
            return resolved
        if not resolved.is_file():
            return {"success": False, "error": f"文件不存在: {file_path}"}
        content = resolved.read_text(encoding="utf-8")
        truncated = len(content) > MAX_READ_CHARS
        if truncated:
            content = content[:MAX_READ_CHARS]
        return {
            "success": True,
            "content": content,
            "truncated": truncated,
            "path": self.sandbox.rel(resolved),
        }

    def write_file(self, file_path: str, content: str) -> dict:
        if is_sensitive_path(file_path):
            return {
                "success": False,
                "error": "敏感文件受策略保护，禁止写入",
                "policy": "sensitive_file",
            }

        resolved = self.sandbox.resolve(file_path, check_sensitive=False)
        if isinstance(resolved, dict):
            return resolved

        encoded = content.encode("utf-8")
        if len(encoded) > MAX_WRITE_BYTES:
            return {
                "success": False,
                "error": f"写入内容超过限制 ({MAX_WRITE_BYTES // 1024}KB)",
                "policy": "write_limit",
            }

        quota_err = check_workspace_quota(
            self.sandbox.user_id,
            extra_bytes=len(encoded),
            replace_path=resolved if resolved.is_file() else None,
        )
        if quota_err is not None:
            return quota_err

        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_bytes(encoded)
        return {
            "success": True,
            "path": self.sandbox.rel(resolved),
            "bytes_written": len(encoded),
        }

    def edit_file(self, file_path: str, old_string: str, new_string: str) -> dict:
        resolved = self.sandbox.resolve(file_path, check_sensitive=True)
        if isinstance(resolved, dict):
            return resolved
        if not resolved.is_file():
            return {"success": False, "error": f"文件不存在: {file_path}"}

        new_bytes = new_string.encode("utf-8")
        if len(new_bytes) > MAX_WRITE_BYTES:
            return {
                "success": False,
                "error": f"替换内容超过限制 ({MAX_WRITE_BYTES // 1024}KB)",
                "policy": "write_limit",
            }

        content = resolved.read_text(encoding="utf-8")
        if old_string not in content:
            return {"success": False, "error": "未找到要替换的 old_string"}
        updated = content.replace(old_string, new_string, 1)
        updated_bytes = updated.encode("utf-8")
        if len(updated_bytes) > MAX_WRITE_BYTES:
            return {
                "success": False,
                "error": f"编辑后文件超过限制 ({MAX_WRITE_BYTES // 1024}KB)",
                "policy": "write_limit",
            }

        quota_err = check_workspace_quota(
            self.sandbox.user_id,
            extra_bytes=len(updated_bytes),
            replace_path=resolved,
        )
        if quota_err is not None:
            return quota_err

        resolved.write_text(updated, encoding="utf-8")
        return {
            "success": True,
            "path": self.sandbox.rel(resolved),
            "replacements": 1,
        }

    def list_dir(self, dir_path: str = ".") -> dict:
        resolved = self.sandbox.resolve(dir_path, check_sensitive=True)
        if isinstance(resolved, dict):
            return resolved
        if not resolved.is_dir():
            return {"success": False, "error": f"目录不存在: {dir_path}"}

        entries = []
        truncated = False
        for item in sorted(resolved.iterdir()):
            rel = self.sandbox.rel(item)
            if is_sensitive_path(rel):
                continue
            entries.append(
                {
                    "name": item.name,
                    "path": rel,
                    "type": "dir" if item.is_dir() else "file",
                }
            )
            if len(entries) >= MAX_LIST_ENTRIES:
                truncated = True
                break

        result: dict = {
            "success": True,
            "entries": entries,
            "path": dir_path,
        }
        if truncated:
            result["truncated"] = True
        return result


def register_filesystem_tools(registry: ToolRegistry, user_id: str) -> None:
    fs = FileSystemTools(user_id)
    registry.register(
        name="read_file",
        description="读取沙箱内指定文件的文本内容。路径相对于用户项目根目录。",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "文件相对路径"},
            },
            "required": ["file_path"],
        },
        handler=fs.read_file,
    )
    registry.register(
        name="write_file",
        description="在沙箱内创建或覆盖文件。路径相对于用户项目根目录。",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "文件相对路径"},
                "content": {"type": "string", "description": "写入的全文内容"},
            },
            "required": ["file_path", "content"],
        },
        handler=fs.write_file,
    )
    registry.register(
        name="edit_file",
        description="在沙箱内替换文件中唯一一段文本。old_string 必须在文件中存在且仅替换第一处。",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "文件相对路径"},
                "old_string": {"type": "string", "description": "要被替换的原文"},
                "new_string": {"type": "string", "description": "替换后的新文"},
            },
            "required": ["file_path", "old_string", "new_string"],
        },
        handler=fs.edit_file,
    )
    registry.register(
        name="list_dir",
        description="列出沙箱内目录下的文件和子目录。dir_path 默认为项目根目录。",
        parameters={
            "type": "object",
            "properties": {
                "dir_path": {
                    "type": "string",
                    "description": "目录相对路径，默认 .",
                },
            },
            "required": [],
        },
        handler=fs.list_dir,
    )


def build_filesystem_registry(user_id: str) -> ToolRegistry:
    """仅文件系统工具（示例/demo 用）。"""
    registry = ToolRegistry()
    register_filesystem_tools(registry, user_id)
    return registry
