import threading
import time

# 启动本地 MCP-like server
from mcp_servers import local_filesystem_mcp

def start_mcp():
    local_filesystem_mcp.run(9000)

mcp_thread = threading.Thread(target=start_mcp, daemon=True)
mcp_thread.start()
print('started local mcp server')

# 触发 FastAPI lifespan
from server.main import app
from fastapi.testclient import TestClient

with TestClient(app) as client:
    # 给后台注册线程一些时间
    time.sleep(3)
    has_registry = hasattr(app.state, 'registry')
    print('has registry ->', has_registry)
    reg = getattr(app.state, 'registry', None)
    if reg is None:
        print('registry is None')
    else:
        schemas = reg.get_schemas()
        print('schemas count ->', len(schemas))
        print('schema names ->', [s['function']['name'] for s in schemas])
        if any(s['function']['name'] == 'list_dir' for s in schemas):
            res = reg.execute('list_dir', {'path': '.'})
            print('exec list_dir ->', res)

print('done')
