# ══════════════════════════════════════════════════════════════════
# Task 3 · 第 4 章 · Lite
#
# 要解决的问题：
#   复杂任务交给 Agent，它怎么知道自己做到哪一步了？
#   让 Agent 用 write_todos 列一次计划，亲眼看状态从 pending 走到 completed。
#
# 教案依据：
#   content/ch04-task-planning.md
#     - v0.7 默认不安装 TodoListMiddleware，需要 middleware=[TodoListMiddleware()] 显式启用。
#     - write_todos 的每一项是 {"content": ..., "status": ...}，
#       status 只有 pending / in_progress / completed 三种。
#     - 清单保存在 Agent State 的 todos 字段，和消息历史分开管理；
#       每次调用都会用新列表整份替换旧列表。
#   notebooks/ch02/02-research-assistant.md:204-211
#     离线脚本也用 write_todos 演示「先规划 → 再更新」，可作为写法参考。
#
# 本脚本用台词写死的假模型（FakeMessagesListChatModel）：
#   模型不会真的思考，但 write_todos、count_chars、write_file 都是真执行的。
#   这样输出里的每次状态变化，都能确定是框架行为，而不是模型编的。
# ══════════════════════════════════════════════════════════════════

from langchain.agents.middleware import TodoListMiddleware
from langchain.messages import AIMessage
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.tools import tool

from deepagents import create_deep_agent

# ── 素材与产物 ──────────────────────────────────────────────────
SAMPLE = "Deep Agents 把计划、文件和子 Agent 放进同一套运行时里。"
COUNT = len(SAMPLE)  # 中文和标点都按一个字符算
REPORT_PATH = "/task03-report.md"
REPORT_TEXT = f"# Task 3 报告\n\n素材共 {COUNT} 个字符。\n"

# ── 计划内容 ────────────────────────────────────────────────────
# 三项任务对应三次真实工具调用：统计 → 写文件 → 读回。
PLAN = [
    f"统计素材的字符数（{COUNT} 个字符）",
    f"把结果写入 {REPORT_PATH}",
    "读回报告，核对内容",
]


def make_todos(statuses):
    """把三项内容和三种状态拼成 write_todos 要求的列表。"""
    return [{"content": content, "status": status} for content, status in zip(PLAN, statuses)]


@tool
def count_chars(text: str) -> int:
    """统计文本的字符数，包含空格和标点。"""
    return len(text)


_CALLS = 0


class MyScriptedModel(FakeMessagesListChatModel):
    """台词写死的假模型：不思考，只按顺序念台词。"""

    def bind_tools(self, tools, **kwargs):
        global _CALLS
        _CALLS += 1
        # 第一次调用时把工具清单打出来 —— write_todos 只可能来自中间件
        if _CALLS == 1:
            print("【模型拿到的工具】")
            print("  " + " / ".join(t.name for t in tools))
            spec = next(t for t in tools if t.name == "write_todos")
            print(f"  write_todos 的参数：{list(spec.args)}")
            print()
        return self


def build_agent():
    """显式挂上 TodoListMiddleware，其余保持 Deep Agent 默认配置。"""
    return create_deep_agent(
        model=MyScriptedModel(
            responses=[
                # ① 第一次规划：三项都是 pending —— 这是「列计划」
                AIMessage(
                    content="",
                    tool_calls=[{
                        "name": "write_todos",
                        "args": {"todos": make_todos(["pending", "pending", "pending"])},
                        "id": "plan-1",
                    }],
                ),
                # ② 开始第 1 项：pending → in_progress
                AIMessage(
                    content="",
                    tool_calls=[{
                        "name": "write_todos",
                        "args": {"todos": make_todos(["in_progress", "pending", "pending"])},
                        "id": "plan-2",
                    }],
                ),
                # ③ 真正执行第 1 项
                AIMessage(
                    content="",
                    tool_calls=[{
                        "name": "count_chars",
                        "args": {"text": SAMPLE},
                        "id": "call-count",
                    }],
                ),
                # ④ 第 1 项 completed，第 2 项 in_progress
                AIMessage(
                    content="",
                    tool_calls=[{
                        "name": "write_todos",
                        "args": {"todos": make_todos(["completed", "in_progress", "pending"])},
                        "id": "plan-3",
                    }],
                ),
                # ⑤ 真正执行第 2 项
                AIMessage(
                    content="",
                    tool_calls=[{
                        "name": "write_file",
                        "args": {"file_path": REPORT_PATH, "content": REPORT_TEXT},
                        "id": "call-write",
                    }],
                ),
                # ⑥ 第 2 项 completed，第 3 项 in_progress
                AIMessage(
                    content="",
                    tool_calls=[{
                        "name": "write_todos",
                        "args": {"todos": make_todos(["completed", "completed", "in_progress"])},
                        "id": "plan-4",
                    }],
                ),
                # ⑦ 真正执行第 3 项
                AIMessage(
                    content="",
                    tool_calls=[{
                        "name": "read_file",
                        "args": {"file_path": REPORT_PATH},
                        "id": "call-read",
                    }],
                ),
                # ⑧ 三项全部 completed
                AIMessage(
                    content="",
                    tool_calls=[{
                        "name": "write_todos",
                        "args": {"todos": make_todos(["completed"] * 3)},
                        "id": "plan-5",
                    }],
                ),
                # ⑨ 收尾回复：清单完成不等于交付，答案要写在最后一条消息里
                AIMessage(content=f"素材共 {COUNT} 个字符；报告已写入 {REPORT_PATH} 并读回核对。"),
            ]
        ),
        tools=[count_chars],
        # ★ 关键的一行：v0.7 默认没有 write_todos，要显式加中间件
        middleware=[TodoListMiddleware()],
    )


def registered_tools(agent):
    """直接读工具节点里注册了哪些工具（不用真的跑一次 Agent）。"""
    return sorted(agent.nodes["tools"].bound.tools_by_name)


def show_enable_control():
    """对照：挂 / 不挂 TodoListMiddleware，工具清单差在哪。"""
    class ProbeModel(FakeMessagesListChatModel):
        def bind_tools(self, tools, **kwargs):
            return self

    # 两边都挂同一个自定义工具，差异才只剩「中间件带来的工具」
    without = create_deep_agent(
        model=ProbeModel(responses=[AIMessage(content="ok")]), tools=[count_chars]
    )
    with_todo = build_agent()

    a, b = registered_tools(without), registered_tools(with_todo)
    print("【先验证：write_todos 是不是默认就有的】")
    print(f"  不挂 TodoListMiddleware：{a}")
    print(f"  挂上 TodoListMiddleware：{b}")
    print(f"  只在挂上之后才多出来的工具：{sorted(set(b) - set(a))}")
    assert "write_todos" not in a
    assert "write_todos" in b
    print()


def show_plan(todos, previous, number):
    """打印一版计划，并标出和上一版相比变了什么。"""
    print(f"【计划 #{number}】")
    for i, item in enumerate(todos, 1):
        status = item["status"]
        if previous is None:
            change = ""
        else:
            old = previous[i - 1]["status"]
            change = "" if old == status else f"   ← {old} → {status}"
        print(f"  {i}. [{status:11}] {item['content']}{change}")
    print()


def show_messages(messages):
    print("【消息链】")
    for m in messages:
        if m.type == "human":
            note = "← 用户输入"
        elif m.type == "ai" and getattr(m, "tool_calls", None):
            note = f"← 请求 {m.tool_calls[0]['name']}"
        elif m.type == "tool":
            note = f"← {m.name}  status={m.status}"
        else:
            note = "← 最终回复"
        text = repr(str(m.content)[:38])
        print(f"  [{m.type:5}] {text:42} {note}")
    print()


def assert_todos(result):
    """把结论钉死：最后一次提交的计划 == 状态里的 todos，且三项全部完成。"""
    messages = result["messages"]
    calls = {
        call["id"]: call
        for message in messages if isinstance(message, AIMessage)
        for call in message.tool_calls
    }
    plans = [
        calls[m.tool_call_id]["args"]["todos"]
        for m in messages
        if m.type == "tool" and m.name == "write_todos" and m.status == "success"
    ]
    assert len(plans) == 5, f"应该提交 5 次计划，实际 {len(plans)} 次"
    assert result["todos"] == plans[-1], "todos 状态应等于最后一次 write_todos 提交的清单"
    assert all(item["status"] == "completed" for item in result["todos"]), "最后应全部 completed"

    # 清单全部 completed 只是 Agent 自己写的标记；产物对不对，要另外查。
    # 这里同时查状态里的文件内容和 read_file 读回来的结果。
    assert result["files"][REPORT_PATH]["content"] == REPORT_TEXT, "报告内容与写入的不一致"
    reads = [m for m in messages if m.type == "tool" and m.name == "read_file"]
    assert reads and REPORT_TEXT.strip() in reads[0].content, "read_file 没有读回报告正文"

    print("【断言通过】")
    print("  1. 模型成功调用 write_todos 5 次，每次都用新列表替换旧列表")
    print("  2. 运行结束时 result['todos'] 逐项等于最后一次提交的清单")
    print("  3. 三项状态最终都是 completed")
    print("  4. 另外核对了产物：状态里的文件内容和 read_file 读回的正文都正确")
    print()


if __name__ == "__main__":
    show_enable_control()

    agent = build_agent()
    print("【用户任务】统计素材字数 → 写入报告 → 读回核对，并把每一步记进计划")
    print()

    # stream_mode="values"：每一步执行完都吐一份完整状态。
    # todos 变了就打印一版，这样能亲眼看到 pending → in_progress → completed。
    result = None
    previous = None
    number = 0
    for snapshot in agent.stream(
        {"messages": [("user", "统计素材字数，写入报告并核对，把每一步记进计划")]},
        stream_mode="values",
    ):
        result = snapshot
        todos = snapshot.get("todos") or []
        if todos and todos != previous:
            number += 1
            show_plan(todos, previous, number)
            previous = todos

    show_messages(result["messages"])

    print("【最终状态里有哪些键】")
    print("  " + ", ".join(sorted(result.keys())))
    print(f"  todos = {result['todos']}")
    print(f"  files = {sorted(result.get('files', {}))}")
    print()

    assert_todos(result)

    print("【这一步的结论】")
    print("  1. v0.7 不会默认给 write_todos；显式加 TodoListMiddleware 之后，工具清单里才多出它。")
    print("  2. 每一次 write_todos 都是整份替换，不是只改一项；状态里始终只有一份最新清单。")
    print("  3. 清单在 Agent State 的 todos 字段里，和 messages 分开存，所以能单独读出来。")
    print("  4. 三项 completed 只说明 Agent 标记完成；报告内容另用断言核对过，两件事不能混为一谈。")
