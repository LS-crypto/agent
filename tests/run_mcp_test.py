import asyncio
from server.mcp_manager import get_mcp_manager


async def main():
    mgr = get_mcp_manager()
    await mgr.start()
    print("enabled:", mgr.enabled)
    tools = await mgr.list_tools()
    print("tools:", tools)
    try:
        res = await mgr.call_tool("list_dir", {"path": "."})
        print("call list_dir result:", res)
    except Exception as e:
        print("call error:", e)
    await mgr.stop()


if __name__ == "__main__":
    asyncio.run(main())
