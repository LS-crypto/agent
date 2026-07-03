PYTHON=uv run python

.PHONY: help mcp-check test-mcp test

help:
	@echo "Available targets: mcp-check, test-mcp, test"

# 本地 MCP 工具注册与状态 API 检查
mcp-check:
	$(PYTHON) scripts/check_mcp_registration.py

# CI 同款 MCP 集成测试
test-mcp:
	uv run pytest -q \
		tests/test_mcp_integration.py \
		tests/test_mcp_status.py \
		tests/test_mcp_tools.py \
		tests/test_github_mcp.py \
		tests/test_brave_search.py

# 全量测试（不含 Docker health）
test:
	uv run pytest tests/ -q --ignore=tests/test_docker_health.py
