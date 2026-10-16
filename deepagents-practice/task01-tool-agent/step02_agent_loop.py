from langchain_core.tools import tool
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain.messages import AIMessage,HumanMessage
from langchain.agents import create_agent

@tool # 装饰器，装饰为langchain_core.tools
def echo(text: str)->str:
    """这是一个echo函数"""
    return f"echo: {text}"

# 假模型：它不真的"思考"，只是把 responses 列表里的台词按顺序念出来。
# 用它是因为：台词是我们写死的，所以输出里出现的东西一定不是模型编的 —— 这叫排除法证据。
class MyScriptedModel(FakeMessagesListChatModel):


    # 框架会在每次调用模型前调用 bind_tools，把"模型能用的工具清单"交给模型。
    # 这里直接 return self，等于"假装收到了"，实际什么都没做（因为我们不需要）。
    # 注意：我们调用的是 agent，但这个方法是框架来调我们的 —— 控制反转。
    def bind_tools(self, tools, **kwargs):
        return self

if __name__ == "__main__":
    # print(type(MyScriptedModel(responses=[AIMessage(content="hi")])))
    agent = create_agent(
        model=MyScriptedModel(
            responses=[
                # 第一句台词：content 是空的，但它提出了工具调用请求
                # 这一坨就是"工具请求"，三个字段：name（调谁）、args（传什么）、id（本次调用的编号）
                AIMessage(
                    content="",
                    tool_calls=[{
                        "name":"echo",
                        "args":{"text":"你好"},
                        "id":"call-1",
                    }]
                ),
                # 第二句台词：模型收到工具结果之后，给出的最终回复
                AIMessage(
                    content="调用已结束"
                )
            ]
        ),
        tools=[echo]
    )

    # agent.invoke() 的入参是"状态字典"，键名必须是 messages
    # 写成别的键名不会报错，只会被静默忽略
    result = agent.invoke(
        {
            "messages" : [
                ("user","hi")     # 元组形式，等价于 HumanMessage(content="hi")
            ]
        }
    )
    # print(result["messages"])

    # 逐条打印消息链。完整顺序是四段：human → ai → tool → ai
    # 每一行都写出"打的是什么"，这样不用对照代码也能读懂输出
    for m in result["messages"]:
        print("这条消息的类是：", type(m))
        # print(type(result["messages"]))
        print("这条消息的内容是：", m)
        # 注意判断的是 AIMessage 而不是 ToolMessage，所以 tool 那条不会被这里的 if 命中
        if type(m) == AIMessage:
            print(f"这条是 AIMessage，它的 content 是：{m.content}")

        elif type(m) == HumanMessage:
            print(f"这条是 HumanMessage，它的 content 是：{m.content}")
