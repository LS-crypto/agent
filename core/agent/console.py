"""终端输出工具：每行附带中文说明，便于理解执行过程。"""

from __future__ import annotations

import json
from typing import Any


def out(text: str, note: str) -> None:
    """打印一行：原文 + 中文说明。"""
    print(f"{text}  --{note}", flush=True)


def step(title: str, note: str) -> None:
    """打印一个步骤标题。"""
    out(f">>> {title}", note)


def tool(name: str, args: dict[str, Any], note: str) -> None:
    """打印工具调用。"""
    args_text = json.dumps(args, ensure_ascii=False)
    out(f"[工具] {name}({args_text})", note)


def tool_result(result: str, note: str) -> None:
    """打印工具返回结果。"""
    out(f"[工具结果] {result}", note)


def answer(text: str, note: str) -> None:
    """打印模型最终回复。"""
    out(f"[回复] {text}", note)


def warn(text: str, note: str) -> None:
    """打印警告。"""
    out(f"[警告] {text}", note)
