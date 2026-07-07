"""组装编程 Agent 所需的全部工具。"""

from core.tools.filesystem import register_filesystem_tools
from core.tools.git import register_git_tools
from core.tools.registry import ToolRegistry
from core.tools.search import register_search_tools
from core.tools.shell import register_shell_tools
from core.tools.mcp_tools import register_mcp_compat_tools
from core.tools.github_mcp import register_github_mcp_tools
from core.tools.brave_search import register_brave_search_tools
from core.tools.skills_tool import register_skills_tools
from core.tools.system import register_system_tools
from server.mcp_manager import get_mcp_manager
import threading
import logging

logger = logging.getLogger(__name__)

_mcp_registry: ToolRegistry | None = None
_mcp_tool_names: list[str] = []


def set_mcp_registry(registry: ToolRegistry, tool_names: list[str]) -> None:
    global _mcp_registry, _mcp_tool_names
    _mcp_registry = registry
    _mcp_tool_names = list(tool_names)


def get_mcp_registry() -> tuple[ToolRegistry | None, list[str]]:
    return _mcp_registry, _mcp_tool_names


def register_mcp_tools(registry: ToolRegistry) -> None:
    """在后台线程中异步探测 MCP 工具并注册到 `ToolRegistry`。

    说明: 后台线程会新建事件循环执行异步探测，避免阻塞主线程或使用
    `run_until_complete` 在已有事件循环中导致冲突。
    """
    import asyncio

    # 创建并启动长期运行的事件循环线程，用于调度 MCP SDK 的异步调用
    loop = asyncio.new_event_loop()

    def _loop_thread():
        asyncio.set_event_loop(loop)
        loop.run_forever()

    t = threading.Thread(target=_loop_thread, daemon=True, name="mcp-register-loop")
    t.start()

    m = get_mcp_manager()

    try:
        future_start = asyncio.run_coroutine_threadsafe(m.start(), loop)
        future_start.result(timeout=8)
        future = asyncio.run_coroutine_threadsafe(m.list_tools(), loop)
        tools = future.result(timeout=8)
    except Exception as exc:
        logger.warning("MCP 工具探测失败: %s", exc)
        return

    registered: list[str] = []
    for entry in tools:
        tool = entry.get("tool")
        if not tool:
            continue
        name = tool.get("name")
        if not name:
            continue
        desc = tool.get("description") or ""
        params = tool.get("parameters") or {
            "type": "object",
            "additionalProperties": True,
        }

        def make_handler(n):
            def handler(**kwargs):
                try:
                    # 参数名适配：很多 MCP 实现使用通用字段名 `path`，
                    # 而本仓库的本地工具常用 `file_path` / `dir_path`。
                    # 在调用远端 MCP 时，将常见别名映射为 `path`，以提高兼容性。
                    adapted = dict(kwargs)
                    if "path" not in adapted:
                        if "file_path" in kwargs and kwargs.get("file_path") is not None:
                            adapted["path"] = kwargs.get("file_path")
                        elif "dir_path" in kwargs and kwargs.get("dir_path") is not None:
                            adapted["path"] = kwargs.get("dir_path")

                    fut = asyncio.run_coroutine_threadsafe(m.call_tool(n, adapted), loop)
                    return fut.result(timeout=30)
                except Exception as e:
                    return {"success": False, "error": str(e)}

            return handler

        try:
            registry.register(name, desc, params, make_handler(name))
            registered.append(name)
        except Exception:
            continue

    if registered:
        set_mcp_registry(registry, registered)

    # 暴露 loop/thread 以便上层在需要时关闭（不强制关闭以保持向后兼容）
    try:
        setattr(registry, "_mcp_loop", loop)
        setattr(registry, "_mcp_thread", t)
        setattr(registry, "_mcp_manager", m)
    except Exception:
        pass
    # 添加封装的停止函数，便于在后端关闭时优雅停止后台 loop
    def _stop_mcp_loop():
        try:
            # 请求后台循环停止
            loop.call_soon_threadsafe(loop.stop)
        except Exception:
            pass
        try:
            # 等待线程结束（短超时）
            t.join(timeout=2)
        except Exception:
            pass

    try:
        setattr(registry, "_stop_mcp_loop", _stop_mcp_loop)
    except Exception:
        pass
    # 为了兼容后端在 lifespan 中传入 registry 的场景，保存一个引用到 app.state
    try:
        import inspect

        # 若调用者传入一个 FastAPI app 对象的 state，则 registry 已被设置
    except Exception:
        pass


def build_coding_registry(user_id: str, register_mcp: bool = True) -> ToolRegistry:
    """注册 filesystem + search + shell 工具。

    Args:
        user_id: 用户 ID，用于某些工具的路径上下文。
        register_mcp: 是否在构建时立即尝试注册 MCP 工具。默认 True 保持向后兼容；
                      在需要在 MCP 启动后再注册的场景中传 False。
    """
    registry = ToolRegistry()
    register_filesystem_tools(registry, user_id)
    register_search_tools(registry, user_id)
    register_shell_tools(registry, user_id)
    register_git_tools(registry, user_id)
    register_system_tools(registry, user_id)
    register_skills_tools(registry)
    register_mcp_compat_tools(registry, user_id)
    register_github_mcp_tools(registry)
    register_brave_search_tools(registry)
    # 尝试注册 MCP 提供的外部工具（如果 MCP 可用）
    if register_mcp:
        mcp_reg, mcp_names = get_mcp_registry()
        if mcp_reg is not None and mcp_names:
            registry.import_tools(mcp_reg, mcp_names)
        else:
            try:
                register_mcp_tools(registry)
            except Exception:
                pass
    return registry
