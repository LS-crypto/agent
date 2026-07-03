"""项目路径常量（全仓库统一引用）。"""

from pathlib import Path

# sheldon-agent/ 项目根
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Sheldon-Shuo-Agent/ 工作区根（含 taste-skill 等）
WORKSPACE_ROOT = PROJECT_ROOT.parent

CORE_ROOT = PROJECT_ROOT / "core"
RUNTIME_ROOT = PROJECT_ROOT / "runtime"
APPS_ROOT = PROJECT_ROOT / "apps"
SERVER_ROOT = PROJECT_ROOT / "server"
TESTS_ROOT = PROJECT_ROOT / "tests"
DEPLOY_ROOT = PROJECT_ROOT / "deploy"
DOCS_ROOT = PROJECT_ROOT / "docs"
