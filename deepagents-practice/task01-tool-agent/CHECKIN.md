# Task 1 学习打卡：我的第一个工具 Agent

**昵称：** 爱眨眼睛的×0

**课程：** DeepAgents 实战 · 第 1–2 章

**学习时间：** 2026-10-12 ~ 2026-10-14

这次从一个简单的 Python 工具开始，先跑通 Agent 的工具调用，再把自己写的字符统计工具接进主应用，最后换几种输入看看结果。
Lite、Basic、Advanced 三档都做了，下面按「想验证什么、做了什么、结果、理解、下一步」记录学习过程。


| 档次     | 这次完成的内容                                                            |
| -------- | ------------------------------------------------------------------------- |
| Lite     | 跑通第一个 Deep Agent，调用自己的工具，看懂「请求 → 执行 → 返回」       |
| Basic    | 启动主应用，接入`count_num`，把模型、工具、Middleware、Backend 对应到代码 |
| Advanced | 对比正常、空字符串、长文本输入，并留下 LangSmith Trace                    |

练习过程中使用了 AI 教练的提问和提示，实验脚本与工具代码由自己完成，打卡文档由 AI 协助整理。

## 一、Lite

### 1.1 我想验证什么

模型说要调用工具之后，工具是怎么真正执行的？执行结果又是怎么回到模型手里的？
我想先用简单的 `echo` 工具，把这个过程跑一遍。

### 1.2 我做了什么

写了三个小脚本，每个脚本往前走一步：


| 脚本                                         | 做的事情                                                               |
| -------------------------------------------- | ---------------------------------------------------------------------- |
| [step01_tool.py](step01_tool.py)             | 用`@tool` 定义 `echo` 和加法工具，查看工具名称、说明、参数，并手动调用 |
| [step02_agent_loop.py](step02_agent_loop.py) | 用`create_agent` 跑通一次工具调用，打印消息过程                        |
| [step03_virtual_fs.py](step03_virtual_fs.py) | 换成`create_deep_agent`，接入 `echo`，看看 Deep Agent 自带哪些工具     |

### 1.3 跑出来的结果

第一个脚本里，普通函数和工具对象都能算出 `3`，但调用方式不同：

```python
add_tool_1(1, 2)                        # 普通函数，结果是 3
add_tool.invoke({"num1": 1, "num2": 2})  # 工具对象，结果也是 3
```

打印类型后发现，`add_tool` 已经是 `StructuredTool`，原来的 Python 函数放在它的 `.func` 里。
工具还带着 `name`、`description`、`args`，分别告诉模型「叫什么、能做什么、需要传什么参数」。

第二个脚本跑出了四条消息：


| 消息           | 我看到的内容                                                   |
| -------------- | -------------------------------------------------------------- |
| `HumanMessage` | 用户输入`hi`                                                   |
| `AIMessage`    | 请求调用`echo`，参数是 `{"text": "你好"}`，调用编号是 `call-1` |
| `ToolMessage`  | 工具返回`echo: 你好`，`tool_call_id` 也是 `call-1`             |
| `AIMessage`    | 回复`调用已结束`                                               |

第三个脚本里，自己只传了一个 `echo`，模型却收到了 9 个工具：

```text
ls / read_file / write_file / edit_file / delete / glob / grep / task / echo
```

这次 `echo` 收到的是 `"1"`，工具结果是 `echo:1`，说明自己的工具已经接进 Deep Agent 并执行了。

### 1.4 我的理解

工具调用请求放在 `AIMessage.tool_calls` 里。例如第二个脚本中的请求是：

```python
{"name": "echo", "args": {"text": "你好"}, "id": "call-1"}
```

框架根据工具名称找到 `echo`，把参数传进去执行，再把结果放进 `ToolMessage`。
返回消息中的 `tool_call_id` 和请求里的 `id` 对上，就知道这个结果对应哪次调用。

我现在能把过程串起来了：**模型提出请求 → 框架执行工具 → 结果返回消息链 → 再调用模型回复。**

### 1.5 接下来想做什么

这一步用的是预设回复的假模型，适合先熟悉调用过程。接下来换真实模型，看看它会不会自己选择我的工具。

## 二、Basic

### 2.1 我想验证什么

把工具放进实际应用之后，能不能正常调用？课程里提到的模型、工具、Middleware、Backend，在项目中分别对应哪里？

### 2.2 我做了什么

在 AgentSeek 模板生成的 `my_deepagent` 项目中，找到 [demo_binding.py](../../my_deepagent/src/my_deepagent/demo_binding.py)，加了一个字符统计工具：

```python
def count_num(text: str) -> int:
    """统计文本的字符数，包含空格和标点。"""
    return len(text)
```

然后把它放进创建 Agent 时的工具列表：

```python
tools=[outline_answer, count_num]
```

配置好 `.env` 中的模型和网关参数，并开启 LangSmith，方便查看调用过程。

### 2.3 跑出来的结果

主应用启动后，健康检查接口返回了 HTTP 200：

```text
GET http://127.0.0.1:18088/agent/health → 200
```

模型可用的工具共有 11 个，其中自己接入的是 `count_num`，模板原有的工具是 `outline_answer`。

用下面这句话做字符统计：

```text
用 count_num 统计这句话的字符数：今天天气不错
```

完整请求有 28 个字符，模型传给工具的正文是 `今天天气不错`，共 6 个字符。工具返回 `6`，之后模型再给出最终回复，完整调用链跑通了。

### 2.4 我的理解

把课程中的四个概念放回代码里看，就具体多了：


| 概念       | 项目里对应的地方                                                  | 我的理解                                               |
| ---------- | ----------------------------------------------------------------- | ------------------------------------------------------ |
| 模型       | `demo_binding.py` 的 `settings.require_model()`，配置来自 `.env`  | 负责理解输入、选择工具和组织回复；这次使用 Qwen3-Coder |
| 工具       | `count_num`、`outline_answer`，通过 `tools=[...]` 接入            | 真正完成具体操作的函数                                 |
| Middleware | `middleware=[TodoListMiddleware()]`，以及 Deep Agent 自带的中间件 | 给 Agent 增加能力，比如待办、文件操作和子 Agent        |
| Backend    | 没有手动设置，默认使用`StateBackend`                              | 这里的虚拟文件放在 Agent 状态里                        |

还有一个发现：`tools=[...]` 里写的两个工具，并不是模型手里的全部工具。Deep Agent 的中间件还会加进其他工具。
相比 Lite 的 9 个工具，主应用多了一个自定义工具，以及 `TodoListMiddleware` 提供的 `write_todos`。

### 2.5 接下来想做什么

再通过 AG-UI 网关发一次完整请求，并试试文件读写工具，让 Middleware 和 Backend 的作用更直观。

## 三、Advanced

### 3.1 我想验证什么

正常文本、空字符串、长文本，模型的表现会不会不同？我也想在 Trace 里看看工具请求和执行过程。

### 3.2 我做了什么

继续使用主应用里的 Agent，不改工具代码，只换输入。分别试了正常统计请求、空字符串和长文本，并在 LangSmith 中查看对应记录。

### 3.3 跑出来的结果


| 输入                 | 模型调用的工具 | 返回结果       |
| -------------------- | -------------- | -------------- |
| 统计「今天天气不错」 | `count_num`    | `6`            |
| 空字符串`""`         | `write_todos`  | 更新了待办列表 |
| 长文本               | `count_num`    | `540`          |

这里的数字是工具收到的 `text` 的字符数。例如正常请求中，工具统计的是「今天天气不错」这段正文，返回 `6`。

比较意外的是空输入：这次模型没有调用字符统计工具，而是调用了 `write_todos`，列出一条「理解用户意图」的待办。
这让我注意到，**把工具提供给模型，并不代表模型每次都会使用它。**

留下长文本这次调用的 Trace：

- 项目：`my-deepagent`
- Trace ID：`01a1382b-e95c-78e2-a7bc-70d6f5553808`
- 查看入口：[LangSmith](https://smith.langchain.com)

### 3.4 我的理解

在 Trace 里展开工具节点后，我看到调度层拿到工具名称、参数和调用编号，而 `count_num` 函数实际收到的是 `text`。
函数返回整数 `540`，消息里的结果则显示为 `"540"`。

这和 Lite 里看到的过程对上了：模型发请求，框架负责调用函数，再把结果包装成 `ToolMessage` 返回。
`id` 和 `tool_call_id` 用来对应请求与结果，`status` 可以帮助查看这次调用是否成功。

之前还遇到过把参数名写成 `content` 的情况，但函数需要的是 `text`，结果就在参数检查时出错了。
所以排查工具调用时，我会先看请求里的参数有没有写对，再看工具执行结果。

### 3.5 接下来想做什么

多试几次空输入，看看是否还会选择 `write_todos`；再换一个模型，对比工具调用的表现。
之后继续学习第 3 章的虚拟文件系统。

## 运行方式

在仓库根目录运行 Lite 脚本：

```powershell
cd deepagents-practice
uv sync --frozen
.\.venv\Scripts\python.exe -X utf8 task01-tool-agent\step01_tool.py
.\.venv\Scripts\python.exe -X utf8 task01-tool-agent\step02_agent_loop.py
.\.venv\Scripts\python.exe -X utf8 task01-tool-agent\step03_virtual_fs.py
```

主应用的启动方式和请求样例见 [README](../../README.md)，配置参考 [.env.example](../../my_deepagent/.env.example)。

本次环境：Windows / Python 3.12。Lite 使用 deepagents 0.7.22，主应用使用 0.7.8，两个项目各用自己的 `.venv`。

这次最大的收获，是把工具定义、模型请求、函数执行和消息返回连起来看了一遍。接下来再学文件系统和子 Agent 时，就有一个具体的调用过程可以参考了。
