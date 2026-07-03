"""FastAPI 入口：阶段 B 后端 API。"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from core.agent.console import step
from server.mcp_manager import get_mcp_manager
from server.cors import get_cors_origins
from server.db.database import init_db
from server.logging_config import (
    disable_uvicorn_access_log,
    setup_app_logging,
    setup_uvicorn_logging,
)
from server.middleware.access_log import AccessLogMiddleware
from server.routes import chat, meta, models, sessions


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    disable_uvicorn_access_log()
    setup_uvicorn_logging()
    setup_app_logging()
    step("后端启动", "初始化 SQLite 会话库（runtime/db/sessions.sqlite）")
    init_db()

    # 内置 MCP HTTP（磁盘/Skills 等），供 MCPManager 与外部客户端
    import os

    if os.getenv("MCP_BUILTIN", "1").strip().lower() in ("1", "true", "yes"):
        try:
            from core.mcp.builtin_server import start_builtin_mcp_server

            host = os.getenv("MCP_BUILTIN_HOST", "127.0.0.1")
            port = int(os.getenv("MCP_BUILTIN_PORT", "9000"))
            url = start_builtin_mcp_server(host, port)
            step("内置 MCP", f"已启动 {url}/tools")
        except OSError as exc:
            step("内置 MCP", f"未启动（端口占用？）: {exc}")

    step("后端就绪", "API 可访问；每条请求日志会带  --中文说明")

    # 启动 MCP 管理器（非阻塞骨架实现）
    mcp_mgr = get_mcp_manager()

    # 预先创建并挂载 ToolRegistry 到 app.state，供其它模块使用；不要在此立即注册 MCP 工具
    try:
        from core.tools.build import build_coding_registry

        _app.state.registry = build_coding_registry("default", register_mcp=False)
    except Exception:
        pass

    # 启动 MCP 并在其就绪后注册 MCP 工具到 registry
    async def _start_and_register():
        await mcp_mgr.start()
        try:
            registry = getattr(_app.state, "registry", None)
            if registry is None:
                from core.tools.build import build_coding_registry

                registry = build_coding_registry("default")
                _app.state.registry = registry

            from core.tools.build import register_mcp_tools

            register_mcp_tools(registry)
        except Exception:
            step("MCP 注册失败", "后台注册 MCP 工具时出错")

    try:
        asyncio.create_task(_start_and_register())
    except Exception:
        pass

    yield

    try:
        from core.mcp.builtin_server import stop_builtin_mcp_server

        stop_builtin_mcp_server()
    except Exception:
        pass

    step("后端关闭", "FastAPI 应用已停止")

    # 停止 MCP 管理器与注册时创建的后台 loop（如有）
    try:
        registry = getattr(_app.state, "registry", None)
        if registry is not None:
            mcp_loop = getattr(registry, "_mcp_loop", None)
            mcp_manager_obj = getattr(registry, "_mcp_manager", None)
            if mcp_loop is not None and mcp_manager_obj is not None:
                try:
                    fut = asyncio.run_coroutine_threadsafe(mcp_manager_obj.stop(), mcp_loop)
                    fut.result(timeout=5)
                except Exception:
                    pass
                try:
                    # 请求后台 loop 停止
                    mcp_loop.call_soon_threadsafe(mcp_loop.stop)
                except Exception:
                    pass
    except Exception:
        pass

    # 最后优雅停止 MCPManager 本身
    try:
        await mcp_mgr.stop()
    except Exception:
        try:
            asyncio.run(mcp_mgr.stop())
        except Exception:
            pass


app = FastAPI(
    title="Sheldon Agent API",
    description="Sheldon 编程 Agent 后端：SSE 流式对话 + SQLite 会话 + MCP + Skills",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AccessLogMiddleware)

app.include_router(sessions.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(models.router, prefix="/api")
app.include_router(meta.router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
