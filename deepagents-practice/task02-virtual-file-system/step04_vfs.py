# ══════════════════════════════════════════════════════════════════
# Task 2 · 第 3 章 · 第 1 步
#
# 要解决的问题：
#   Agent 用 write_file 写了一个「文件」—— 这个文件到底写到哪里去了？
#
# 教案依据（notebooks/ch02/02-research-assistant.md）：
#   :173  write_file 写入的是 Agent 状态里的虚拟文件，不会在你的电脑上创建文件。
#   :364  result["files"]：虚拟文件系统，键是路径，值里的 content 是文件内容，
#         另有创建和修改时间。
#   :302  传给工具的 research/notes.md 会保存成 /research/notes.md，
#         用 Deep Agents 自己的 validate_path 做同样的转换。
#
# 这一步其实只做一件事：把「文件在哪」这个事实亲眼看到。
# ══════════════════════════════════════════════════════════════════

from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends.utils import validate_path
from langchain.messages import AIMessage
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel

# ── 要写入的东西 ────────────────────────────────────────────────
# REPORT_PATH 以 "/" 开头，这是「虚拟路径」。
# 它不是电脑上的 F:\... —— 它是 Agent 眼里看到的路径，
# 具体落到哪儿由 Backend 决定。这是整章的核心。
REPORT_PATH = "/report.md"
REPORT_TEXT = "# 实验报告\n\n这是写进虚拟文件系统的一段内容。\n"

# 模块级标志：说明书只打一次，不刷屏。
# 注意别写成类属性 —— MyScriptedModel 是 Pydantic 模型，
# 下划线开头的类属性会被 Pydantic 当成「私有属性描述符」，判断恒为真。
_DETAIL_PRINTED = False


class MyScriptedModel(FakeMessagesListChatModel):
    """台词写死的假模型：不思考，只按顺序念台词。"""

    # 框架每调用一次模型，都会先调一次 bind_tools，把工具清单递进来。
    # 借这个钩子观察「模型手上有什么工具」—— 这是唯一能看见它的办法。
    def bind_tools(self, tools, **kwargs):
        global _DETAIL_PRINTED

        # 每轮都打名字：打几行，就说明模型被调用了几轮
        print("【模型这一轮拿到的工具】")
        print("  " + " / ".join(t.name for t in tools))

        # 工具的参数说明只详细打一次 —— 参数名不用猜，让工具自己说
        if not _DETAIL_PRINTED:
            _DETAIL_PRINTED = True
            spec = next(t for t in tools if t.name == "write_file")
            print()
            print("【write_file 的说明书（工具自己给的，不用猜）】")
            for arg, info in spec.args.items():
                print(f"  {arg}: {info.get('description')}")

        print()
        return self


def build_agent():
    """组装第一个会写文件的 Deep Agent。"""
    return create_deep_agent(
        model=MyScriptedModel(
            responses=[
                # 第 1 句台词：请求调用 write_file
                #   请求工具时 content 必须是空字符串（Task 1 学过）
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "write_file",
                            "args": {
                                # 这两个参数名来自上面的说明书
                                "file_path": REPORT_PATH,
                                "content": REPORT_TEXT,
                            },
                            "id": "call-write-1",
                        }
                    ],
                ),
                # 第 2 句台词：读到工具结果之后的收尾
                AIMessage(content="报告已写入。"),
            ]
        ),
        # 不传 tools=   ：这一步只用 Deep Agent 自带的文件工具
        # 不传 backend=：用默认后端 —— 这正是本步要观察的对象
    )


def show_messages(messages):
    """把消息链按角色逐条打印出来。"""
    print("【消息链】")
    for m in messages:
        text = repr(str(m.content)[:40])
        if m.type == "human":
            note = "← 用户输入"
        elif m.type == "ai" and getattr(m, "tool_calls", None):
            note = f"← 模型提出工具请求：{m.tool_calls[0]['name']}"
        elif m.type == "tool":
            note = f"← 工具真实返回  status={m.status}  id={m.tool_call_id}"
        else:
            note = "← 模型读到结果后的最终回复"
        print(f"  [{m.type:5}] {text:42} {note}")
    print()


def show_state(result):
    """把 Agent 跑完之后的「状态」结构打出来。"""
    print("【状态里有哪些键】")
    print("  " + ", ".join(sorted(result.keys())))
    print()

    files = result.get("files", {})
    print("【虚拟文件系统 result['files']】")
    print(f"  文件路径：{sorted(files) or '（空）'}")
    for path, data in files.items():
        print(f"  单个文件的字段：{sorted(data.keys())}")
        print(f"  ── {path} 的内容 ──")
        for line in str(data["content"]).splitlines():
            print(f"      {line}")
    print()


def assert_with_validate_path(result):
    """教案 ch02/02:338-345 的检查手法：先用断言把结论钉死，再打印。

    为什么需要 validate_path？
      模型可能写 "/report.md"，也可能写 "report.md"。
      框架会把它们统一成带前导斜杠的形式；用同一个函数做同样的转换，
      断言才不会因为路径写法不同而误判。
    """
    normalized = validate_path(REPORT_PATH)
    files = result.get("files", {})
    assert normalized in files, f"{normalized} 应出现在虚拟文件系统中"
    assert files[normalized]["content"] == REPORT_TEXT, "文件内容与写入的不一致"
    print(f"【断言通过】validate_path({REPORT_PATH!r}) -> {normalized!r}，内容逐字一致")
    print()


def check_disk():
    """去磁盘上找一遍：它到底有没有落到电脑的文件系统里？"""
    print("【磁盘检查】")
    print(f"  当前工作目录：{Path.cwd()}")
    for p in [Path.cwd() / "report.md", Path.cwd() / REPORT_PATH.lstrip("/")]:
        print(f"    {str(p):60} 存在？ -> {p.exists()}")
    print()


if __name__ == "__main__":
    agent = build_agent()
    result = agent.invoke({"messages": [("user", "把报告写到 /report.md")]})

    show_messages(result["messages"])
    show_state(result)
    assert_with_validate_path(result)
    check_disk()

    print("【这一步的结论】")
    print("  1. write_file 执行成功了（status=success），内容一个字不差。")
    print("  2. 但它存在 result['files'] 里 —— 那是 Agent 的『状态』，不是电脑磁盘。")
    print("  3. 磁盘上找不到这个文件。想让它落到磁盘，要换一个后端。")
