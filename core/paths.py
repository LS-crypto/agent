"""项目路径常量（全仓库统一引用）。"""

from pathlib import Path

# 仓库根（pyproject.toml 所在目录）
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 工作区根：与 PROJECT_ROOT 相同（含 taste-skill、andrej-karpathy-skills 等）
WORKSPACE_ROOT = PROJECT_ROOT

CORE_ROOT = PROJECT_ROOT / "core"
RUNTIME_ROOT = PROJECT_ROOT / "runtime"
APPS_ROOT = PROJECT_ROOT / "apps"
SERVER_ROOT = PROJECT_ROOT / "server"
TESTS_ROOT = PROJECT_ROOT / "tests"
DEPLOY_ROOT = PROJECT_ROOT / "deploy"
DOCS_ROOT = PROJECT_ROOT / "docs"
