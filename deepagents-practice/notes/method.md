# 调试与验证方法

> 不绑定具体语言或框架 —— 是"我怎么知道自己做对了"这类问题。
> 这一类最容易被忽略，但**最值钱**：换个项目、换个语言照样用。
> 开记于 2026-10-13 ｜ 索引见 [`../knowledge_notes.md`](../knowledge_notes.md)

---

### 「能创建」不等于「能用」：测试要覆盖行为

- **一句话结论**：`print(type(x))` 只证明对象造出来了，**不证明它能被正确使用**。真正的验证是把它交给"会使用它的代码"跑一遍。
- **为什么**：很多错误不发生在"创建"时，而发生在"框架按约定调用你"时 —— 签名不对、少实现一个方法、必填内容为空，这些都要跑起来才暴露。
- **示例**：

  ```python
  class M:
      def f(self):        # 少写了一个参数
          return 1

  m = M()
  print(type(m))          # 不报错！
  m.f(1)                  # TypeError: f() takes 1 positional argument but 2 were given
  ```

- **踩坑点**：写完一行测试，问自己一句 —— **「这行代码真的碰到了我想验证的那件事吗？」** 只创建对象不够，要调用它、还要检查**结果**，而不只是"没报错"。

### 证明「装饰后名字指向的对象变了」

- **一句话结论**：最干净的证据是**对比两边的类型**：`type(装饰后的名字)` 和 `type(它.func)`。
- **为什么**：装饰器返回的是新对象，原函数被挂在 `.func` 上。两边类型不同，就说明这个名字已经换了主人。
- **示例**：

  ```python
  print(type(echo))         # <class 'langchain_core.tools.structured.StructuredTool'>
  print(type(echo.func))    # <class 'function'>
  print(echo.func is echo)  # False
  ```

- **踩坑点**：`echo("hi")` 报 `TypeError` 也算证据，但"报错了"不如"类型变了"直接 —— **证明要给出可复现的事实，而不是一次失败的经历**。

### 怎么读 `ValidationError`：字段名 + 缺什么 + 为什么

- **一句话结论**：pydantic 的报错结构是「`N validation errors for 类名`」→「字段路径」→「原因」，照着字段名补就行。
- **为什么**：这类错误发生在**创建对象之前**（校验阶段），不是代码跑到一半才炸 —— 所以别去翻函数体，直接看是哪个字段没给、或者给错了。
- **示例**：

  ```
  ValidationError: 1 validation error for MyScriptedModel
  responses
    Field required [type=missing, input_value={}, input_type=dict]
  ```

  逐行读：有 **1** 个校验错误 → 出问题的字段是 **responses** → 原因是**必填但没给**（`input_value={}` 说明创建时一个参数都没传）。

- **踩坑点**：字段路径带点号时（如 `responses.0.type`），那个 `0` 表示**列表的第 0 个元素** —— 说明问题出在列表**里面**的某个元素，而不是列表本身。

### 看报错要看「在哪一层炸的」

- **一句话结论**：别只读报错的最后一行，要顺着**调用栈**看错误发生在哪一层 —— 那一层决定了问题的性质。
- **为什么**：同一个异常类型，炸在不同位置意味着完全不同的原因。
- **示例**：

  ```
  base.py   763  in invoke          → tool_input, kwargs = _prep_run_args(input, config, ...)
  base.py  1367  in _prep_run_args  → config = ensure_config(config)
  config.py 288  in ensure_config   → for k, v in config.items()
  AttributeError: 'str' object has no attribute 'items'
  ```

  炸点在 `ensure_config` 里、而不是在你的加法函数里 —— 说明问题是**参数的位置**不对，不是**参数的值**不对。

- **踩坑点**：只看到最后一行的 `AttributeError` 很容易往错误的方向查。**从下往上看栈帧，找到第一个属于"你的代码"的那层**，那才是问题的起点。

### 用一个「干净环境」隔离变量，别在污染的环境里猜

- **一句话结论**：当错误**可能**来自"环境残留"时（缓存、锁、上次中断的进程），**换一个干净的环境跑一次**，比在原地反复猜测快得多。
- **为什么**：环境残留会和真正的错误**叠在一起**，让你看到的是次要症状，而不是根因。隔离掉干扰项，真正的错误才会露出来。

- **示例**（一次真实的排查）：

  ```
  症状：uv sync 一直报「等待锁超时 (300s)」
  猜测：上次强杀进程留下的陈旧锁
  验证：用 File.Open(..., Share.None) 打开锁文件 —— 成功了
  结论：判定为陈旧锁 → 挪走它 → 重试 → 还是失败（说明判断错了）

  改进：换一个干净的缓存目录重跑
        → 锁的问题消失，露出真正的错误：
          fatal: unable to access 'https://github.com/...': Could not connect to server
  ```

  真正的根因有**两个**，而第一个（锁）一直掩盖着第二个（网络）。**换环境是让第一个消失的最快办法。**

- **踩坑点**：
  - **Windows 的字节范围锁（`LockFileEx`）用共享模式检测不出来** —— `File.Open(path, ..., Share.None)` 能打开，**不代表**没有别的进程锁着它。别用这个方法证明"这个锁是陈旧的"。
  - 有**并发进程**在跑同类工具时，先怀疑**并发争抢**，而不是陈旧残留。
  - 通用手法：**换缓存目录 / 换工作副本 / 换干净容器** —— 让干扰项消失，看剩下什么。

### 虚拟文件的证据在「状态」里，不在磁盘上

- 一句话结论：要证明 Agent 写了个文件，去 `result["files"]` 取证，不要去文件管理器里找。
- 为什么：默认后端根本不碰磁盘；去磁盘找必然空手，还会误判成「我写错了」。
- 示例：

  ```python
  files = result.get("files", {})
  print(sorted(files))                  # ['/report.md']
  assert "/report.md" in files
  ```

- 踩坑点：换成 `FilesystemBackend` 之后**两处都要查** —— 状态里没有、磁盘上才有。
  这个反差正是「后端决定落点」的直接证据。

### 断言之前先统一「表达形式」

- 一句话结论：比较路径、JSON、时间这类**有多种写法**的东西时，先归一化，再断言。
- 为什么：模型写 `/report.md` 还是 `report.md` 都合法，框架内部会统一；
  断言若用原样对比，失败原因会变成「写法不同」而不是「行为不对」。
- 示例：

  ```python
  from deepagents.backends.utils import validate_path

  normalized = validate_path("report.md")     # -> '/report.md'
  assert normalized in result["files"]
  ```

- 踩坑点：`validate_path` 还会**拒绝 Windows 绝对路径**（`C:/`、`F:/`），
  因为虚拟路径体系里不允许出现真实盘符。

### 想看清「每一步状态怎么变」，用 `stream_mode="values"`

- **一句话结论**：`agent.invoke()` 只给最终状态；`agent.stream(..., stream_mode="values")` 每执行完一个图节点就吐一份完整状态，适合观察状态流转。
- **为什么**：`invoke` 把中间过程收起来了。`values` 模式相当于在每一步后拍一张快照，比较相邻两张就能看到哪个字段变了。
- **示例**：

  ```python
  previous = None
  for snapshot in agent.stream(inputs, stream_mode="values"):
      todos = snapshot.get("todos") or []
      if todos and todos != previous:      # 只在变化时打印
          print(todos)
          previous = todos
  ```

- **踩坑点**：第一份快照是输入状态，`todos` 还不存在；要过滤空值，否则会多打一版「空计划」。

### 进度标记不是结果验证：`completed` ≠ 做对了

- **一句话结论**：`write_todos` 的 `completed` 只是 Agent 自己写的进度标记，不能当作验收通过；产物要另外断言。
- **为什么**：模型可以跳过步骤、写错内容，仍然把清单标成全部完成。教案明确说 `completed` 是「Agent 写入的进度标记」，应用仍需检查产物。
- **示例**：

  ```python
  assert all(t["status"] == "completed" for t in result["todos"])   # 只证明它这么标了
  assert result["files"][REPORT_PATH]["content"] == EXPECTED        # 这才证明产物对
  assert EXPECTED.strip() in read_back_message.content              # 读回也要核对
  ```

- **踩坑点**：别把「清单全绿」当成验收报告。计划项应逐条对应一个可检查的事实：文件在不在、内容对不对、引用能不能核实。
