# 和 step02 的区别：这里用的是 create_deep_agent（Deep Agent），不是 create_agent（裸骨架）
# 差别在于 Deep Agent 自带一套 Harness —— 默认的中间件会往工具列表里塞进一批工具
from deepagents import create_deep_agent
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.tools import tool
from langchain.messages import AIMessage

@tool
def echo(text: str)->str:
    """返回一个text"""

    return f"echo:{text}"

# 假模型：台词写死在 responses 里。
# 所以输出里如果出现 "echo:1"，那不可能是它编的 —— 只能是 echo 函数真的执行了。
class MyScriptedModel(FakeMessagesListChatModel):

    # 框架每调用一次模型，就会先调一次 bind_tools，把工具清单递给模型。
    # 我们在这里把工具名打印出来 —— 这是唯一能"看见"模型手上有什么工具的办法。
    # 打印几次，就说明模型被调用了几轮。
    def bind_tools(self, tools, **kwargs):
        for t in tools:
            print(t.name)
        return self

if __name__ == "__main__":
    # model = MyScriptedModel(responses=[AIMessage(content="hi")])
    agent = create_deep_agent(
        model= MyScriptedModel(
            responses=[
                # 第一句台词：提出 echo 的工具调用请求（content 是空的）
                # tool_calls 必须放在第一条，否则模型一上来就说"hi"，循环直接结束
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name":"echo",
                            "args":{"text":"1"},
                            "id":"tool-call-1"
                        }
                    ]
                ),   
                # 第二句台词：读到工具结果之后的收尾回复
                AIMessage(
                    content="hi"
                ),             
                # AIMessage(
                #     content="",
                #     tool_calls=[
                #         {
                #             "name":"write_file",
                #             "args":{"text":"hi"},
                #             "id":"tool-call-2"
                #         }
                #     ]
                # )

            ]
        ),
        tools=[echo]     # 我们自己的工具只有一个；其余 8 个是 Deep Agent 的中间件给的
        # 注意这里没有传 middleware=，所以工具清单里没有 write_todos
        # 对比 my_deepagent/demo_binding.py：那里显式挂了 TodoListMiddleware，工具就多一个
    )
    r = agent.invoke(
        {
            "messages":[("user","hi")]
        }
    )
    # m.type 是消息角色：human / ai / tool
    # 这里截前 60 个字符，因为超长输入时 content 会非常长
    # 每一行后面直接标出"这条是什么"，这样光看终端输出就能读懂整条链
    for m in r["messages"]:
        if m.type == "human":
            note = "← 我发的输入"
        elif m.type == "tool":
            note = "← ★ 工具执行结果：echo 真正被调用后返回的值"
        elif m.type == "ai" and not m.content:
            note = "← 模型的工具请求（content 是空的，请求在 tool_calls 里）"
        else:
            note = "← 模型读到工具结果后的最终回复"
        print(f"这条消息的 type 是 {m.type}，content 是：{str(m.content)[:60]}", note)
