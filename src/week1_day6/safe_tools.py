# 定义工具函数：加法
def add(a: float, b: float) -> float:
    return a + b

# 定义工具函数：乘法
def multiply(a: float, b: float) -> float:
    return a * b

#定义工具函数：除法
def divide(a: float, b: float) -> float:
    return a / b


# 定义工具注册表，将定义的工具函数存放在注册表中，然后通过工具名称与工具函数建立对应关系，例如用add就是使用加法工具函数
tool_registry = {
    "add": add,
    "multiply": multiply,
    "divide": divide,
}

# 实现“工具不存在”检查函数，参数设置name和args
def execute_tool(name: str, args: dict) -> dict:

    # 定义变量tool，提取所用工具的名字
    tool = tool_registry.get(name)

    # 如果提取的工具名字未定义，则返回“error”和“工具未注册”
    if tool is None:
        return {
            "status": "error",
            "stage": "lookup",
            "message": "工具未注册"
        }
    
    #使用try...except...关键字，尝试将输入的参数a和参数b转化为float格式
    try:
        a = float(args["a"])
        b = float(args["b"])

    #如果转化失败就捕获异常并返回错误，错误包括键错误（字典中不存在指定的键）、对象类型错误、对象值错误
    except (KeyError, TypeError, ValueError) as error:
        return {
            "status": "error",
            "stage": "validation",
            "message": f"参数错误：{error}"
        }

    try:
        result = tool(a, b)

    except Exception as error:
        return {
        "status": "error",
        "stage": "execution",
        "error_type": type(error).__name__,
        "message": str(error),
        }

    return {
        "status": "success",
        "result": result
    }

# 新增决策函数
def decide_next_action(outcome: dict) -> str:

    # 情况1：工具执行成功
    if outcome["status"] == "success":
        return "check_goal"

    # 情况2：工具不存在
    if outcome.get("stage") == "lookup":
        return "choose_tool"

    # 情况3：参数错误
    if outcome.get("stage") == "validation":
        return "revise_arguments"

    # 情况4：发生除零错误
    if outcome.get("error_type") == "ZeroDivisionError":
        return "stop"

    # 情况5：发生连接错误
    if outcome.get("error_type") == "ConnectionError":
        return "retry"

    # 其他错误：默认停止
    return "stop"


# 定义测试函数
def main() -> None:

    tests = [
    ("multiply", {"a": 20, "b": 4}),
    ("divide", {"a": 10, "b": 2}),
    ("multiply", {"a": "hello", "b": 4}),
    ("multiply", {"a": 20}),
    ("subtract", {"a": 10, "b": 2}),
    ("divide", {"a": 10, "b": 0}),
    ]

    for name, args in tests:
        outcome = execute_tool(name, args)

        action = decide_next_action(outcome)

        print(f"\n工具：{name}")
        print(f"执行结果：{outcome}")
        print(f"下一步决策：{action}")


if __name__ == "__main__":
    main()
