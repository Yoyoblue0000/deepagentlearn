# ══════════════════════════════════════════════════════════════════
# Task 2 · 第 3 章 · Lite 第 2 步
#
# 要解决的问题：
#   怎么让 Agent 写出来的「文件」真的落到项目目录里，能用手找到？
#
# step04 已经证明：默认后端（StateBackend）把文件写进「状态」，磁盘上没有。
# 这一步换一个后端 —— 同一份代码，文件就落到磁盘上了。
#
# 教案依据：
#   content/ch03-virtual-filesystem.md（FilesystemBackend 一节）
#     agent = create_deep_agent(model=model,
#                               backend=FilesystemBackend(root_dir=".", virtual_mode=True))
#
#   notebooks/ch11/01-filesystem-permissions.md:175
#     虚拟路径 /workspace/notes.txt 对应 root 目录下的 workspace/notes.txt；
#     Agent 工具访问时则由 Backend 完成路径映射。
#
#   notebooks/ch11/01-filesystem-permissions.md:233
#     从磁盘反查虚拟路径： "/" + file.relative_to(root).as_posix()
#
# 本步让 Agent 走完 Lite 要求的三件事：写入 → 读回 → 修改。
# ══════════════════════════════════════════════════════════════════

from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain.messages import AIMessage
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel

# ── 路径与内容 ──────────────────────────────────────────────────
# HERE 是这个脚本所在的目录（task02-virtual-file-system/）
HERE = Path(__file__).resolve().parent

# WORKSPACE 就是交给后端的 root_dir —— Agent 只能在这个目录里活动。
# 注意：这是「电脑磁盘上的真实目录」。
WORKSPACE = HERE / "agent_workspace"

# REPORT_PATH 是「虚拟路径」，Agent 眼里只有它。
# 虚拟路径 /report.md  +  root_dir agent_workspace/
#              ↓  Backend 负责翻译
# 真实文件 agent_workspace/report.md
REPORT_PATH = "/report.md"

ORIGINAL = "# 实验报告\n\n第一版内容：这一句等一下要被改掉。\n"
EDITED = "# 实验报告\n\n第二版内容：这一句已经被 edit_file 改过了。\n"
OLD_SNIPPET = "第一版内容：这一句等一下要被改掉。"
NEW_SNIPPET = "第二版内容：这一句已经被 edit_file 改过了。"

_DETAIL_PRINTED = False


class MyScriptedModel(FakeMessagesListChatModel):
    """台词写死的假模型：不思考，只按顺序念台词。"""

    def bind_tools(self, tools, **kwargs):
        global _DETAIL_PRINTED
        print("【模型这一轮拿到的工具】")
        print("  " + " / ".join(t.name for t in tools))
        if not _DETAIL_PRINTED:
            _DETAIL_PRINTED = True
            for name in ("write_file", "edit_file"):
                spec = next(t for t in tools if t.name == name)
                print(f"  {name} 参数：{list(spec.args)}")
        print()
        return self


def build_agent():
    """组装一个把文件写到磁盘上的 Deep Agent。

    和 step04 唯一的区别，就是多了 backend= 这一行。
    """
    WORKSPACE.mkdir(parents=True, exist_ok=True)

    return create_deep_agent(
        model=MyScriptedModel(
            responses=[
                # 第 1 步：写入
                AIMessage(
                    content="",
                    tool_calls=[{
                        "name": "write_file",
                        "args": {"file_path": REPORT_PATH, "content": ORIGINAL},
                        "id": "call-write",
                    }],
                ),
                # 第 2 步：读回（证明写进去的能拿出来）
                AIMessage(
                    content="",
                    tool_calls=[{
                        "name": "read_file",
                        "args": {"file_path": REPORT_PATH},
                        "id": "call-read",
                    }],
                ),
                # 第 3 步：修改（edit_file 只改局部，不像 write_file 整份覆盖）
                AIMessage(
                    content="",
                    tool_calls=[{
                        "name": "edit_file",
                        "args": {
                            "file_path": REPORT_PATH,
                            "old_string": OLD_SNIPPET,
                            "new_string": NEW_SNIPPET,
                        },
                        "id": "call-edit",
                    }],
                ),
                # 收尾
                AIMessage(content="写入、读回、修改，三步都完成了。"),
            ]
        ),
        # ★ 和 step04 唯一的区别：指定后端，把文件落到真实目录
        backend=FilesystemBackend(root_dir=WORKSPACE, virtual_mode=True),
    )


def show_messages(messages):
    print("【消息链】")
    for m in messages:
        text = repr(str(m.content)[:34])
        if m.type == "human":
            note = "← 用户输入"
        elif m.type == "ai" and getattr(m, "tool_calls", None):
            note = f"← 请求 {m.tool_calls[0]['name']}"
        elif m.type == "tool":
            note = f"← {m.name}  status={m.status}"
        else:
            note = "← 最终回复"
        print(f"  [{m.type:5}] {text:38} {note}")
    print()


def show_state(result):
    """换了后端之后，状态里的 files 应该空了 —— 这正是关键对照。"""
    print("【状态里有哪些键】")
    print("  " + ", ".join(sorted(result.keys())))
    print(f"  result['files'] = {result.get('files', '（没有这个键）')}")
    print("  ↑ step04 用默认后端时这里有 /report.md；现在空了，因为文件落到磁盘去了")
    print()


def show_disk():
    """到磁盘上，用手能摸到的地方找这份产物。"""
    print("【磁盘上真的找到了吗】")
    real = WORKSPACE / REPORT_PATH.lstrip("/")     # 教案 ch11:175 的映射规则
    print(f"  root_dir     : {WORKSPACE}")
    print(f"  真实文件路径 : {real}")
    print(f"  存在？       : {real.exists()}")

    # 教案 ch11:233 的反查手法：从磁盘文件反推它对应的虚拟路径
    found = {
        "/" + f.relative_to(WORKSPACE).as_posix(): f.read_text(encoding="utf-8")
        for f in sorted(WORKSPACE.rglob("*")) if f.is_file()
    }
    print(f"  目录里的文件 : {sorted(found)}")
    print()
    print("  ── 文件内容 ──")
    for line in real.read_text(encoding="utf-8").splitlines():
        print(f"      {line}")
    print()

    # 断言：磁盘上的内容 == 我们期望的「改完之后」的版本
    assert real.exists(), "磁盘上应该有这个文件"
    assert real.read_text(encoding="utf-8") == EDITED, "磁盘内容应为修改后的版本"
    print("  【断言通过】磁盘内容 == 修改后的版本（说明 edit_file 真的改了磁盘文件）")
    print()


if __name__ == "__main__":
    agent = build_agent()
    result = agent.invoke({"messages": [("user", "写、读、改 /report.md")]})

    show_messages(result["messages"])
    show_state(result)
    show_disk()

    print("【Lite 的三件事都做完了】")
    print("  写入  write_file -> 磁盘上出现 report.md")
    print("  读回  read_file  -> 把内容读出来")
    print("  修改  edit_file  -> 只改一句话，磁盘文件跟着变")
    print(f"  · 产物就在：{WORKSPACE / REPORT_PATH.lstrip('/')}")
