"""CORS 配置：从环境变量读取允许来源。"""

from __future__ import annotations

import os

_DEFAULT_DEV_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
)

# Capacitor Android / iOS 壳内 WebView 来源（APK 登录必需）
_MOBILE_APP_ORIGINS = (
    "https://localhost",
    "http://localhost",
    "capacitor://localhost",
    "ionic://localhost",
)


def get_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "").strip()
    origins = (
        [o.strip() for o in raw.split(",") if o.strip()]
        if raw
        else list(_DEFAULT_DEV_ORIGINS)
    )
    for origin in _MOBILE_APP_ORIGINS:
        if origin not in origins:
            origins.append(origin)
    return origins
