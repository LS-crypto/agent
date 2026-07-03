import threading
import time

import pytest

pytest.importorskip("mcp_servers")

from mcp_servers import local_filesystem_mcp
from server.main import app
from fastapi.testclient import TestClient


def _start_mcp_server():
    # run blocks, so run in daemon thread
    local_filesystem_mcp.run(9000)


def test_mcp_registration_and_call():
    t = threading.Thread(target=_start_mcp_server, daemon=True)
    t.start()
    # allow server to start
    time.sleep(0.5)

    with TestClient(app) as client:
        # allow background registration to complete
        time.sleep(1.5)
        assert hasattr(app.state, "registry")
        reg = app.state.registry
        schemas = reg.get_schemas()
        names = [s["function"]["name"] for s in schemas]
        assert "list_dir" in names

        # try calling the registered list_dir tool
        res = reg.execute("list_dir", {"path": "."})
        assert isinstance(res, dict)
        assert res.get("ok") is True or res.get("success") is True
