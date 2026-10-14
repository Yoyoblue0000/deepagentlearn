from langchain_core.tools import tool

# @tool 是装饰器。它不改函数内部的逻辑，
# 而是把「普通函数」包装成一个 LangChain 能识别的工具对象（StructuredTool）。
# 包装之后，模型能看到的"工具说明书"就来自这个函数本身：
#   name        ← 函数名
#   description ← docstring（所以不写 docstring 会直接报错）
#   args        ← 参数名 + 类型标注
@tool # 装饰器，装饰为langchain_core.tools
def echo(text: str)->str:
    """这是一个echo函数"""      # 这句不是写给人看的注释，是写给模型看的描述
    return f"echo: {text}"

@tool
def add_tool(num1: int, num2: int)->int:
    """这是一个工具函数，用来完成两个数的加法"""
    return num1 + num2           # 因为加了 @tool，add_tool 这个名字现在指向"工具对象"

# 和上面唯一的区别：没有 @tool
# 所以它还是普通函数，只能被 Python 直接调用，模型看不到它
def add_tool_1(num1: int, num2: int)->int:
    """这是一个工具函数，用来完成两个数的加法"""
    return num1 + num2

if __name__ == "__main__":
    # 注意这里调的是 add_tool_1（普通函数），不是 add_tool（工具对象）
    # add_tool(1, 2) 这样写会直接报错：'StructuredTool' object is not callable
    # 工具对象只能用 .invoke() 调用，见下面
    print("add_tool_1(1, 2) 的结果是：", add_tool_1(1, 2))

    # 下面几行是"刨开工具对象看里面"：
    #   .func      取回被包装之前的原始函数
    #   .__doc__   原始函数的 docstring
    #   .__name__  原始函数的名字
    #   .__args__  原始函数的参数名
    # print(add_tool.func.__doc__)
    # print(echo.func.__doc__)
    # print(add_tool.func.__name__)
    # print(echo.func.__name__)
    # print(add_tool.func.__args__)
    # print(echo.func.__args__)

    # 下面六个就是"模型看到的说明书"的三要素，两个工具各打一遍
    print("add_tool.description 的结果是：", add_tool.description)
    print("add_tool.name 的结果是：", add_tool.name)
    print("add_tool.args 的结果是：", add_tool.args)
    print("echo.name 的结果是：", echo.name)
    print("echo.description 的结果是：", echo.description)
    print("echo.args 的结果是：", echo.args)



    # 调用工具对象的正确方式是 .invoke()，不能直接像函数那样 add_tool(1,2)
    # 参数写成字典，键名必须和函数参数名一致
    # 这里故意传字符串 "1" / "2"，工具会按 args 里的类型标注自动转成整数
    print('add_tool.invoke({"num1":"1","num2":"2"}) 的结果是：', add_tool.invoke({"num1":"1","num2":"2"}))

    # 参数只有一个时，两种写法等价：
    print('echo.invoke({"text" : "hi"}) 的结果是：', echo.invoke({"text" : "hi"}))   # 显式写字典
    print('echo.invoke("hi") 的结果是：', echo.invoke("hi"))                        # 省略键名，直接给值

    #证明echo为什么不是原来的函数
    # 前者是"包装后的工具对象"，后者才是"被包装前的原始函数"
    print("type(add_tool) 的结果是：", type(add_tool))
    print("type(add_tool.func) 的结果是：", type(add_tool.func))
