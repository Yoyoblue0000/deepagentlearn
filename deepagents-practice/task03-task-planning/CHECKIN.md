# Task 3 学习打卡：让项目按计划完成（任务规划）

**昵称：** 爱眨眼睛的×0

**群号：** 2群

**课程：** DeepAgents 实战 · 第 4 章

**学习时间：** 2026-10-20

**本次档次：** Lite 打卡级

开头那个问题 —— 为什么复杂任务交给 Agent，它常常做着做着就忘了自己在干嘛？
我的理解是：模型每一步只能看到「消息历史」，而历史会越来越长、还会被总结压缩。
如果没有一份**单独存起来的任务清单**，它就没有稳定的「进度锚点」。
第 4 章给的办法就是 `write_todos`：清单放在 Agent State 的 `todos` 字段里，和消息历史分开管理。

这次做 Lite：让 Agent 用 `write_todos` 列一次计划，亲眼看它从 `pending` 走到 `completed`。

练习过程中使用了 AI 教练的提问和提示；脚本、运行结果和结论由自己跑出来验证。

---

## 一、验证什么

三个问题：

1. `write_todos` 是 Deep Agent 默认就有的吗？
2. 一次多步骤任务中，计划怎么从 `pending` 走到 `completed`？每次更新是「只改一项」还是「整份替换」？
3. 清单全部 `completed`，能不能当作验收通过？

---

## 二、改了什么

新建 [`step06_todo_plan.py`](step06_todo_plan.py)，让 Agent 完成一个 3 步任务：

| 步骤 | 计划内容 | 真实工具调用 |
| --- | --- | --- |
| 1 | 统计素材的字符数 | `count_chars` |
| 2 | 把结果写入 `/task03-report.md` | `write_file` |
| 3 | 读回报告，核对内容 | `read_file` |

关键改动只有中间件这一行：

```python
agent = create_deep_agent(
    model=...,
    tools=[count_chars],
    middleware=[TodoListMiddleware()],   # ★ v0.7 要显式加，默认没有
)
```

另外两处和前面的 Task 不同：

- **对照实验**：分别构建「不挂 / 挂」Todo 中间件的 Agent，直接读工具节点里注册的工具名，证明 `write_todos` 来自中间件。
- **用 `stream(..., stream_mode="values")` 运行**：每执行完一个图节点就拿到一份完整状态，`todos` 一变就打印一版，所以能亲眼看到状态流转，而不是只看最后结果。

模型仍然用台词写死的假模型（`FakeMessagesListChatModel`）。它不会思考，但 `write_todos`、`count_chars`、`write_file`、`read_file` 都是真执行的。

---

## 三、实际结果

### 3.1 先证明：`write_todos` 不是默认工具

```text
不挂 TodoListMiddleware：['count_chars', 'delete', 'edit_file', 'execute', 'glob',
                         'grep', 'ls', 'read_file', 'task', 'write_file']
挂上 TodoListMiddleware：['count_chars', 'delete', 'edit_file', 'execute', 'glob',
                         'grep', 'ls', 'read_file', 'task', 'write_file', 'write_todos']
只在挂上之后才多出来的工具：['write_todos']
```

两次构建都挂了同一个自定义工具 `count_chars`，所以差异只剩 `write_todos` —— 它确实由 `TodoListMiddleware` 提供。

模型这一轮拿到的工具清单里还有 `write_todos`，参数只有一个：

```text
write_todos 的参数：['todos']
```

### 3.2 计划从 pending 一路走到 completed

脚本一共提交了 5 版计划，终端逐版打印：

```text
【计划 #1】
  1. [pending    ] 统计素材的字符数（37 个字符）
  2. [pending    ] 把结果写入 /task03-report.md
  3. [pending    ] 读回报告，核对内容

【计划 #2】
  1. [in_progress] 统计素材的字符数（37 个字符）   ← pending → in_progress
  2. [pending    ] 把结果写入 /task03-report.md
  3. [pending    ] 读回报告，核对内容

【计划 #3】
  1. [completed  ] 统计素材的字符数（37 个字符）   ← in_progress → completed
  2. [in_progress] 把结果写入 /task03-report.md   ← pending → in_progress
  3. [pending    ] 读回报告，核对内容

【计划 #4】
  1. [completed  ] 统计素材的字符数（37 个字符）
  2. [completed  ] 把结果写入 /task03-report.md   ← in_progress → completed
  3. [in_progress] 读回报告，核对内容   ← pending → in_progress

【计划 #5】
  1. [completed  ] 统计素材的字符数（37 个字符）
  2. [completed  ] 把结果写入 /task03-report.md
  3. [completed  ] 读回报告，核对内容   ← in_progress → completed
```

对应的消息链里，每次 `write_todos` 都返回 `status=success`：

```text
[ai  ] ''                              ← 请求 write_todos
[tool] "Updated todo list to [{'content': '统计素"   ← write_todos  status=success
[ai  ] ''                              ← 请求 count_chars
[tool] '37'                            ← count_chars  status=success
...
[ai  ] ''                              ← 请求 read_file
[tool] '@@ lines 1-3 of 3 @@\n# Task 3 报告...'      ← read_file  status=success
[ai  ] '素材共 37 个字符；报告已写入 /task03-report.md 并读回'  ← 最终回复
```

### 3.3 跑完之后的状态

```text
【最终状态里有哪些键】
  files, messages, todos
  todos = [{'content': '统计素材的字符数（37 个字符）', 'status': 'completed'},
           {'content': '把结果写入 /task03-report.md', 'status': 'completed'},
           {'content': '读回报告，核对内容', 'status': 'completed'}]
  files = ['/task03-report.md']
```

脚本最后的断言全部通过：

```text
【断言通过】
  1. 模型成功调用 write_todos 5 次，每次都用新列表替换旧列表
  2. 运行结束时 result['todos'] 逐项等于最后一次提交的清单
  3. 三项状态最终都是 completed
  4. 另外核对了产物：状态里的文件内容和 read_file 读回的正文都正确
```

---

## 四、证据与解释

### 4.1 工具清单的差集，就是「中间件做了什么」的直接证据

挂中间件前后，唯一新增的工具是 `write_todos`。
这比「文档说会加」更直接：**能力是从中间件来的，不是模型自带的。**

教案里对应的一句话是：v0.7 默认不再安装 `TodoListMiddleware`，需要时应明确传入。

### 4.2 每次 `write_todos` 都是整份替换

第 5 次提交的计划，和状态里最终的 `todos` **逐项相等**（脚本用断言核对）。
中间那几版 `in_progress` 并没有被「保留」下来 —— 每次调用都用一个新列表覆盖旧列表。

这解释了消息链里的现象：`write_todos` 的 ToolMessage 内容都是完整清单，而不是一句「第 2 项已改为 completed」。
所以清单的**历史版本**只能从消息链里的每次提交去还原，状态里永远只有最新一版。

### 4.3 `todos` 和 `messages` 是两个独立的字段

最终状态有三个键：`messages`、`files`、`todos`。

- `messages`：完整的对话与工具调用记录
- `files`：Task 2 见过的虚拟文件系统
- `todos`：这一章的任务清单

清单单独存，才有机会在对话被总结压缩后继续存在（教案说的「锚定作用」）。
不过这次没有触发上下文压缩，**「总结后清单还在」这一点本次没有验证**，只是看到了字段确实独立。

### 4.4 `pending → in_progress → completed` 是约定，不是强制状态机

教案特别提醒：这是可用工作方式，不是框架强制执行的状态机。
从源码也能对上：`TodoListMiddleware` 主要做三件事 ——

1. 注入 `write_todos` 工具；
2. 通过 `state_schema` 给状态加上 `todos` 字段；
3. 在模型调用前后注入规划提示词，并拒绝同一轮并行调用多次 `write_todos`。

它**不检查**「你能不能直接跳到 completed」。这次能按顺序走，是因为脚本模型按顺序念台词；
它证明的是**机制跑通**，不能证明真实模型一定会这样规划。

### 4.5 全部 completed ≠ 验收通过

这次特意把两件事分开做：

- `write_todos` 的 `completed` 只是 Agent 自己写入的**进度标记**；
- 产物对不对，用另外的断言检查：状态里的文件内容逐字等于写入内容，`read_file` 也读回了报告正文。

如果只看最后那版「三项全 completed」，其实什么都没证明 —— 清单完成和任务完成是两回事。

### 4.6 `todos` 的参数结构，是工具自己说的

`write_todos` 只有一个参数 `todos`，它的每一项是：

```python
{"content": "任务内容", "status": "pending" | "in_progress" | "completed"}
```

和 Task 2 查 `write_file.args` 的方法一样：参数名和约束不用猜，工具对象自己带着。

---

## 五、下一步修正

1. **这次是脚本模型，不能证明真实模型会主动规划。**
   台词是写死的，`write_todos` 一定会被调用。真实模型可能根本不列计划，或者列了不更新。
   下一步（Basic）换真实模型 + 固定资料，跑一个多步骤任务，再逐项核对产物。

2. **「计划全部 completed」还没有被当成验收清单逐项核对。**
   这次只核对了报告内容。Basic 里要把每条计划拆成可检查的验收项：
   文件是否存在、内容是否包含关键数据、来源能否核实，而不是看状态颜色。

3. **没有验证跨次运行的清单接续。**
   教案说多次 `invoke()` 要接续清单，需要 Checkpointer + 同一个 `thread_id`。
   这次是单次运行，`todos` 只活在这一轮的状态里。

4. **没有对比 Todo 开 / 关。**
   第 3.1 节只对比了「注册了哪些工具」，没有让同一个任务分别在有无 Todo 的情况下各跑一遍。
   这是 Advanced 的内容：固定输入与模型，对比完成情况和调用轨迹。

5. **继续读本章中间件部分。**
   `TodoListMiddleware` 的真身、Node-style 与 Wrap-style Hook 的区别，以及它和 `SummarizationMiddleware` 的配合，这次只读到了概念，没有动手验证。

---

## 运行方式

在 `deepagents-practice` 目录下运行（Lite 不需要 API Key）：

```powershell
cd deepagents-practice
uv sync --frozen
.\.venv\Scripts\python.exe -X utf8 task03-task-planning\step06_todo_plan.py
```

本次环境：Windows / Python 3.12 / deepagents 0.7.22 / langchain 1.4.3。

---

## 引用资料

- 《Deep Agents 实战》第 4 章「任务规划与分解」：
  <https://datawhalechina.github.io/deepagents-in-action/>
- 课程仓库（含本章正文与 Notebook）：
  <https://github.com/datawhalechina/deepagents-in-action>
- 课程离线示例的 `write_todos` 写法：
  `notebooks/ch02/02-research-assistant.md`（规划 → 搜索 → 写笔记 → 更新计划 → 报告）
- 中间件实现（本机安装的 langchain 1.4.3）：
  `langchain/agents/middleware/todo.py` —— `TodoListMiddleware` / `PlanningState` / `write_todos`
