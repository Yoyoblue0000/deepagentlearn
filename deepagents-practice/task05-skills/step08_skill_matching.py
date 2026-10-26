# ══════════════════════════════════════════════════════════════════
# Task 5 · 第 7 章 · Lite
#
# 要解决的问题：
#   想让 Agent 复用我写好的能力，有没有不改代码、更轻的方式？
#   答案：一个目录 + 一份 SKILL.md。启动时只有 name/description 进提示词，
#   正文等 Agent 判断「这活儿归它管」之后自己 read_file 取。
#
# 教案依据：
#   content/ch07-skills.md
#     - Skill = 目录 + SKILL.md（YAML frontmatter + Markdown 正文）。
#     - description 是 Agent 选择 Skill 的唯一依据，正文不会提前读。
#     - Progressive Disclosure：Metadata（启动）→ 正文（按需 read_file）→ 资源（再按需）。
#     - skills 参数给的是「包含 Skill 子目录的父目录」，不是 SKILL.md 本身。
#   notebooks/ch07/01-skills-progressive-disclosure.md
#     - 用 on_chat_model_start 抄下「每次真正发给模型的请求」。
#     - 用两句只出现在某一层里的文字当观察线索，核对披露顺序。
#     - 脚本模型「没有判断何时需要 Skill 的能力」，所以匹配必须用真实模型验。
#
# 本脚本与 ch07 notebook 的区别：
#   notebook 用脚本模型证明「机制」，这里换成真实模型（硅基流动 Qwen3-Coder-30B），
#   证明「匹配」这件事本身 —— 用户请求里不提 skill 名字，全靠 description 命中。
#   一次正向请求 + 一次无关请求（对照组），看它是「真的匹配上了」还是「每次都读」。
# ══════════════════════════════════════════════════════════════════

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ── 固定路径与线索 ──────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
SKILL_FILE = ROOT / "skills" / "checkin-writer" / "SKILL.md"
SKILL_PATH = "/skills/checkin-writer/SKILL.md"
DRAFT_PATH = "/out/task05-checkin-draft.md"
DRAFT_FILE = ROOT / "out" / "task05-checkin-draft.md"
ENV_FILE = ROOT.parent.parent / "my_deepagent" / ".env"

# 这句话只出现在 SKILL.md 正文里：第一次请求若带着它，说明正文提前进上下文了
BODY_MARKER = "证据不足就写「未验证」，不许补数字"
# 这五个标题也只在正文里：产物里出现它们，说明正文真的被执行了，而不只是被读到
HEADINGS = ["一、验证什么", "二、改了什么", "三、实际结果", "四、证据与解释", "五、下一步修正"]

SYSTEM_PROMPT = "用中文回答。需要读写文件时使用文件工具，不要凭空猜测文件内容。"

# 正向请求：故意不提 skill 名字，只说人话 —— 能不能命中全靠 description
MATCH_REQUEST = """帮我把今天 Task5 的实验整理成一份打卡草稿，用 write_file 写到 {draft}。

材料（都是我这次真跑出来的）：
- 我写了一个 Skill：skills/checkin-writer/SKILL.md，frontmatter 只有 name 和 description，
  正文里写了输出结构和写作规则。
- 挂载方式是 FilesystemBackend + skills=["/skills/"]，模型是硅基流动的 Qwen3-Coder-30B。
- 启动时抓到的系统提示里，只有 checkin-writer 的名字、用途和 SKILL.md 的路径。
- 之后模型自己 read_file 读了 /skills/checkin-writer/SKILL.md，再按正文的结构写产物。

按我们组统一的要求写，别自己发明结构。""".format(draft=DRAFT_PATH)

# 对照组：跟打卡毫无关系，用来排除「反正每次都读一遍」这种解释
CONTROL_REQUEST = "3 的平方加 4 的平方等于几？只回答一个数字，不要用工具。"


# ── 模型：复用 my_deepagent 的硅基流动配置 ──────────────────────
def load_model() -> ChatOpenAI:
    env: dict[str, str] = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip()
    return ChatOpenAI(
        model=env["BUB_MODEL"].split(":", 1)[1],
        api_key=env["BUB_API_KEY"],
        base_url=env["BUB_API_BASE"],
        temperature=0,
        timeout=120,
        max_retries=2,
    )


# ── 观察点：抄下每一次真正发给模型的请求 ────────────────────────
class RecordRequests(BaseCallbackHandler):
    """只观察，不修改输入。记的是「模型实际收到了什么」。"""

    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []

    def on_chat_model_start(self, serialized, messages, **kwargs):  # noqa: ANN001
        batch = messages[0]
        self.requests.append(
            {
                "system": "\n".join(m.text for m in batch if isinstance(m, SystemMessage)),
                "context": "\n".join(m.text for m in batch),
                "tool_ids": {m.tool_call_id for m in batch if isinstance(m, ToolMessage)},
            }
        )


def run(user_query: str) -> tuple[dict, list[dict[str, object]]]:
    recorder = RecordRequests()
    agent = create_deep_agent(
        model=load_model(),
        backend=FilesystemBackend(root_dir=str(ROOT), virtual_mode=True),
        skills=["/skills/"],
        system_prompt=SYSTEM_PROMPT,
    )
    result = agent.invoke(
        {"messages": [{"role": "user", "content": user_query}]},
        config={"recursion_limit": 30, "callbacks": [recorder]},
    )
    return result, recorder.requests


# ── 展示 ────────────────────────────────────────────────────────
def tool_pairs(result: dict) -> list[tuple[dict, ToolMessage]]:
    """把每个工具调用和它的返回按调用 ID 配对：只看「真执行过的」。"""
    calls: dict[str, dict] = {}
    pairs: list[tuple[dict, ToolMessage]] = []
    for message in result["messages"]:
        if isinstance(message, AIMessage):
            for call in message.tool_calls:
                calls[call["id"]] = call
        elif isinstance(message, ToolMessage):
            call = calls.pop(message.tool_call_id)
            assert message.name == call["name"], "工具名与调用对不上"
            pairs.append((call, message))
    assert not calls, "有工具调用没有返回"
    return pairs


def show_run(label: str, result: dict, requests: list[dict[str, object]]) -> tuple[dict, ...]:
    print(f"\n{'═' * 66}\n【{label}】用户请求：{result['messages'][0].text.splitlines()[0][:40]}…")

    pairs = tool_pairs(result)
    print(f"\n  工具调用（{len(pairs)} 次）：")
    for call, reply in pairs:
        print(f"    {call['name']}({call['args']}) → {reply.status}")

    print(f"\n  模型请求（{len(requests)} 次），每次都看它手里有什么：")
    for index, request in enumerate(requests, 1):
        has_body = BODY_MARKER in request["context"]
        has_meta = "checkin-writer" in request["system"]
        stage = "目录 + 正文" if has_body else ("仅目录（含 name/description/路径）" if has_meta else "无 Skill 信息")
        print(f"    第 {index} 次：{stage}")

    print("\n  最终答复：")
    print("    " + result["messages"][-1].text.replace("\n", "\n    ")[:800])
    return tuple(pairs)


# ── 验收 ────────────────────────────────────────────────────────
def check_match(result: dict, requests: list[dict[str, object]]) -> None:
    pairs = tool_pairs(result)
    reads = [call for call, _ in pairs if call["name"] == "read_file"]
    read_paths = [call["args"].get("file_path") for call in reads]
    assert SKILL_PATH in read_paths, f"没有读取 SKILL.md，实际读了：{read_paths}"

    skill_call, skill_reply = next((c, r) for c, r in pairs if c["args"].get("file_path") == SKILL_PATH)
    assert skill_reply.status == "success", "SKILL.md 读取失败"

    # Level 1：启动时只有元数据
    first = requests[0]
    description_line = [line for line in SKILL_FILE.read_text(encoding="utf-8").splitlines()
                        if line.startswith("description:")][0]
    description_text = description_line.split(":", 1)[1].strip()
    assert "checkin-writer" in first["system"], "系统提示里没有 Skill 名字"
    assert SKILL_PATH in first["system"], "系统提示里没有 SKILL.md 路径"
    assert description_text[:30] in first["system"], "系统提示里没有 description"
    assert BODY_MARKER not in first["context"], "正文提前进入了第一次请求"

    # Level 2：正文必须等 read_file 的返回之后才出现
    for request in requests:
        if skill_call["id"] not in request["tool_ids"]:
            assert BODY_MARKER not in request["context"], "没读文件就出现了正文"
    after_read = next(r for r in requests if skill_call["id"] in r["tool_ids"])
    assert BODY_MARKER in after_read["context"], "读完之后正文没有进入上下文"

    # 正文被执行：产物里有那五个标题（结构）以及被要求贴的原始输出（内容）
    text = DRAFT_FILE.read_text(encoding="utf-8")
    positions = [text.find(heading) for heading in HEADINGS]
    assert all(p >= 0 for p in positions), f"产物缺标题：{[h for h, p in zip(HEADINGS, positions) if p < 0]}"
    assert positions == sorted(positions), "标题顺序不对"
    print("\n【断言通过·正向】")
    print("  1. 第一次请求：系统提示里有 checkin-writer 的 name / description / 路径，没有正文")
    print("  2. 模型自己发起 read_file 读 SKILL.md，且读取成功")
    print("  3. 正文只在这次读取之后才进入请求")
    print(f"  4. 产物 {DRAFT_PATH} 含五个标题且顺序正确 → 正文被执行了，不只是被读到")


def show_draft(requests: list[dict[str, object]]) -> None:
    """产物 + 启动开销：说明「多花的 token」到底是几个字。"""
    text = DRAFT_FILE.read_text(encoding="utf-8")
    print(f"\n【产物 {DRAFT_PATH}】")
    print("  " + text.strip().replace("\n", "\n  "))

    skill_lines = [line for line in requests[0]["system"].splitlines()
                   if "checkin-writer" in line or SKILL_PATH in line]
    print("\n【启动开销：元数据 vs 正文】")
    print(f"  第 1 次请求里和这个 Skill 有关的行：{len(skill_lines)} 行 / "
          f"{sum(len(line) for line in skill_lines)} 字符")
    for line in skill_lines:
        print("    " + line)
    print(f"  SKILL.md 全文：{len(SKILL_FILE.read_text(encoding='utf-8'))} 字符 ← 这些只在读取后才花掉")

    section3 = text.split(HEADINGS[2], 1)[-1].split(HEADINGS[3], 1)[0] if HEADINGS[3] in text else ""
    quoted = any(word in section3 for word in ("read_file", "ls(", "→ success", "write_file"))
    print(f"\n  第三段是否贴了原始输出：{'是' if quoted else '否（还是概括性描述）'}")
    print(f"  第三段是否标了「未提供原始输出」：{'是' if '未提供原始输出' in section3 else '否'}")


def check_control(requests: list[dict[str, object]], result: dict) -> None:
    pairs = tool_pairs(result)
    read_paths = [c["args"].get("file_path") for c, _ in pairs if c["name"] == "read_file"]
    print("\n【对照组结果】")
    print(f"  工具调用：{[c['name'] for c, _ in pairs] or '无'}")
    print(f"  read_file 路径：{read_paths or '无'}")
    verdict = "没读 → 是「匹配」而不是「每次都读」" if SKILL_PATH not in read_paths else "也读了 → 存在误召回"
    print(f"  判定：{verdict}")


def main() -> None:
    digest_before = hashlib.sha256(SKILL_FILE.read_bytes()).hexdigest()
    if DRAFT_FILE.exists():
        DRAFT_FILE.unlink()  # 先删掉旧产物，免得把上一次的结果当成本次的

    print(f"Skill 文件：{SKILL_FILE.relative_to(ROOT.parent)}")
    print(f"正文标记：{BODY_MARKER}")

    result, requests = run(MATCH_REQUEST)
    show_run("正向请求", result, requests)
    check_match(result, requests)
    show_draft(requests)

    control_result, control_requests = run(CONTROL_REQUEST)
    show_run("对照组", control_result, control_requests)
    check_control(control_requests, control_result)

    assert hashlib.sha256(SKILL_FILE.read_bytes()).hexdigest() == digest_before, "SKILL.md 被改动了"
    print("\n【SKILL.md 未被改动】hash 前后一致")


if __name__ == "__main__":
    main()
