# Task 4 学习打卡：把一项工作交给子 Agent

**昵称：** 爱眨眼睛的×0

**群号：** 2群

**课程：** DeepAgents 实战 · 第 5 章

**学习时间：** 2026-10-23

**本次档次：** Lite 打卡级

群公告里那个问题 —— 主 Agent 的「脑子」装不下所有上下文，怎么办？
这一章给的答案是 **Context Quarantine（上下文隔离）**：
把一整块工作交给子 Agent，中间的工具调用记录留在它自己的上下文里，
主 Agent 只收到一句结论。打个比方，主 Agent 是项目经理，子 Agent 是专项负责人，
项目经理不需要参加每一次技术讨论会，只看负责人交上来的总结。

这次做 Lite：造一个职责明确的子 Agent，让它被主 Agent 真正调用一次，
并顺手把「上下文隔离」到底隔离了什么，逐项验证清楚。

练习过程中使用了 AI 教练的提问和提示；脚本、运行结果和结论由自己跑出来验证。

---

## 一、验证什么

四个问题：

1. 子 Agent 怎么声明？主 Agent 怎么把它叫起来？
2. 「上下文隔离」具体隔离了**什么**？子 Agent 的中间调用记录，主 Agent 看得到吗？
3. 子 Agent 写的文件，主 Agent 拿得到吗？
4. 子 Agent 的 `tools` 是「继承」还是「替换」？

---

## 二、改了什么

新建 [`step07_subagent_delegation.py`](step07_subagent_delegation.py)，
用一个固定的本地案例（`storage-plan`：比较 A、B 两种存储方案是否满足约束）走完一次委派。

子 Agent 的声明就是**一个字典**：

```python
researcher = {
    "name": "researcher",
    "description": "研究本地 storage-plan 案例，比较 A、B 两种方案并把带证据的报告写入文件。",
    "system_prompt": "你是研究员。处理 storage-plan 时：\n"
                     "1. 调用 lookup_case 获取资料；\n"
                     "2. 逐条对照约束，用 write_file 写入 /research/storage-choice.md；\n"
                     "3. 报告保留 [A]、[B]、[约束] 三个标签和关键数字；\n"
                     "4. 最终只返回一两句结论和文件路径，不要复制原始资料。",
    "tools": [lookup_case],   # 显式指定 → 完全替换，不继承主 Agent 的自定义工具
}
```

主 Agent 这边，只多传一个 `subagents=[researcher]`，外加一个**只有主 Agent 有**的工具：

```python
agent = create_deep_agent(
    model=ScriptedModel(responder=scripted_reply),
    tools=[draft_outline],      # 主 Agent 独有，用来验证「不继承」
    system_prompt="你是协调者。遇到 storage-plan 研究任务，必须调用 task 并指定 subagent_type=researcher……",
    subagents=[researcher],
)
```

为了看清「谁拿到了什么」，脚本用了两处观察：

| 观察点 | 做法 | 能看到什么 |
| --- | --- | --- |
| 子 Agent 是否真的查了资料 | 在 `lookup_case` 里往外部列表 `lookup_trace` 追加记录 | 中间过程不进入主消息，只能从这里取证 |
| 每一轮各自有哪些工具 | 在模型的 `bind_tools` 里记录工具名 | 主 Agent 与子 Agent 的工具集对照 |

模型仍然是台词写死的脚本模型（参照课程 `ScriptedChatModel` 的写法），
靠「当前手里有没有 `lookup_case`」来区分自己是主 Agent 还是子 Agent。

---

## 三、实际结果

### 3.1 委派确实发生了

```text
【委派：主 Agent 发出的 task 调用】
  subagent_type : researcher
  description   : 研究 storage-plan：读取固定资料，比较 A、B 是否满足约束，
                  把带证据的短报告写入 /research/storage-choice.md，只返回结论。

【回传：子 Agent 交给主 Agent 的内容】
  status = success
  content = 方案 B 满足三项约束，报告已写入 /research/storage-choice.md。
```

主 Agent 交代的是一整块工作，拿回来的只有一句话。

### 3.2 上下文隔离：主 Agent 只看到 `task`

```text
【主 Agent 本轮消息数】4
【消息链】
  [human] '请把 storage-plan 交给 researcher：比较 A、B 哪个满足约束，保存'   ← 用户输入
  [ai   ] ''                                                 ← 请求 task
  [tool ] '方案 B 满足三项约束，报告已写入 /research/storage-choice.md。'   ← task  status=success
  [ai   ] '已收到 task 的结果。'                                    ← 最终回复

【主 Agent 收到的工具结果名】
  ['task']
  ↑ 只有 task：lookup_case / write_file 都发生在子 Agent 自己的上下文里
```

整个第一轮只有 **4 条消息**。子 Agent 内部至少跑了 `lookup_case` 和 `write_file` 两次工具调用，
这两条记录一条都没出现在主 Agent 的消息里。

### 3.3 工具集边界：`tools` 是完全替换

```text
【运行时每一轮拿到的工具】
  主 Agent：delete / draft_outline / edit_file / glob / grep / ls / read_file / task / write_file
  子 Agent：delete / edit_file / glob / grep / lookup_case / ls / read_file / write_file
```

对照着看两行：

- 主 Agent 有 `draft_outline`，子 Agent 没有 → **自定义工具没被继承**
- 子 Agent 有 `lookup_case`，主 Agent 没有 → 子 Agent 自己的工具确实生效了
- 两边都有文件工具、但没有 `task`（子 Agent 不能再往下委派）

教案里写的「显式指定后完全替换（不合并）」，在这里是能直接看到的事实。

### 3.4 文件不隔离：报告回到了主 Agent 的状态里

```text
【共享的文件状态】
  状态里的文件：['/research/storage-choice.md']
  报告存在？True
      [A] 写入 p95 8 ms，成本 0.030 元/GB·月，可用性 99.95%。
      [B] 写入 p95 15 ms，成本 0.015 元/GB·月，可用性 99.90%。
      [约束] p95 < 20 ms；成本 <= 0.020；可用性 >= 99.9%。
      结论：A 的成本超标；方案 B 同时满足三项约束。
```

第一轮结束时，**文件已经在主 Agent 的状态里了，但正文还没进主 Agent 的上下文** ——
上面 3.2 的消息链里只有 `task` 一条工具结果，没有任何 `read_file`。

### 3.5 第二轮：主 Agent 主动读，正文才进来

```text
【第二轮：主 Agent 主动读文件】
  本轮新消息数：4
  read_file 调用：['read_file']
  返回头：@@ lines 1-4 of 4 @@
```

脚本断言了读回的正文与共享状态里的报告逐字一致。

### 3.6 断言全部通过

```text
【断言通过：第一轮】
  1. 主 Agent 用 task 委派给 researcher，且只收到 task 这一条工具结果
  2. lookup_case 真的执行过，但它的原始资料没有进入主 Agent 消息
  3. 报告写进了共享状态，第一轮主 Agent 还没主动读它
  4. 子 Agent 的 tools 完全替换：它有 lookup_case，没有主 Agent 的 draft_outline

【断言通过：第二轮】
  1. 主 Agent 自己调用 read_file 之后，报告正文才进入它的上下文
  2. 读回的正文与共享状态里的报告逐字一致
```

---

## 四、证据与解释

### 4.1 「隔离」隔离的是消息上下文，不是文件

这是我这次最想弄清楚的边界。三样东西要分开看：

| 东西 | 隔不隔离 | 证据 |
| --- | --- | --- |
| 子 Agent 的中间工具调用记录 | ✅ 隔离 | 主 Agent 消息里只有 `task` |
| 子 Agent 的 `system_prompt` / 工具集 | ✅ 各自独立 | 两行工具清单对不上 |
| 共用 Backend 时的文件 | ❌ 不隔离 | 报告出现在主 Agent 的 `files` 状态里 |
| 文件正文进不进主上下文 | 要主动读才进 | 第一轮没有 `read_file`，第二轮才有 |

所以「上下文隔离」的准确说法是：**主 Agent 不会自动看到子 Agent 的过程**，
但状态里的数据（文件）仍然共享。教案里那句「消息隔离不等于文件隔离」，这次是亲手验证的。

### 4.2 为什么 `lookup_case` 的调用记录只能靠外部列表观察

因为子 Agent 的上下文根本不会回到主 Agent 那里。如果不留一份外部记录，
就只能凭「子 Agent 说它查了」来判断 —— 那只是它的自述，不是证据。
`lookup_trace` 相当于在工具里装了个摄像头，记录的是**实际执行**，不是模型的说法。

这和 Task 3 里「`completed` 不等于做对了」是同一个道理：
**要证据，不要自述。**

### 4.3 `tools` 完全替换，这件事有实际后果

如果以为 `tools` 是「合并」，就会以为子 Agent 也能用主 Agent 的自定义工具。
实际是替换：一旦显式写了 `tools`，主 Agent 的工具就**一个都不会给**。

这次 `draft_outline` 只出现在主 Agent 那行清单里，就是这个规则的直接后果。
反过来说，如果确实希望子 Agent 用某个工具，必须自己在它的 `tools` 里写一遍。
这也正好符合教案说的「最小权限原则」：只给它需要的工具。

### 4.4 子 Agent 拿不到 `task`

两行工具清单里都没有 `task`。也就是说子 Agent 不能再往下委派 —— 这是一个单层的委派结构。
教案没有专门强调这一点，但对照清单能直接看出来。

### 4.5 回传内容的质量，取决于子 Agent 的提示词

这次子 Agent 的 `system_prompt` 里明确写了「只返回一两句结论和文件路径，不要复制原始资料」，
所以回传给主 Agent 的只有 20 多个字。

如果去掉这句，子 Agent 完全可能把 `CASE_MATERIAL` 整段贴回来 ——
那样主 Agent 的上下文照样会被撑大，**上下文隔离就白做了**。
所以「返回结果要精简」不是建议，而是这套机制能否成立的前提。

### 4.6 没有 Checkpointer，第二轮必须手动传 `files`

第二轮调用是显式把 `files=first_result["files"]` 传回去的。
没有配置 Checkpointer 时，同一个 Agent 对象**不会**自动记住上一轮的文件。

这一点和 Task 3 的 `todos` 是同一个机制：跨次 `invoke()` 要接续状态，需要 Checkpointer + 同一个 `thread_id`。

---

## 五、下一步修正

1. **这次是脚本模型，不能证明真实模型会主动委派。**
   台词写死了「必须调用 task」，所以委派一定发生。
   真实模型可能自己把活干完、根本不委派，也可能委派给错误的子 Agent。
   这是 Basic 要验证的第一件事。

2. **只验证了「能委派」，没验证「委派得对不对」。**
   `description` 写得好不好，直接决定主 Agent 会不会选对子 Agent。
   这次只有一个子 Agent，没有选择压力；要加第二个角色才能看出路由准不准（Advanced）。

3. **回传内容没有做结构化。**
   现在 `task` 返回的是一句自由文本。教案里提到可以用 `response_format` 让子 Agent 返回 JSON，
   方便程序化处理，这次没有试。

4. **只用了 `StateBackend`，没试文件系统后端。**
   `FilesystemBackend` 下子 Agent 写的文件会不会直接落磁盘、主 Agent 的 `files` 状态会怎样，这次没看。

5. **没有对比「不用子 Agent」的成本。**
   教案说子 Agent 有开销（多一次模型调用、多一层上下文）。这次没做对照，
   所以说不清「隔离带来的收益」是否值得这些开销 —— 这是 Advanced 的内容。

---

## 运行方式

在 `deepagents-practice` 目录下运行（Lite 不需要 API Key）：

```powershell
cd deepagents-practice
uv sync --frozen
.\.venv\Scripts\python.exe -X utf8 task04-subagents\step07_subagent_delegation.py
```

本次环境：Windows / Python 3.12 / deepagents 0.7.22 / langchain 1.4.3。

---

## 引用资料

- 《Deep Agents 实战》第 5 章「子 Agent 与上下文隔离」：
  <https://datawhalechina.github.io/deepagents-in-action/>
- 课程仓库（含本章正文与 Notebook）：
  <https://github.com/datawhalechina/deepagents-in-action>
- 第 5 章配套实验 Notebook（`lookup_trace` 观察手法、消息/文件边界检查）：
  <https://github.com/datawhalechina/deepagents-in-action/blob/main/notebooks/ch05/01-subagent-delegation.ipynb>
- 脚本模型写法参考课程辅助包 `course_notebooks/testing.py` 的 `ScriptedChatModel`：
  <https://github.com/datawhalechina/deepagents-in-action/tree/main/notebooks/src/course_notebooks>
