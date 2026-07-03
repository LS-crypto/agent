"""Docker 集成：构建镜像并验证容器内 /health。"""

from __future__ import annotations

import shutil
import subprocess
import time
import urllib.error
import urllib.request

import pytest

IMAGE = "sheldon-agent:test-health"
CONTAINER = "sheldon-agent-test-health"
HOST_PORT = "18765"


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _run(cmd: list[str], *, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


@pytest.mark.skipif(not _docker_available(), reason="未安装 Docker")
def test_docker_build_and_health() -> None:
    root = __import__("pathlib").Path(__file__).resolve().parent.parent

    build = _run(
        [
            "docker",
            "build",
            "-f",
            str(root / "deploy" / "Dockerfile"),
            "-t",
            IMAGE,
            str(root),
        ],
        timeout=600,
    )
    assert build.returncode == 0, build.stderr or build.stdout

    _run(["docker", "rm", "-f", CONTAINER], timeout=30)

    run = _run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            CONTAINER,
            "-p",
            f"{HOST_PORT}:8765",
            "-e",
            "DASHSCOPE_API_KEY=sk-test-placeholder",
            IMAGE,
        ],
        timeout=60,
    )
    assert run.returncode == 0, run.stderr or run.stdout

    # 等待 Uvicorn 监听（冷启动约数秒）
    time.sleep(6)

    try:
        url = f"http://127.0.0.1:{HOST_PORT}/health"
        last_err: Exception | None = None
        for _ in range(45):
            try:
                with urllib.request.urlopen(url, timeout=2) as resp:
                    assert resp.status == 200
                    body = resp.read().decode("utf-8")
                    assert '"ok"' in body
                    return
            except (urllib.error.URLError, TimeoutError, AssertionError) as exc:
                last_err = exc
                time.sleep(1)
        raise AssertionError(f"容器 /health 未就绪: {last_err}")
    finally:
        _run(["docker", "rm", "-f", CONTAINER], timeout=30)
