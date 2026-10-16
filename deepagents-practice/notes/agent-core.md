# Agent / LangChain 概念

> 这个框架特有的概念与 API。学完 LangChain 之后价值会降低，但学的时候最常用。
> 开记于 2026-10-13 ｜ 索引见 [`../knowledge_notes.md`](../knowledge_notes.md)

---

## 工具（Tool）

### 工具对象不是函数：`()` 与 `.invoke()`

- **一句话结论**：`@tool` 装饰后拿到的是一个**工具对象**（`StructuredTool`），它不能像函数那样用 `()` 调用，要用它自己的调用入口 `.invoke(...)`。
- **为什么**：装饰器把原函数换成了框架的对象。这个对象要额外携带名字、描述、参数 schema 等信息，所以调用方式也换了一套。
- **示例**：

  ```python
  from langchain_core.tools import tool

  @tool
  def echo(text: str) -> str:
      """原样返回文本。"""
      return f"echo: {text}"

  echo("hi")                    # TypeError: 'StructuredTool' object is not callable
  echo.invoke("hi")             # 可以：echo: hi
  echo.invoke({"text": "hi"})   # 也可以：echo: hi
  ```

- **踩坑点**：**原函数没有消失**，它被挂在 `.func` 属性上。打印 `type(echo)` 就能看到类型已经变了。

### 属性查找会「往上找类」：`__doc__` 为什么不等于你的 docstring

- **一句话结论**：被装饰成对象之后，`工具.__doc__` 拿到的是**框架类的文档**，不是你写在函数里的那句话。你自己的描述在 `.description` 上。
- **为什么**：装饰后这个名字指向一个**实例**。实例自己没有 `__doc__` 时，Python 沿着"实例 → 类"往上找，于是取到了 `StructuredTool` 这个类的说明。
- **示例**：

  ```python
  print(echo.__doc__)        # Tool that can operate on any number of inputs.  ← 类的
  print(echo.description)    # 原样返回文本。                              ← 你的
  print(echo.func.__doc__)   # 原样返回文本。                              ← 原函数上还留着
  ```

- **踩坑点**：`__doc__` 只在**普通函数**上等于 docstring。一旦被装饰，就要用框架提供的属性。

### `invoke()` 的第二个位置参数不是「第二个工具参数」

- **一句话结论**：`工具.invoke(...)` 只接受**一个**参数装工具入参；第二个位置参数是 `config`（运行配置），不是第二个工具参数。
- **为什么**：`invoke(input, config=None)` 的签名就是这么定的。工具入参必须在**一个**结构里给全。
- **示例**：

  ```python
  add.invoke("1", "2")                      # AttributeError: 'str' object has no attribute 'items'
  add.invoke({"num1": 1, "num2": 2})        # 对：入参全放一个字典里
  add.invoke({"num1": 1, "num2": 2}, config={"tags": ["demo"]})   # 对
  ```

- **踩坑点**：**看报错要看调用栈在哪一层炸的**。这里的 `AttributeError` 发生在 `ensure_config` 里、而不是在你的加法里 —— 说明问题出在"参数的位置"，不是"参数的值"。

### 工具调用的 `args` 键名必须和函数参数名一致

- **一句话结论**：`tool_calls` 里 `args` 字典的键，必须和工具函数的**参数名一字不差** —— 框架是拿它按关键字（`函数(**args)`）去调用的。
- **为什么**：框架不会去猜"`content` 是不是就是 `text`"。名字对不上就是缺参数，校验直接失败。
- **示例**：

  ```python
  @tool
  def echo(text: str) -> str:        # 参数名是 text
      """..."""
      return f"echo: {text}"

  {"name": "echo", "args": {"content": "你好"}}   # ❌ text: Field required
  {"name": "echo", "args": {"text": "你好"}}      # ✅
  ```

- **踩坑点**：参数名就是你写函数时定的那个名字（工具对象的 `.args` 也能查到）。别把它和消息的 `content` 字段搞混。

---

## 模型与工具绑定

### `bind_tools`：模型「能不能用工具」的开关

- **一句话结论**：`bind_tools(tools)` 表示「这个模型可以调用这些工具」，框架靠它把工具清单交给模型。
- **为什么**：`create_agent` 在组装时会去调用模型上的 `bind_tools`。真实模型会把它翻译成发给服务商的请求参数；假模型不需要发给谁，返回自己就够了。
- **示例**：

  ```python
  def bind_tools(self, tools, **kwargs):
      return self        # 假模型：收到工具清单，什么都不用做
  ```

- **踩坑点**：
  - **没有这个方法，`create_agent` 一组装就会失败**（报错里通常直接点名 `bind_tools`）。
  - 父类 `BaseChatModel` 里那个版本是个**空壳，一调用就抛 `NotImplementedError`** —— 所以你必须**自己覆盖它**，不是白拿。
  - 签名要照着父类来：`(self, tools, *, tool_choice=None, **kwargs)`。收窄会破坏契约。

### 假模型的 `responses`：按顺序发放的固定回答

- **一句话结论**：`responses` 是一个**消息对象列表**，假模型第 1 次被调用返回第 1 条，第 2 次返回第 2 条。
- **为什么**：真实模型每次都现场生成回答；假模型不推理，只能照本宣科。所以实验里"模型说了什么"完全由你预先安排。
- **示例**：

  ```python
  from langchain_core.messages import AIMessage

  responses=[AIMessage(content="第一次回答"), AIMessage(content="第二次回答")]
  ```

- **踩坑点**：**列表里必须是消息对象，不能是字典**。传 `[{"content": "hi"}]` 会报 `responses.0.type Field required`。

### 字段类型就是契约：`list[BaseMessage]` 为什么拒绝字典

- **一句话结论**：pydantic 会按字段**声明的类型**做校验，类型不符在**创建对象时**就被拒绝，而不是等运行到一半。
- **为什么**：`responses: list[BaseMessage]` 声明的是「一个列表，元素是消息对象」。传字典进去，校验器发现元素不是 `BaseMessage`，直接报错。
- **示例**：

  ```python
  # 父类声明：responses: list[BaseMessage]
  Model(responses=[{"content": "hi"}])          # ❌ ValidationError
  Model(responses=[AIMessage(content="hi")])    # ✅
  ```

- **踩坑点**：想知道"到底能传什么"，别猜也别试错 —— **直接问它**：

  ```python
  print(Model.model_fields["responses"].annotation)   # list[BaseMessage]
  ```

---

## 消息协议

### `AIMessage.tool_calls`：模型「请求调用工具」的表达方式

- **一句话结论**：模型想调工具时不是靠文字说的，而是在 `AIMessage` 里填一个 `tool_calls` 列表；每个元素是一个字典，描述"调谁、传什么、编号是多少"。
- **为什么**：文字是给人看的，`tool_calls` 是给**框架**看的结构化指令 —— 框架只认它。
- **示例**：

  ```python
  AIMessage(
      content="",                    # 请求在 tool_calls 里，正文就留空
      tool_calls=[{
          "name": "echo",            # 工具名，必须和工具对象的 .name 完全一致
          "args": {"text": "你好"},   # 参数：字典，键名对应工具的参数名
          "id": "call-1",            # 本次调用编号，用来和工具返回值配对
      }],
  )
  ```

- **踩坑点**：`content=""` 是正常的 —— 这一轮模型没说话，它在"举手"要求调工具。之后 `ToolMessage` 会用 `tool_call_id` 把结果**配对回**这个 `id`。

### 工具出错不会让流程崩溃：错误会变成一条 `ToolMessage`

- **一句话结论**：工具参数校验失败、或函数体抛异常时，框架**不终止**流程，而是把错误信息包装成一条 `ToolMessage`（`status='error'`）放回消息列表，让模型看到并有机会改正。
- **为什么**：这是 Agent 的容错设计 —— 一次工具失败不该让整个对话报废。
- **示例**：

  ```
  ToolMessage(content="Error invoking tool 'echo' ... text: Field required ...",
              name='echo', tool_call_id='call-1', status='error')
  ```

- **踩坑点**：**"流程跑完了"不等于"工具成功了"** —— 一定要看 `ToolMessage` 的 `status` 和内容。`status='error'` 时，你的函数体**根本没被执行**（参数校验那关就挡下了）。

### 消息对象的 `.type`：不用判断类型就能分支

- **一句话结论**：LangChain 消息自带 `.type` 字段 —— `HumanMessage` 是 `'human'`、`AIMessage` 是 `'ai'`、`ToolMessage` 是 `'tool'`。
- **为什么**：框架特意提供了这个字段，就是为了省掉 `isinstance` 判断。
- **示例**：

  ```python
  for m in result["messages"]:
      if m.type == "ai":
          print("模型：", m.content)
      elif m.type == "tool":
          print("工具：", m.content)
  ```

- **踩坑点**：`.type` 是**属性，不加括号**。这也顺带解释了当初 `echo.type()` 为什么失败 —— **消息对象有 `.type` 字段，工具对象没有**。

### 消息的简写形式：`("user", "内容")`

- **一句话结论**：`{"messages": [("user", "你好")]}` 里的 `("user", "你好")` 是 LangChain 提供的**简写**，等价于 `HumanMessage(content="你好")`。
- **为什么**：手写消息对象太啰嗦，框架允许用 `(角色, 内容)` 的元组代替，收到时会自动转换。
- **示例**：

  ```python
  agent.invoke({"messages": [("user", "你好")]})
  # 等价于
  agent.invoke({"messages": [HumanMessage(content="你好")]})
  ```

- **踩坑点**：这是**两元素**的元组，正常写就行（只有"单元素元组"才必须加尾逗号）。角色名常用的有 `"user"`、`"system"`。

### Agent 的输入是「状态字典」：键名写错会被静默忽略

- **一句话结论**：`agent.invoke(...)` 收的是**状态字典**，键名必须是状态结构里声明过的（对话记录那个键叫 `messages`）。写了不存在的键，**不报错，直接丢掉**。
- **为什么**：LangGraph 按状态结构读取输入，只认声明过的字段。
- **示例**：

  ```python
  r = agent.invoke({"text": "hi"})                  # ❌ 不报错
  print(r["messages"])                              # 里面根本没有 human 消息！

  r = agent.invoke({"messages": [("user", "hi")]})   # ✅
  print([m.type for m in r["messages"]])            # ['human', 'ai', ...]
  ```

- **踩坑点**：**"不报错"在这里格外危险** —— 输入被丢掉，程序照样跑完。养成习惯：跑完先打印**返回值的结构**（有哪些 key），确认输入真的进去了。

### Harness 白送的工具来自哪些中间件

- **一句话结论**：`create_deep_agent` 默认给你的那些工具**不是凭空来的，是中间件提供的** —— 认工具，就是认中间件。
- **为什么**：所谓 Harness，本质就是**一组预先配好的中间件**；每个中间件往工具清单里注册自己的工具。你只写了一个 `echo`，却看到 9 个工具，差的 8 个就是它们贡献的。
- **各中间件的贡献**（deepagents 0.7 实测）：

  | 中间件 | 提供的工具 | 数量 |
  | --- | --- | --- |
  | `FilesystemMiddleware` | `ls` `read_file` `write_file` `edit_file` `delete` `glob` `grep` | 7 |
  | `SubAgentMiddleware` | `task` | 1 |

- **怎么自己看到**（用 `bind_tools` 当观察窗口）：

  ```python
  class M(FakeMessagesListChatModel):
      def bind_tools(self, tools, **kwargs):
          for t in tools:
              print(t.name)      # 打印出来，就知道 Harness 给了你什么
          return self
  ```

- **踩坑点**：`bind_tools` **每次模型调用前都会被调一次** —— 两轮对话就会打印两遍工具清单。**打印次数 = 模型轮数**，反过来也能用它数轮数。

### `tool.args` 是工具的「说明书」：参数名和约束都在里面

- 一句话结论：不用猜工具要什么参数 —— 工具对象自带参数表，`tool.args` 是 `{参数名: 规格}` 字典。
- 为什么：包装工具时会读函数签名生成 JSON Schema；规格里的 `description` 还带着**约束**
  （7 个文件工具的 `file_path` 都写着 `Must be absolute, not relative`）。
- 示例：

  ```python
  def bind_tools(self, tools, **kwargs):
      for t in tools:
          print(t.name, list(t.args))            # write_file ['file_path', 'content']
          for arg, spec in t.args.items():
              print(f"  {arg}: {spec['description']}")
      return self
  ```

- 踩坑点：只打 `.name` 只知道「有什么工具」，打 `.args` 才知道「怎么用」。参数名写错时函数体一行都不执行。

### Agent 跑完的状态里只有 `messages` 和 `files`

- 一句话结论：没挂 `TodoListMiddleware` 的 Deep Agent，`invoke()` 返回的字典就这两个键。
- 为什么：`messages` 是消息链，`files` 是**虚拟文件系统**。键名不是随便起的 —— `StateBackend`
  就是往 `files` 这个状态通道写数据的。
- 示例：

  ```python
  result = agent.invoke({"messages": [("user", "把报告写到 /report.md")]})
  print(sorted(result.keys()))      # ['files', 'messages']
  print(sorted(result["files"]))    # ['/report.md']
  ```

- 踩坑点：挂了 `TodoListMiddleware` 会多出 `todos` 键。先把 `result.keys()` 打出来，别猜键名。

### 虚拟文件是「带元数据的字典」，不是字符串

- 一句话结论：`result["files"][路径]` 拿到的是字典，正文在 `content` 里，另带时间与编码。
- 为什么：既然叫「文件系统」，每个文件就得像文件 —— 有内容、有创建/修改时间。
- 示例：

  ```python
  data = result["files"]["/report.md"]
  print(sorted(data))          # ['content', 'created_at', 'encoding', 'modified_at']
  print(data["content"])       # '# 实验报告\n...'
  ```

- 踩坑点：直接 `str(result["files"][路径])` 会打印整个字典，看不出正文；要写 `.content`。

### 默认后端把文件写进「状态」，不落磁盘

- 一句话结论：`create_deep_agent()` 不传 `backend=` 时用 `StateBackend` —— `write_file` 会成功、
  内容也一字不差，但**电脑磁盘上找不到这个文件**。
- 为什么：`StateBackend` 的职责就是把文件存进 LangGraph 的 agent state（源码原话：*ephemeral*，
  *persist within a conversation thread but not across threads*）。
  Agent 眼里一律是「虚拟路径」（`/` 开头），落到哪儿由后端决定。
- 示例：

  ```python
  agent = create_deep_agent(model=model)                    # 默认 StateBackend
  from deepagents.backends import FilesystemBackend
  agent = create_deep_agent(model=model,                    # 换后端就落磁盘
                            backend=FilesystemBackend(root_dir=".", virtual_mode=True))
  ```

- 踩坑点：「工具返回 success」只说明工具执行了，**不说明文件落在你想要的地方**。
