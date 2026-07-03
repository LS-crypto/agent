PYTHON=python

.PHONY: help mcp-check test-mcp

help:
	@echo "Available targets: mcp-check, test-mcp"

# Run the local MCP-like server and quick check script (for local dev)
mcp-check:
	$(PYTHON) scripts/check_mcp_registration.py

# Run the single integration test for MCP registration (CI-friendly)
test-mcp:
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pytest -q tests/test_mcp_integration.py::test_mcp_registration_and_call
