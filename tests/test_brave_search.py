"""Brave Search 工具测试（Mock API）。"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from core.tools.brave_search import BraveSearchTools
from core.tools.build import build_coding_registry


@pytest.fixture
def brave_tools(monkeypatch):
    monkeypatch.setenv("BRAVE_API_KEY", "BSA_test_key")
    monkeypatch.setenv("BRAVE_SEARCH_COUNT", "5")
    return BraveSearchTools()


def test_not_configured(monkeypatch):
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    tools = BraveSearchTools()
    r = tools.brave_web_search("python asyncio")
    assert r["success"] is False
    assert "BRAVE_API_KEY" in r["error"]


def test_empty_query(brave_tools):
    r = brave_tools.brave_web_search("   ")
    assert r["success"] is False


def test_web_search_mock(brave_tools):
    payload = {
        "web": {
            "results": [
                {
                    "title": "Python asyncio docs",
                    "url": "https://docs.python.org/3/library/asyncio.html",
                    "description": "Asynchronous I/O",
                    "age": "2d",
                },
                {
                    "title": "Tutorial",
                    "url": "https://example.com/async",
                    "description": "Learn async",
                },
            ]
        }
    }
    with patch("core.tools.brave_search.http_get", return_value=(200, payload)):
        r = brave_tools.brave_web_search("python asyncio", count=2)
    assert r["success"] is True
    assert r["count"] == 2
    assert r["results"][0]["url"].startswith("https://")


def test_news_search_mock(brave_tools):
    payload = {
        "results": [
            {
                "title": "Tech news",
                "url": "https://news.example.com/1",
                "description": "Headline",
                "source": "Example News",
            }
        ]
    }
    with patch("core.tools.brave_search.http_get", return_value=(200, payload)):
        r = brave_tools.brave_news_search("AI agents")
    assert r["success"] is True
    assert r["results"][0]["source"] == "Example News"


def test_api_error(brave_tools):
    with patch("core.tools.brave_search.http_get", return_value=(401, {"message": "Invalid token"})):
        r = brave_tools.brave_web_search("test")
    assert r["success"] is False
    assert "401" in r["error"]


def test_registry_includes_brave(monkeypatch):
    monkeypatch.setenv("BRAVE_API_KEY", "BSA_test")
    reg = build_coding_registry("default", register_mcp=False)
    names = {s["function"]["name"] for s in reg.get_schemas()}
    assert "brave_web_search" in names
    assert "brave_news_search" in names
