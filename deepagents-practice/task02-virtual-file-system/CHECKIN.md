# Task 2 学习打卡：让成果留在文件里（虚拟文件系统）

**昵称：** 爱眨眼睛的×0

**课程：** DeepAgents 实战 · 第 3 章

**学习时间：** 2026-10-16

**本次档次：** Lite 打卡级

这次想搞清楚一件事：Agent 用 `write_file` 写出来的「文件」，到底存到哪儿去了。
做了两个脚本 —— 第一个用默认后端，第二个把后端换成文件系统 —— 然后去项目目录里亲手找那份产物。

练习过程中使用了 AI 教练的提问和提示，脚本与结论由自己跑出来验证。

---

## 一、验证什么

三个问题：

1. Agent 写完文件之后，这个文件**在电脑磁盘上吗**？
2. 要让它真的落到项目目录里，**需要改什么**？
3. 「写入 → 读回 → 修改」这条链路，每一步长什么样？

---

## 二、改了什么

在 `task02-virtual-file-system/` 下新建两个脚本：

| 脚本 | 做什么 | 后端 |
| --- | --- | --- |
| `step04_vfs.py` | 写一个文件，再从 Agent 的**状态**里把它读回来 | 默认（`StateBackend`） |
| `step05_filesystem.py` | 写入 → 读回 → 修改，产物落到**项目目录** | `FilesystemBackend` |

两个脚本**只差一行**：

```python
backend=FilesystemBackend(root_dir=WORKSPACE, virtual_mode=True)
```

---

## 三、实际结果

### 3.1 step04：默认后端把文件写进「状态」

跑完之后，Agent 返回的字典里只有两个键：

```text
【状态里有哪些键】
  files, messages

【虚拟文件系统 result['files']】
  文件路径：['/report.md']
  单个文件的字段：['content', 'created_at', 'encoding', 'modified_at']
```

`write_file` 返回的是 `Updated file /report.md`，`status=success`，内容也一个字不差。

但去磁盘上找 —— **找不到**：

```text
【磁盘检查】
    ...\deepagents-practice\report.md 存在？ -> False
```

### 3.2 step05：换成文件系统后端，产物真落到磁盘

同一个 Agent、同一套工具，只换了后端：

```text
【状态里有哪些键】
  messages
  result['files'] = （没有这个键）
```

**状态里连 `files` 这个键都消失了**，因为文件不再存进状态，而是直接写到了磁盘：

```text
【磁盘上真的找到了吗】
  真实文件路径 : ...\task02-virtual-file-system\agent_workspace\report.md
  存在？       : True
  目录里的文件 : ['/report.md']

  ── 文件内容 ──
      # 实验报告

      第二版内容：这一句已经被 edit_file 改过了。
```

### 3.3 「写入 → 读回 → 修改」三步都跑通

| 步骤 | 工具 | 工具返回 |
| --- | --- | --- |
| 写入 | `write_file` | `Updated file /report.md` |
| 读回 | `read_file` | `@@ lines 1-3 of 3 @@` + 正文 |
| 修改 | `edit_file` | `Successfully replaced 1 instance(s)` |

三步的 `status` 都是 `success`。

### 3.4 亲手在项目目录里找到产物

```text
deepagents-practice/task02-virtual-file-system/agent_workspace/report.md
（76 字节）
```

这份文件已经跟着代码一起提交进仓库，**点开就能看到**。

---

## 四、证据与解释

### 4.1 工具的参数名是查出来的，不是猜的

在 `bind_tools` 里把工具的 `.args` 打出来：

```text
  write_file 参数：['file_path', 'content']
  edit_file  参数：['file_path', 'old_string', 'new_string', 'replace_all']
```

参数表里还带着约束。比如 `file_path` 的说明写着 **"Must be absolute, not relative"** —— 所以传进去的是 `/report.md` 这种带前导斜杠的路径。

一开始我按 `echo` 的写法给它传了 `text`，那个参数根本不存在。

### 4.2 核心结论：文件存哪，由 Backend 决定

Agent 看到的**永远是一个虚拟路径**（`/report.md`）；**它落到哪儿，由后端翻译**：

```text
虚拟路径 /report.md
      ├─ StateBackend      → 存进 Agent 状态里的 files 键（磁盘上没有）
      └─ FilesystemBackend → 落到 root_dir 下的 report.md（真文件）
```

翻译规则很简单：去掉虚拟路径开头的斜杠，拼到 `root_dir` 后面。
所以 `/report.md` + `root_dir=agent_workspace/` = `agent_workspace/report.md`。

**同一份代码只改一行，产物就从「状态里的一个字典」变成「一个能用编辑器打开的文件」。**

### 4.3 状态里的 `files` 键消失，本身就是证据

step04 的状态是 `files, messages`；step05 只剩 `messages`。

因为 `StateBackend` 的职责就是往 `files` 这个状态键里写数据；换成 `FilesystemBackend` 之后，没有东西再往那儿写了。**这个「少了一个键」比任何解释都直接。**

### 4.4 `write_file` 和 `edit_file` 的分工

- `write_file` 是**整份覆盖** —— 同一个路径再写一次，旧内容全没了。
- `edit_file` 是**局部替换**，必须给出 `old_string` 和 `new_string`，而且 `old_string` 在文件里要唯一。

这次改一句话用的就是 `edit_file`，返回值是 `Successfully replaced 1 instance(s)`。

### 4.5 断言比肉眼可靠

脚本最后做了一次断言：

```python
assert real.read_text(encoding="utf-8") == EDITED, "磁盘内容应为修改后的版本"
```

只有磁盘上的内容**逐字等于修改后的版本**，才能说明 `edit_file` 真的动了磁盘文件 —— 而不是只返回了一句成功提示。

### 4.6 两个意外收获

**① 工具的说明书可以打印出来。** `tool.args` 就是参数表，连约束都在里面 —— 不用翻文档，也不用猜。

**② 状态里有哪些键，要先打出来看。** 我原以为 `result` 里会有很多字段，实际上没挂 `TodoListMiddleware` 时就只有 `messages` 和 `files` 两个。

---

## 五、下一步修正

1. **这次用的是脚本模型。** 台词是写死的，所以只能证明机制跑通，**不能证明真实模型会自己选对工具**。想观察真实行为，得换成真实模型再跑一次。

2. **产物进了仓库。** `agent_workspace/report.md` 是脚本生成的，我把它一起提交当作证据。如果以后要反复跑、内容会变，应该改成写进临时目录，或者加进 `.gitignore`。

3. **没有对比 `write_file` 覆盖前后的差别。** 这次只调了 `edit_file`，没验证整份覆盖的效果。这属于 Advanced 档的内容，本次不做。

4. **继续读第 3 章正文的剩余部分** —— 文件系统怎么帮 Agent 管理上下文（大结果自动卸载、对话历史总结）。
