
import os
import httpx

from dotenv import load_dotenv
from google import genai
from google.genai import types, errors

from .safe_tools import (
    multiply,
    execute_tool,
    decide_next_action,
    tool_registry,
)


# ===== 1. 模拟不稳定的工具 =====

# 1 = 第一次失败，第二次成功
# 2 = 前两次都失败，用于测试重试上限
FAIL_FIRST_N_CALLS = 1

simulator = {"calls": 0}


def unstable_multiply(a: float, b: float) -> float:
    """计算两个数字的乘积，模拟临时连接故障。"""

    simulator["calls"] += 1

    if simulator["calls"] <= FAIL_FIRST_N_CALLS:
        raise ConnectionError("模拟：服务连接暂时中断")

    return multiply(a, b)


# ===== 2. 主程序 =====

def main() -> None:

    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("没有找到 GEMINI_API_KEY")
        return

    client = genai.Client(api_key=api_key)

    simulator["calls"] = 0

    # 注册工具
    tool_registry["unstable_multiply"] = unstable_multiply

    question = (
        "请调用 unstable_multiply 工具计算20乘以4。"
        "如果发生临时连接故障，请重试一次。"
    )

    # 初始化 Agent 状态
    state = {
        "step": 0,
        "retry_count": 0,
        "status": "running",
        "tool_succeeded": False,
        "last_action": None,
        "history": [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=question)],
            )
        ],
    }

    max_steps = 4
    max_retries = 1

    # Gemini 配置
    config = types.GenerateContentConfig(
        system_instruction=(
            "你是一个数学计算助手。"
            "请使用提供的工具完成计算。"
            "如果收到临时连接错误，可以重试一次。"
            "工具成功后，根据真实结果回答。"
            "如果任务无法完成，请说明原因。"
            "每轮最多请求一个工具。"
        ),
        tools=[unstable_multiply],
        automatic_function_calling=(
            types.AutomaticFunctionCallingConfig(
                disable=True
            )
        ),
        tool_config=types.ToolConfig(
            function_calling_config=(
                types.FunctionCallingConfig(mode="AUTO")
            )
        ),
    )

    print(f"用户：{question}")

    # ===== 3. Agent Loop =====

    while state["step"] < max_steps:

        print(
            f"\n--- 模型决策轮次，"
            f"已执行工具 {state['step']} 次 ---"
        )

        # 请求 Gemini
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=state["history"],
                config=config,
            )

        except (httpx.TransportError, errors.APIError) as error:
            state["status"] = "api_error"
            print(f"Gemini API 请求失败：{error}")
            break

        calls = response.function_calls or []

        # 模型没有请求工具
        if not calls:

            print(f"\nGemini 最终回答：{response.text}")

            if state["tool_succeeded"] and response.text:
                state["status"] = "completed"
            elif state["step"] > 0:
                state["status"] = "ended_without_success"
            else:
                state["status"] = "answered_without_tool"

            break

        if len(calls) != 1:
            state["status"] = "invalid_call_count"
            print("每轮只允许调用一个工具")
            break

        call = calls[0]

        # ===== 4. 工具执行前的安全检查 =====

        if call.name != "unstable_multiply":
            state["status"] = "invalid_tool"
            print("模型请求了未授权工具")
            break

        if state["tool_succeeded"]:
            state["status"] = "unexpected_tool_call"
            print("工具已经执行成功，拒绝重复执行")
            break

        # 第二次及之后的调用属于重试
        if state["step"] > 0:

            if state["last_action"] != "retry":
                state["status"] = "unexpected_retry"
                print("当前操作不允许重试")
                break

            if state["retry_count"] >= max_retries:
                state["status"] = "retry_limit_reached"
                print("超过最大重试次数")
                break

            state["retry_count"] += 1

        print("模型选择工具：", call.name)
        print("模型提供参数：", call.args)

        # ===== 5. 安全执行工具 =====

        outcome = execute_tool(
            call.name,
            call.args or {},
        )

        action = decide_next_action(outcome)

        print("工具执行结果：", outcome)
        print("下一步处理决策：", action)

        # ===== 6. 更新对话历史 =====

        state["history"].append(
            response.candidates[0].content
        )

        function_response = types.Part.from_function_response(
            name=call.name,
            response=outcome,
        )

        state["history"].append(
            types.Content(
                role="user",
                parts=[function_response],
            )
        )

        state["step"] += 1
        state["last_action"] = action

        # ===== 7. 根据执行结果决定下一步 =====

        if outcome["status"] == "success":
            state["tool_succeeded"] = True
            continue

        if action == "retry":

            if state["retry_count"] >= max_retries:
                state["status"] = "retry_limit_reached"
                print("重试后仍然失败，停止执行")
                break

            print("允许模型重新决策")
            continue

        state["status"] = "stopped"
        print(
            "任务停止：",
            outcome.get("message", "未知错误")
        )
        break

    else:
        state["status"] = "max_steps_reached"
        print("达到最大工具执行步数")

    # ===== 8. 输出最终状态 =====

    print("\n===== Agent 执行报告 =====")
    print(f"工具执行次数：{state['step']}")
    print(f"重试次数：{state['retry_count']}")
    print(f"最终状态：{state['status']}")


if __name__ == "__main__":
    main()
