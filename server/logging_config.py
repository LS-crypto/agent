"""Uvicorn 日志：常见行附带中文说明。"""

from __future__ import annotations

import logging
import sys

# Uvicorn 固定文案 → 中文说明
_UVICORN_NOTES: list[tuple[str, str]] = [
    ("Will watch for changes in these directories", "文件变更时将自动重载（--reload）"),
    ("Started server process", "Uvicorn 工作进程已启动"),
    ("Waiting for application startup", "等待 FastAPI 应用初始化"),
    ("Application startup complete", "应用初始化完成，可处理请求"),
    ("Uvicorn running on", "HTTP 服务已监听，等待前端/客户端连接"),
    ("Started reloader process", "热重载监控进程已启动（--reload）"),
    ("Stopping reloader process", "热重载监控进程已停止"),
    ("Shutting down", "正在关闭 HTTP 服务"),
    ("Finished server process", "工作进程已退出"),
]


class AnnotatedFormatter(logging.Formatter):
    """在 Uvicorn 日志行末尾追加  --中文说明。"""

    def format(self, record: logging.LogRecord) -> str:
        line = super().format(record)
        msg = record.getMessage()
        for key, note in _UVICORN_NOTES:
            if key in msg:
                return f"{line}  --{note}"
        return line


def _ensure_utf8_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass


def setup_uvicorn_logging() -> None:
    """给 uvicorn / uvicorn.error 的 handler 套上 AnnotatedFormatter。"""
    _ensure_utf8_stdout()
    formatter = AnnotatedFormatter("%(levelname)s:     %(message)s")
    for name in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(name)
        for handler in logger.handlers:
            handler.setFormatter(formatter)


def setup_app_logging() -> None:
    """应用自身日志（请求、启动步骤），格式与 console.out 一致。"""
    _ensure_utf8_stdout()
    logger = logging.getLogger("sheldon.agent")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.propagate = False


def disable_uvicorn_access_log() -> None:
    """关闭 Uvicorn 默认 access log，改由中间件输出带中文说明的版本。"""
    logging.getLogger("uvicorn.access").disabled = True
