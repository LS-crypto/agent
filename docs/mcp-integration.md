# MCP 集成指南

本指南说明如何在本项目中集成 Model Context Protocol（MCP），包括本地测试、SDK 使用与常见 transport 配置示例。

## 概念

- MCP：一套允许模型对外调用具名工具（tool）并传参的协议。工具以 schema（JSON Schema）描述参数。
- 在本项目中，`MCPManager` 负责探测可用的 MCP 源（HTTP 或 SDK），并暴露 `list_tools()` / `call_tool()` API。
- `tools.build.register_mcp_tools` 会把 MCP 返回的工具 schema 注册到 `ToolRegistry`，使模型能够选择并调用这些工具。

## 本地快速验证（推荐）

1. 启动本地 MCP-like HTTP 示例服务器：

```powershell
python -c "from mcp_servers.local_filesystem_mcp import run; import threading; threading.Thread(target=lambda: run(9000), daemon=True).start()"
```

2. 启动后端（或运行集成测试）：

```powershell
python -m backend
# 或
python scripts/check_mcp_registration.py
```

3. 在运行时，`app.state.registry` 将包含从 MCP 获取的工具 schema，可以通过 `registry.execute(name, args)` 调用工具。

## 使用 Python SDK（可选）

若你希望使用官方 `modelcontextprotocol/python-sdk`：

```powershell
git clone https://github.com/modelcontextprotocol/python-sdk.git mcp_servers/python-sdk
cd mcp_servers/python-sdk
python -m venv .venv
.venv\Scripts\python -m pip install -e .[cli]
```

然后可通过环境变量 `MCP_SDK_PATH` 指向 SDK 的 `src` 目录，以便主项目直接导入 SDK（便于调试）：

```powershell
setx MCP_SDK_PATH "D:\\system\\TEST\\qwen-agent\\mcp_servers\\python-sdk\\src"
```

`MCPManager` 会尝试根据 `MCP_SDK_TRANSPORT`（如果设置）将 transport 参数传给 SDK client 构造函数；不同 SDK 版本的构造签名可能不同。

## 常见 transport 示例

- stdio：用于本地可执行的工具桥（子进程 stdio 通信）。
- streamable-http：通过 HTTP + SSE/流式响应支持逐步输出的工具。

注意：transport 名称取决于 SDK 的实现与版本，参考你克隆的 `python-sdk` 文档以获得准确的 transport 字符串。

## 配置项（环境变量）

- `MCP_ENABLED` — 启用 MCP 集成（true/false，默认自动检测）。
- `MCP_HTTP_URL` — MCP HTTP 服务基址（例如 `http://localhost:9000`）。
- `MCP_SDK_PATH` — 本地 SDK 源路径（可选，用于调试）。
- `MCP_SDK_TRANSPORT` — 传递给 SDK client 的 transport 名称（可选）。

## 安全建议

- 在生产环境中，只从可信来源加载外部工具 schema。对于来自第三方的工具，务必进行安全审计。
- 建议在生产中开启访问控制（API Key / IAM / service account）并审计工具调用日志（`runtime/logs/`）。

## 故障排查

- 若没有工具被注册：确认 MCP 服务是否可达（`curl $MCP_HTTP_URL/tools`），或检查 `MCP_SDK_PATH` 导入是否成功。
- 遇到异步/事件循环问题：本项目将 MCP 异步调用封装在后台线程事件循环中，若需要更深度集成请在 `tools/build.py` 中调整实现。

---

如需我把 `MCPManager` 的 SDK 会话管理进一步扩展为支持 long-lived sessions 与 auth，请告诉我具体期望（例如：session-per-user、token-rotation、transport-fallback 策略）。
