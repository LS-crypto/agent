"""演示：ActivityLogger 写入日志 + 终端中文注释。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.agent.activity import ActivityLogger, refresh_activity_summary
from core.agent.console import step
from core.user.paths import ensure_user_dirs


def main() -> None:
    user_id = "default"
    ensure_user_dirs(user_id)
    logger = ActivityLogger(user_id)

    step("演示活动记录", "模拟一次 Agent 会话并写入 runtime/logs/")
    logger.session_start()
    logger.user_message("帮我看看项目里有什么文件")
    logger.tool_call("list_dir", {"path": "."})
    logger.tool_result_event(True, "projects/ (空目录)")
    logger.assistant_reply("当前项目目录下仅有 projects 文件夹，暂无其他文件。")
    logger.session_end()

    summary = refresh_activity_summary()
    step("完成", f"日志已写入，汇总已更新：{summary}")


if __name__ == "__main__":
    main()
