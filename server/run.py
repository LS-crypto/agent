"""推荐启动入口：Uvicorn + 中文日志。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# 允许直接 python backend/run.py（无需 -m）
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> None:
    import uvicorn

    from server.logging_config import (
        disable_uvicorn_access_log,
        setup_app_logging,
        setup_uvicorn_logging,
    )

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8765"))
    reload = os.getenv("UVICORN_RELOAD", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )

    disable_uvicorn_access_log()
    setup_uvicorn_logging()
    setup_app_logging()

    uvicorn.run(
        "server.main:app",
        host=host,
        port=port,
        reload=reload,
        access_log=False,
    )


if __name__ == "__main__":
    main()
