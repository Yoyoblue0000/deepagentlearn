# ══════════════════════════════════════════════════════════════════
# Task 4 · 第 5 章 · Lite
#
# 要解决的问题：
#   主 Agent 的「脑子」装不下所有上下文，怎么办？
#   答案是把一整块工作委派给子 Agent —— 中间过程留在它自己的上下文里，
#   主 Agent 只收到一句结论。
#
# 教案依据：
#   content/ch05-subagents.md
#     - 子 Agent 用字典声明：name / description / system_prompt 必填。
#     - tools 不写就继承主 Agent，写了就「完全替换」，不是合并。
#     - system_prompt 不继承：每个子 Agent 要有自己的指令。
#     - 主 Agent 通过 task(subagent_type=..., description=...) 委派。
#     - 子 Agent 的中间调用记录不进入主 Agent 对话；共用 Backend 时文件仍可共享。
#   notebooks/ch05/01-subagent-delegation.md
#     - 用 lookup_trace 这个外部列表观察子 Agent 真的调用了资料工具。
#     - 消息隔离 ≠ 文件隔离：文件在状态里，主 Agent 要主动 read_file 才看得到正文。
#
# 本脚本用台词写死的脚本模型：不思考，但 task / lookup_case / write_file /
# read_file 都是真执行的。它验证机制与数据边界，不证明真实模型会主动委派。
# ══════════════════════════════════════════════════════════════════

from collections.abc import Callable, Sequence
from typing import Any

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import Field

from deepagents import create_deep_agent

# ── 固定资料与产物 ──────────────────────────────────────────────
CASE_ID = "storage-plan"
REPORT_PATH = "/research/storage-choice.md"

# 这是一份「教学用」固定资料，数字不代表真实产品测量。
CASE_MATERIAL = """[A] 本地 SSD 池：写入 p95 延迟 8 ms，成本 0.030 元/GB·月，可用性 99.95%。
[B] 对象存储 + 写缓存：写入 p95 延迟 15 ms，成本 0.015 元/GB·月，可用性 99.90%。
[约束] 写入 p95 延迟 < 20 ms；成本 <= 0.020 元/GB·月；可用性 >= 99.9%。"""

REPORT_TEXT = """[A] 写入 p95 8 ms，成本 0.030 元/GB·月，可用性 99.95%。
[B] 写入 p95 15 ms，成本 0.015 元/GB·月，可用性 99.90%。
[约束] p95 < 20 ms；成本 <= 0.020；可用性 >= 99.9%。
结论：A 的成本超标；方案 B 同时满足三项约束。"""

# 子 Agent 的中间过程不进入主 Agent 消息，只能靠这个外部列表观察
lookup_trace: list[dict[str, str]] = []


@tool
def lookup_case(case_id: str) -> str:
    """读取本地固定的存储方案研究材料。case_id 应为 storage-plan。"""
    result = CASE_MATERIAL if case_id == CASE_ID else f"未知案例：{case_id}"
    lookup_trace.append({"case_id": case_id, "result": result})
    return result


@tool
def draft_outline(topic: str) -> str:
    """（主 Agent 专用）给报告列一个提纲。子 Agent 不该拿到这个工具。"""
    return f"{topic}：背景 / 方案对比 / 约束核对 / 结论"


# 每次模型被调用时，记录「这一轮它手上有哪些工具」。
# 主 Agent 和子 Agent 共用同一个模型实例，靠这份记录区分两者。
tool_trace: list[tuple[str, ...]] = []


class ScriptedModel(FakeMessagesListChatModel):
    """按「当前是谁在说话」决定下一句台词的脚本模型。

    同一个模型实例会同时被主 Agent 和子 Agent 使用，
    所以靠 tool_names 区分身份：子 Agent 手里有 lookup_case，主 Agent 没有。
    """

    responder: Callable[[list[BaseMessage], tuple[str, ...]], AIMessage] | None = Field(
        default=None, exclude=True
    )
    responses: list[BaseMessage] = Field(default_factory=list)

    def bind_tools(self, tools: Sequence[Any], **kwargs):
        names = tuple(convert_to_openai_tool(t)["function"]["name"] for t in tools)
        tool_trace.append(names)
        return self.bind(tool_names=names)

    def _generate(self, messages, stop=None, run_manager=None, *, tool_names=(), **kwargs):
        if self.responder is None:
            return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
        return ChatResult(generations=[ChatGeneration(message=self.responder(messages, tool_names))])


def scripted_reply(messages, tool_names):
    """子 Agent：查资料 → 写报告 → 返回结论；主 Agent：委派 → 转述 → 读文件。"""
    called = [
        call["name"] for m in messages if isinstance(m, AIMessage) for call in m.tool_calls
    ]

    if "lookup_case" in tool_names:  # 只有 researcher 注册了资料工具
        if "lookup_case" not in called:
            name, args = "lookup_case", {"case_id": CASE_ID}
        elif "write_file" not in called:
            name, args = "write_file", {"file_path": REPORT_PATH, "content": REPORT_TEXT}
        else:
            return AIMessage(content=f"方案 B 满足三项约束，报告已写入 {REPORT_PATH}。")

    elif isinstance(messages[-1], ToolMessage):  # 主 Agent 刚收到工具结果
        return AIMessage(content=f"已收到 {messages[-1].name} 的结果。")

    else:
        request = next(m.content for m in reversed(messages) if isinstance(m, HumanMessage))
        if "read_file" in request:
            name, args = "read_file", {"file_path": REPORT_PATH}
        else:
            name, args = "task", {
                "subagent_type": "researcher",
                "description": (
                    f"研究 {CASE_ID}：读取固定资料，比较 A、B 是否满足约束，"
                    f"把带证据的短报告写入 {REPORT_PATH}，只返回结论。"
                ),
            }
    return AIMessage(
        content="", tool_calls=[{"name": name, "args": args, "id": f"ch05-{name}"}]
    )


# ── 子 Agent 的声明 ─────────────────────────────────────────────
researcher = {
    "name": "researcher",
    "description": "研究本地 storage-plan 案例，比较 A、B 两种方案并把带证据的报告写入文件。",
    "system_prompt": f"""你是研究员。处理 {CASE_ID} 时：
1. 调用 lookup_case(case_id="{CASE_ID}") 获取资料；
2. 逐条对照约束，用 write_file 把短报告写入 {REPORT_PATH}；
3. 报告保留 [A]、[B]、[约束] 三个标签和关键数字；
4. 最终只返回一两句结论和文件路径，不要复制原始资料。""",
    "tools": [lookup_case],   # 显式指定 → 完全替换，不继承主 Agent 的自定义工具
}


def build_agent():
    return create_deep_agent(
        model=ScriptedModel(responder=scripted_reply),
        tools=[draft_outline],  # 主 Agent 独有的工具；子 Agent 显式写了 tools，不应继承它
        system_prompt=(
            "你是协调者。遇到 storage-plan 研究任务，必须调用 task 并指定 "
            "subagent_type=researcher。资料由 researcher 的 lookup_case 提供，"
            "报告写入虚拟文件。本轮不要自己调用 lookup_case 或 read_file，"
            "收到结果后简短转述；用户之后明确要求读文件时再调用 read_file。"
        ),
        subagents=[researcher],
    )


def show_tools(agent):
    print("【主 Agent 注册的工具】")
    print("  " + " / ".join(sorted(agent.nodes["tools"].bound.tools_by_name)))
    print()


def show_tool_sets():
    """运行时的工具清单：主 Agent 与子 Agent 各拿到什么，一眼对照。"""
    print("【运行时每一轮拿到的工具】")
    seen = []
    for names in tool_trace:
        if names not in seen:
            seen.append(names)
    for names in seen:
        who = "子 Agent" if "lookup_case" in names else "主 Agent"
        print(f"  {who:6}：{' / '.join(sorted(names))}")
    print()
    return seen


def show_delegation(result):
    """把「主 Agent 说了什么、子 Agent 交回了什么」单独挑出来。"""
    messages = result["messages"]
    task_calls = [
        call for m in messages if isinstance(m, AIMessage)
        for call in m.tool_calls if call["name"] == "task"
    ]
    task_results = [m for m in messages if isinstance(m, ToolMessage) and m.name == "task"]

    print("【委派：主 Agent 发出的 task 调用】")
    for call in task_calls:
        print(f"  subagent_type : {call['args']['subagent_type']}")
        print(f"  description   : {call['args']['description']}")
    print()

    print("【回传：子 Agent 交给主 Agent 的内容】")
    for m in task_results:
        print(f"  status = {m.status}")
        print(f"  content = {m.content}")
    print()
    return task_calls, task_results


def show_message_boundary(result):
    """主 Agent 的消息里，应该只看得到 task，看不到子 Agent 的中间调用。"""
    messages = result["messages"]
    print(f"【主 Agent 本轮消息数】{len(messages)}")
    print("【消息链】")
    for m in messages:
        if m.type == "ai" and getattr(m, "tool_calls", None):
            note = f"← 请求 {m.tool_calls[0]['name']}"
        elif m.type == "tool":
            note = f"← {m.name}  status={m.status}"
        elif m.type == "human":
            note = "← 用户输入"
        else:
            note = "← 最终回复"
        print(f"  [{m.type:5}] {str(m.content)[:46]!r:50} {note}")
    print()

    parent_tools = [m.name for m in messages if isinstance(m, ToolMessage)]
    print("【主 Agent 收到的工具结果名】")
    print(f"  {parent_tools}")
    print("  ↑ 只有 task：lookup_case / write_file 都发生在子 Agent 自己的上下文里")
    print()
    return parent_tools


def show_shared_files(result):
    """消息隔离 ≠ 文件隔离：文件仍然回到主 Agent 的状态里。"""
    files = result.get("files", {})
    print("【共享的文件状态】")
    print(f"  状态里的文件：{sorted(files)}")
    report = files.get(REPORT_PATH)
    print(f"  报告存在？{report is not None}")
    if report:
        for line in report["content"].splitlines():
            print(f"      {line}")
    print()
    return report


def run_second_round(agent, first_result):
    """第二轮：用户明确要求读文件，主 Agent 才把正文拉进自己的上下文。"""
    second = agent.invoke({
        "messages": [
            *first_result["messages"],
            {"role": "user", "content": f"请用 read_file 读取 {REPORT_PATH}，再简短告诉我结论。"},
        ],
        "files": first_result["files"],   # 没有 Checkpointer，必须手动把文件传回去
    })
    new_messages = second["messages"][len(first_result["messages"]):]
    reads = [m for m in new_messages if isinstance(m, ToolMessage) and m.name == "read_file"]
    print("【第二轮：主 Agent 主动读文件】")
    print(f"  本轮新消息数：{len(new_messages)}")
    print(f"  read_file 调用：{[m.name for m in new_messages if isinstance(m, ToolMessage)]}")
    for m in reads:
        print(f"  返回头：{str(m.content).splitlines()[0]}")
    print()
    return second, new_messages, reads


if __name__ == "__main__":
    agent = build_agent()
    show_tools(agent)

    first = agent.invoke({
        "messages": [{
            "role": "user",
            "content": (
                f"请把 {CASE_ID} 交给 researcher：比较 A、B 哪个满足约束，"
                "保存有证据的短报告，然后告诉我结论。"
            ),
        }]
    })

    task_calls, task_results = show_delegation(first)
    parent_tools = show_message_boundary(first)
    report = show_shared_files(first)
    tool_sets = show_tool_sets()

    # ① 主 Agent 确实通过 task 委派了 researcher
    assert any(c["args"]["subagent_type"] == "researcher" for c in task_calls), "没有委派给 researcher"
    assert task_results and str(task_results[-1].content).strip(), "task 没有回传结果"
    # ② 子 Agent 真的查了资料（证据在外部列表里，不在主消息里）
    assert any(item["case_id"] == CASE_ID for item in lookup_trace), "researcher 没有调用 lookup_case"
    # ③ 消息边界：子 Agent 的中间调用没有混进主 Agent 的消息
    assert parent_tools == ["task"], f"主 Agent 只应看到 task，实际 {parent_tools}"
    assert "lookup_case" not in str(first["messages"]), "lookup_case 的原始资料不应进入主 Agent 消息"
    # ④ 文件边界：报告写进了共享状态，主 Agent 第一轮还没读到正文
    assert report is not None, f"researcher 没写入 {REPORT_PATH}"
    assert all(label in report["content"] for label in ("[A]", "[B]", "[约束]", "8 ms", "15 ms"))
    assert "[A]" not in str(first["messages"][-1].content), "第一轮主 Agent 不该已看到报告正文"
    # ⑤ tools 完全替换：子 Agent 显式写了 tools，就不继承主 Agent 的 draft_outline
    sub_tools = next(t for t in tool_sets if "lookup_case" in t)
    parent_tools_seen = next(t for t in tool_sets if "lookup_case" not in t)
    assert "draft_outline" in parent_tools_seen, "主 Agent 应拿到自己的 draft_outline"
    assert "draft_outline" not in sub_tools, "子 Agent 不该继承主 Agent 的自定义工具"

    print("【断言通过：第一轮】")
    print("  1. 主 Agent 用 task 委派给 researcher，且只收到 task 这一条工具结果")
    print("  2. lookup_case 真的执行过，但它的原始资料没有进入主 Agent 消息")
    print("  3. 报告写进了共享状态，第一轮主 Agent 还没主动读它")
    print("  4. 子 Agent 的 tools 完全替换：它有 lookup_case，没有主 Agent 的 draft_outline")
    print()

    second, new_messages, reads = run_second_round(agent, first)
    assert reads, "主 Agent 没有调用 read_file"
    assert REPORT_TEXT.strip() in str(reads[-1].content), "读回的内容与共享状态里的报告不一致"
    print("【断言通过：第二轮】")
    print("  1. 主 Agent 自己调用 read_file 之后，报告正文才进入它的上下文")
    print("  2. 读回的正文与共享状态里的报告逐字一致")
    print()

    print("【这一步的结论】")
    print("  1. 子 Agent 是「用字典声明」的：name / description / system_prompt 必填。")
    print("  2. 上下文隔离是真的：lookup_case、write_file 的记录只在子 Agent 那边，主 Agent 只收到 task 一条结果。")
    print("  3. 文件不隔离：共用 Backend 时报告仍在主 Agent 的 files 状态里，但要主动 read_file 才进上下文。")
    print("  4. 子 Agent 的 tools 是「完全替换」：显式写了 lookup_case，就不会继承主 Agent 的自定义工具。")
