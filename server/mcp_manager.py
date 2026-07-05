"""MCP 管理器（骨架实现）。

当前实现为最小可用骨架：当检测到 `mcp` SDK 可用时会记录可用性，
否则以禁用状态运行。后续可扩展为：读取配置、启动 stdio/http 客户端、
维护会话并提供 `list_tools` / `call_tool` 等方法。
"""
from __future__ import annotations

import asyncio
import logging
import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional
import sys

from core.config import get_mcp_config

logger = logging.getLogger(__name__)


class MCPManager:
    """简易 MCP 管理器骨架。

    在启动时尝试导入 `mcp` SDK；如果不可用，则保持禁用状态但不阻塞后端启动。
    """

    def __init__(self) -> None:
        self.enabled = False
        self._started = False
        self._servers: List[Dict[str, Any]] = []
        self._http_server_url: Optional[str] = None
        self._sessions: Dict[str, Any] = {}

        cfg = get_mcp_config()
        self._cfg = cfg

        try:
            if cfg and cfg.sdk_path:
                # 可选：将本地 SDK 路径加入 sys.path 以便导入
                if cfg.sdk_path not in sys.path:
                    sys.path.insert(0, cfg.sdk_path)

            import mcp  # type: ignore

            self._has_sdk = True
            self._sdk = mcp
            logger.info("MCP SDK 可用，准备启用 MCP 支持")
        except Exception:
            self._has_sdk = False
            self._sdk = None
            logger.info("未检测到 MCP SDK，MCP 功能将被禁用（可选安装 modelcontextprotocol/python-sdk）")

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        # 根据配置探测 HTTP MCP server（可配置 URL），便于快速本地测试
        http_candidates = []
        if self._cfg and self._cfg.http_url:
            http_candidates.append(self._cfg.http_url.rstrip("/"))
        http_candidates.append("http://localhost:9000")

        for candidate in http_candidates:
            try:
                url = f"{candidate}/tools"
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=1.0) as resp:
                    if resp.status == 200:
                        body = resp.read()
                        parsed = json.loads(body.decode("utf-8"))
                        if isinstance(parsed, dict) and "tools" in parsed:
                            tool_list = parsed["tools"]
                        elif isinstance(parsed, list):
                            tool_list = parsed
                        else:
                            tool_list = []
                        self._servers.append(
                            {"type": "http", "url": candidate, "tools": tool_list}
                        )
                        self._http_server_url = candidate
                        self.enabled = True
                        logger.info(f"已连接到本地 MCP-like HTTP 服务器 ({candidate})")
                        return
            except Exception:
                logger.debug("未检测到 MCP-like HTTP 服务器 %s", candidate)

        # 若存在 modelcontextprotocol SDK，可在此处初始化 SDK 客户端
        if self._has_sdk:
            # TODO: 使用 SDK 初始化更多连接
            # 尝试用 SDK 创建一个内存 client（轻量探测）
            try:
                # 使用 SDK 的 Client 进行内存 transport 探测（不必实际连接远端）
                # SDK 的客户端构造在不同版本可能不同，尝试常见路径与 transport 参数
                client = None
                # 优先使用配置中指定的 transport
                transport = getattr(self._cfg, "sdk_transport", None)
                if transport:
                    # 尝试常见构造签名
                    try:
                        client = self._sdk.client.Client(transport=transport)
                    except Exception:
                        try:
                            client = self._sdk.client.Client(transport=transport, config={})
                        except Exception:
                            client = None

                # 回退到无参构造
                if client is None:
                    try:
                        client = self._sdk.client.Client()
                    except Exception:
                        try:
                            client = getattr(self._sdk, "Client", None) and self._sdk.Client()
                        except Exception:
                            client = None
                # 保存 client 以备之后调用（后续可支持不同 transports）
                self._sdk_client = client
                if client is None:
                    raise RuntimeError("无法初始化 MCP SDK client")
                self.enabled = True
                logger.info("MCP SDK 已初始化（内存 client），MCPManager 已启用")
                # 尝试为 SDK 创建一个默认会话（如果 SDK client 支持）
                try:
                    create_sess = getattr(self._sdk_client, "create_session", None)
                    if callable(create_sess):
                        sess = create_sess()
                        self._sessions["default"] = sess
                except Exception:
                    pass
                return
            except Exception:
                logger.exception("使用 MCP SDK 初始化客户端失败")
                self.enabled = False
                return
            return

        self.enabled = False
        logger.info("MCPManager 初始化完成（未启用任何 MCP Server）")

    async def stop(self) -> None:
        if not self._started:
            return
        # 尝试关闭 SDK 客户端（若提供关闭方法）
        try:
            c = getattr(self, "_sdk_client", None)
            if c is not None:
                # 支持 aclose/close
                if hasattr(c, "aclose"):
                    await c.aclose()
                elif hasattr(c, "close"):
                    try:
                        c.close()
                    except Exception:
                        pass
        except Exception:
            logger.debug("关闭 SDK client 时发生错误", exc_info=True)

        self._started = False
        logger.info("MCPManager 已停止")

    async def create_session(self, session_id: str = "default") -> Any:
        """为 SDK 创建会话并返回会话对象（如果 SDK 支持）。"""
        if not self._has_sdk or getattr(self, "_sdk_client", None) is None:
            return None
        try:
            create_sess = getattr(self._sdk_client, "create_session", None)
            if callable(create_sess):
                sess = create_sess()
                self._sessions[session_id] = sess
                return sess
        except Exception:
            logger.debug("创建 SDK 会话失败", exc_info=True)
        return None

    async def close_session(self, session_id: str = "default") -> None:
        sess = self._sessions.pop(session_id, None)
        if sess is None:
            return
        try:
            if hasattr(sess, "aclose"):
                await sess.aclose()
            elif hasattr(sess, "close"):
                try:
                    sess.close()
                except Exception:
                    pass
        except Exception:
            logger.debug("关闭 SDK 会话失败", exc_info=True)

    async def list_tools(self) -> List[Dict[str, Any]]:
        """返回可用工具的列表（占位）。"""
        if not self.enabled:
            return []
        # 合并已发现的服务器提供的工具
        result: List[Dict[str, Any]] = []
        # 如果 SDK client 可用，优先通过 SDK 获取工具列表
        if getattr(self, "_sdk_client", None) is not None:
            try:
                # 客户端的 list_tools 返回 mcp_types.ListToolsResult
                tools_res = await self._sdk_client.list_tools()
                for t in tools_res.tools:
                    result.append({"server": "sdk", "tool": {"name": t.name, "description": getattr(t, 'description', '')}})
            except Exception:
                logger.exception("从 MCP SDK 获取工具失败，回退到已发现的 servers 列表")
        for s in self._servers:
            for t in s.get("tools", []):
                result.append({"server": s.get("url"), "tool": t})
        return result

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """调用指定工具并返回结果（占位）。"""
        if not self.enabled:
            raise RuntimeError("MCP 未启用")
        # TODO: 根据 tool_name 分发到对应 MCP Server
        # 如果 SDK client 可用，尝试通过 SDK 调用工具
        if getattr(self, "_sdk_client", None) is not None:
            try:
                # Client.call_tool 或 session.call_tool 的高层方法
                # 某些实现可能返回同步结果或协程，处理两种情况
                call = getattr(self._sdk_client, "call_tool", None)
                if call is None:
                    raise RuntimeError("SDK client 不支持 call_tool")

                res = call(tool_name, arguments)
                if asyncio.iscoroutine(res):
                    res = await res
                return res
            except Exception:
                logger.exception("通过 MCP SDK 调用工具失败，回退到 HTTP 调用")

        # 简单实现：如果本地 HTTP server 被发现，则调用 /call
        if self._http_server_url:
            url = f"{self._http_server_url}/call"
            data = json.dumps({"tool": tool_name, "args": arguments}).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=10.0) as resp:
                    body = resp.read()
                    return json.loads(body.decode("utf-8"))
            except urllib.error.HTTPError as e:
                raise RuntimeError(f"HTTP error from MCP server: {e.code} {e.reason}")
            except Exception as e:
                raise RuntimeError(f"调用 MCP server 失败: {e}")

        raise NotImplementedError("当前仅支持本地 HTTP MCP-like 服务器")


_manager: MCPManager | None = None


def get_mcp_manager() -> MCPManager:
    global _manager
    if _manager is None:
        _manager = MCPManager()
    return _manager
