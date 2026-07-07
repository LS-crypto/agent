"""最小 API 连通性验证：单次百炼调用。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.agent.console import answer, step
from core.config import MODEL_FLASH, create_client


def main() -> int:
    step("Ping Agent", f"向百炼发送单次请求（model={MODEL_FLASH}）")
    client = create_client()
    resp = client.chat.completions.create(
        model=MODEL_FLASH,
        messages=[{"role": "user", "content": "用一句话介绍你自己"}],
        max_tokens=60,
    )
    text = resp.choices[0].message.content or ""
    answer(text, "API 连通正常，阶段 0 验收通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
