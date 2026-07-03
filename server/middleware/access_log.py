"""请求访问日志中间件（中文说明）。"""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from server.access_log import log_request


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        client = request.client.host if request.client else "-"
        path = request.url.path
        if request.url.query:
            path = f"{path}?{request.url.query}"
        log_request(client, request.method, path, response.status_code, elapsed_ms)
        return response
