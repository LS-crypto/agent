"""演示：CodingAgent 完整工具集。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.agent.coding_agent import CodingAgent
from core.agent.console import step

USER_ID = "default"


def main() -> None:
    step("编程 Agent 演示", "完整工具集：文件 + 搜索 + 命令")
    agent = CodingAgent(user_id=USER_ID, resume=False, verbose=True)
    agent.start_session()

    prompt = "请列出项目目录里有什么，如果没有 hello.py 就创建一个，内容是 print('hello')"
    agent.chat(prompt)

    agent.end_session()
    step("演示结束", "生成文件在 runtime/workspaces/default/projects/")


if __name__ == "__main__":
    main()
