from .safe_tools import execute_tool, decide_next_action

def run_with_recovery(
    name: str,
    args: dict,
    fixed_args: dict | None = None,
    max_attempts: int = 2
) -> dict:

    state = {
        "attempts": 0,
        "status": "running",
        "last_outcome": None
    }

    while state["attempts"] < max_attempts:

        state["attempts"] += 1

        outcome = execute_tool(name, args)

        state["last_outcome"] = outcome

        action = decide_next_action(outcome)

        print(f"\n第{state['attempts']}次尝试")
        print(f"执行结果：{outcome}")
        print(f"处理决策：{action}")

                # 工具成功
        if action == "check_goal":
            state["status"] = "tool_succeeded"
            return state

        # 达到最大尝试次数
        if state["attempts"] >= max_attempts:
            state["status"] = "max_attempts_reached"
            return state

        # 参数错误且有修正方案
        if action == "revise_arguments" and fixed_args is not None:
            args = fixed_args
            fixed_args = None
            print("使用修正后的参数重新尝试")
            continue

        # 其他情况停止
        state["status"] = "stopped"
        return state

    state["status"] = "max_attempts_reached"
    return state


def main() -> None:

    result = run_with_recovery(
    name="divide",
    args={"a": 10, "b": 0},
    max_attempts=2
    )

    print("\n最终状态：", result["status"])
    print("尝试次数：", result["attempts"])


if __name__ == "__main__":
    main()