"""最小可用 Agent 示例：天气查询（百炼 Qwen API）。"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.agent.console import answer, out, step, tool, tool_result
from core.config import MODEL_FLASH, create_client

client = create_client()


def get_weather(city: str) -> str:
    weather_data = {
        "北京": "26°C，晴",
        "上海": "32°C，阴转小雨",
        "深圳": "28°C，多云",
    }
    return weather_data.get(city, "暂无数据")


tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"}
                },
                "required": ["city"],
            },
        },
    }
]


def run_agent(prompt: str) -> str:
    step("启动 Agent", f"用户问题：{prompt}")
    messages = [{"role": "user", "content": prompt}]
    round_num = 0

    while True:
        round_num += 1
        step(
            f"第 {round_num} 轮 · 请求模型",
            f"向百炼发送对话与工具定义（model={MODEL_FLASH}）",
        )

        resp = client.chat.completions.create(
            model=MODEL_FLASH,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        msg = resp.choices[0].message

        if not msg.tool_calls:
            step("模型返回最终答案", "未再请求工具，Agent 循环结束")
            return msg.content or ""

        out(
            f"[模型决策] 需要调用 {len(msg.tool_calls)} 个工具",
            "模型判断需查外部数据，返回 tool_calls",
        )
        messages.append(msg)

        for tc in msg.tool_calls:
            fn_name = tc.function.name
            fn_args = json.loads(tc.function.arguments)
            tool(fn_name, fn_args, "按模型指定的函数名和参数，在本地执行工具")

            if fn_name == "get_weather":
                result = get_weather(fn_args["city"])
            else:
                result = f"未知工具: {fn_name}"

            tool_result(result, "将工具返回值写入 messages，供下一轮模型使用")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )


if __name__ == "__main__":
    step("运行示例", "python examples/weather_agent.py")
    final = run_agent("深圳今天热不热？")
    answer(final, "以上即为 Agent 基于工具数据生成的自然语言回答")
    step("完成", "示例运行结束")
