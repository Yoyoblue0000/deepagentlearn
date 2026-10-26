# Task 5 学习打卡：把经验做成可复用的 Skill

**昵称：** 爱眨眼睛的×0

**群号：** 2群

**课程：** DeepAgents 实战 · 第 7 章

**学习时间：** 2026-10-26

**本次档次：** Lite 打卡级

群公告里那个问题 —— 想让 Agent 复用我写好的能力，有没有不用改代码、更轻的方式？
这一章给的答案是 **Skill**：一个目录 + 一份 `SKILL.md`。
启动时系统提示里只放 `name`、`description` 和文件路径；模型判断「这活儿归它管」，
才自己 `read_file` 去取正文。Agent 的装配代码里没有引用它 ——
`checkin-writer` 这个名字只出现在验证脚本的断言路径里。

Lite 的要求是「写出第一个最小 `SKILL.md`，并让它被成功匹配一次」。
我把 Task 2–4 里最有复用价值的那套东西打包了：**打卡文档的写法**。
从 Task 2 开始，每次打卡都要「验证什么 / 改了什么 / 实际结果 / 证据与解释 / 下一步修正」，
这套结构连着用了三遍 —— 正好是「经验」该被复用的样子。

练习过程中使用了 AI 教练的提问和提示；脚本、运行结果和结论由自己跑出来验证。

---

## 一、验证什么

四个问题：

1. 「最小」的 Skill 要几个文件？只写 `SKILL.md` 够不够用？
2. 请求里**不提 skill 名字**，Agent 靠什么认出它？`description` 到底够不够？
3. 是不是「宁可多读」？无关请求会不会也去读正文（对照组）？
4. 启动时到底多花了多少 token？正文是在第几次请求才进来的？

---

## 二、改了什么

新增 [`skills/checkin-writer/SKILL.md`](skills/checkin-writer/SKILL.md) ——
**一个文件，没有 `scripts/`、`references/`、`assets/`**。

结构是最小版：frontmatter 只有 `name` + `description`；正文三段——
输入 / 输出格式（五个标题照抄，不增不减）/ 写作规则 + 边界情况。

`description` 里塞了三个触发信号：打卡、checkin / CHECKIN.md、学习笔记打卡，
外加一句「按统一格式把这次记录写成一篇」。

挂载只多了一个参数：

```python
agent = create_deep_agent(
    model=ChatOpenAI(...),                 # 硅基流动 Qwen3-Coder-30B
    backend=FilesystemBackend(root_dir=str(ROOT), virtual_mode=True),
    skills=["/skills/"],                   # 给的是父目录，不是 SKILL.md
    system_prompt="用中文回答。需要读写文件时使用文件工具，不要凭空猜测文件内容。",
)
```

这里有个坑，教案写得很直白：`skills` 参数要的是**包含 Skill 子目录的父目录**，
写成 `SKILL.md` 的路径不符合扫描约定。顺手验了一下，它的表现是这样的：

```text
Cannot load skills from '/skills/checkin-writer/SKILL.md': Path '/skills/checkin-writer/SKILL.md': not_a_directory
Skills load errors: [...]

=== SKILL.md 路径: skills=['/skills/checkin-writer/SKILL.md']
    系统提示里真正加载了 Skill：False
    | (No skills available yet. You can create skills in /skills/checkin-writer/SKILL.md)

=== 父目录: skills=['/skills/']
    系统提示里真正加载了 Skill：True
    | - **checkin-writer**: 当用户要把一次课程实验……时使用。按五段固定结构输出：……
    | -> Read `/skills/checkin-writer/SKILL.md` for full instructions
```

**不抛异常**——只有 stderr 一条 warning，系统提示变成「(No skills available yet…)」。
所以写错路径不会崩，只是模型手上一个技能都没有；不主动去看系统提示，很难发现。

验证脚本 [`step08_skill_matching.py`](step08_skill_matching.py) 做了三处观察
（手法沿用 ch07 notebook）：

| 观察点 | 做法 | 能看到什么 |
| --- | --- | --- |
| 每次真正发给模型的请求 | `BaseCallbackHandler.on_chat_model_start` 抄下来 | 元数据、正文分别在第几次请求出现 |
| 工具是否真的执行了 | 按 `tool_call_id` 把 `AIMessage.tool_calls` 与 `ToolMessage` 配对 | `read_file` 读的是哪个路径、`status` 是什么 |
| 正文是「被读到」还是「被执行了」 | 断言产物里有那五个标题、且顺序正确 | 标题只在正文里出现过，产品里有它就说明照着做了 |

请求本身刻意**不写 skill 名字**，全靠 description 命中：

```text
帮我把今天 Task5 的实验整理成一份打卡草稿，用 write_file 写到 /out/task05-checkin-draft.md。
材料（都是我这次真跑出来的）：……
按我们组统一的要求写，别自己发明结构。
```

对照组是一句跟打卡毫无关系的话：

```text
3 的平方加 4 的平方等于几？只回答一个数字，不要用工具。
```

---

## 三、实际结果

### 3.1 正向请求：靠 description 命中

```text
【正向请求】用户请求：帮我把今天 Task5 的实验整理成一份打卡草稿，用 write_file 写到…

  工具调用（3 次）：
    ls({'path': '/skills/checkin-writer'}) → success
    read_file({'file_path': '/skills/checkin-writer/SKILL.md'}) → success
    write_file({'file_path': '/out/task05-checkin-draft.md', ...}) → success

  模型请求（4 次），每次都看它手里有什么：
    第 1 次：仅目录（含 name/description/路径）
    第 2 次：仅目录（含 name/description/路径）
    第 3 次：目录 + 正文
    第 4 次：目录 + 正文
```

注意第 2 次请求仍然是「仅目录」：那一次是 `ls` 的返回，返回里没有正文，
所以正文没有被顺带带进来。正文是第 3 次请求才出现的，也就是 `read_file` 之后。

### 3.2 启动时到底多了什么

```text
【启动开销：元数据 vs 正文】
  第 1 次请求里和这个 Skill 有关的行：2 行 / 205 字符
    - **checkin-writer**: 当用户要把一次课程实验、练习或排障过程整理成打卡文档（checkin /
      CHECKIN.md / 学习笔记打卡），或要求「按统一格式把这次记录写成一篇」时使用。按五段固定结构
      输出：验证什么、改了什么、实际结果、证据与解释、下一步修正。
      -> Read `/skills/checkin-writer/SKILL.md` for full instructions
  SKILL.md 全文：770 字符 ← 这些只在读取后才花掉
```

启动成本是 **205 字符的说明 + 一行路径**，不是 770 字符的正文。
按这个比例，20 个 Skill 启动时也就多四千字符左右 —— 线性增长，不碰上下文窗口。

### 3.3 对照组：无关请求不读

```text
【对照组】用户请求：3 的平方加 4 的平方等于几？只回答一个数字，不要用工具。

  工具调用：无
  read_file 路径：无
  判定：没读 → 是「匹配」而不是「每次都读」
```

这一组是这次打卡里我最想留的证据：它排除了「反正每次都把 Skill 读一遍」这个解释。

### 3.4 产物：五段结构确实照着做了

脚本断言了产物里五个标题都出现、且顺序正确。节选第三段（下面 3.5 会说到它的问题）：

```markdown
三、实际结果
模型成功读取了 /skills/checkin-writer/SKILL.md 文件，并按照其定义的五段式结构生成了打卡草稿。草稿内容包括：
- 一、验证什么：描述了本次实验要验证的内容。
- 二、改了什么：说明了对技能文件的修改。
……
```

### 3.5 一个没做到的地方，如实记下

```text
  第三段是否贴了原始输出：否（还是概括性描述）
  第三段是否标了「未提供原始输出」：否
```

我把正文改了两轮想让它改掉这个毛病（见 4.5），产物没变。
所以结论是：**结构类规则它照做了，内容类规则它没照住。**

### 3.6 断言全部通过

```text
【断言通过·正向】
  1. 第一次请求：系统提示里有 checkin-writer 的 name / description / 路径，没有正文
  2. 模型自己发起 read_file 读 SKILL.md，且读取成功
  3. 正文只在这次读取之后才进入请求
  4. 产物 /out/task05-checkin-draft.md 含五个标题且顺序正确 → 正文被执行了，不只是被读到

【SKILL.md 未被改动】hash 前后一致
```

---

## 四、证据与解释

### 4.1 匹配看的是 description，不是文件名

请求里一次都没提 `checkin-writer`，模型自己 `ls` 了 `/skills/checkin-writer` 目录、
再读 `SKILL.md` ——说明它是顺着系统提示里那两行「名字 + 用途 + 路径」找过去的。

`description` 里那几个触发信号和请求里的说法是对得上的：请求说「打卡草稿」「按我们组统一的要求写」，
描述里是「打卡文档 / checkin / 按统一格式把这次记录写成一篇」。这就是匹配发生的全部依据。

### 4.2 元数据给的是「目录」，不是「简介」

系统提示里那两行告诉模型的是：有这个能力、它管什么事、去哪个文件看细节。
它不知道具体怎么做 ——「先读哪个文件、五段标题是什么」都在正文里。

所以 `skills` 这套机制省的不只是 token，更是**判断成本**：
Skill 从 5 个涨到 50 个，模型要读的依然只是 50 行说明。
这也解释了为什么 `description` 是最重要的字段：它是模型唯一能看见的东西。

### 4.3 `ls` 不算「读到」

第 2 次请求还是「仅目录」，因为 `ls` 的返回里只有文件名，没有正文。
正文要等 `read_file` 的 `ToolMessage` 回到上下文才出现。

这跟 Task 2 的「文件在状态里 ≠ 正文在上下文里」是同一条规矩：
**工具返回才是内容进入上下文的唯一通道**。我一开始以为 `ls` 会把内容带进来，日志直接否掉了。

### 4.4 匹配成功 ≠ 正文执行到位

标题它照抄了（结构），但「第三段逐条贴实际输出」它写成了概括、
「材料只有概括时标出来」它也没标（内容）。三次运行结果一致，不是偶发。

更值得记的是：每次的最终答复都自称「严格遵循了五段式结构」。
**Agent 的自述和产物是两回事** —— 这和 Task 3 的「`completed` 不等于做对了」是同一条：
要证据，不要自述。所以我把断言写在产物上，不写在这句话上。

### 4.5 两次改正文为什么没效果

| 版本 | 正文改了什么 | 产物第三段 |
| --- | --- | --- |
| v1 | 「第三段只放实际输出；没跑过的不写」 | 概括性描述 |
| v2 | 改成「逐条贴实际输出，可以截断，但不能改写成评价」 | 还是概括 |
| v3 | 加边界情况「材料只有概括时，第三段开头写『以下为概括，未提供原始输出』」 | 仍没标 |

三次运行都命中了 Skill、都读到了当时的正文（每次跑到第 3 个模型请求时，正文都已经在上下文里），
但新加的规则一条都没在产物里落地。

能确定的原因只有一个：**材料里根本没给原始输出行**，模型手上没有可贴的东西，只能概括。
这也暴露了正文的一个漏洞：我写了「没跑过的不写」，却没写「材料只有概括时该怎么处理」，
直到 v3 才补 —— 而补完模型也没执行。

所以「把规则写得更严」不是万能解。更可能有效的是给个**样子**（模板或示例），
这属于 Basic 要试的方向，记在第五节。

### 4.6 一个文本文件就够了

从 v1 到 v3，我改的都是 `SKILL.md` 这一个文本文件 —— Agent 的装配代码一个字符没动
（只改过验证脚本打印什么），下一次运行读到的就是新版本：因为正文是运行时从磁盘读的，不是编译进代码的。

这正是群公告说的「不用改代码、更轻的方式」：**能力复用变成了改文档**。
代价是文档的行为不像代码那样确定 —— 4.5 就是代价的样本：同一份正文，说改严了，产物没跟着变。

### 4.7 为什么「最小」能成立

Lite 只写了一个 `SKILL.md`，就完成了匹配、读取、产出这三步。
`scripts/`、`references/`、`assets/` 都是可选的 —— 只有当正文「说不完」的时候才需要。

反过来看 4.5：结构能靠正文说清，内容约束不住。
**需要给例子的事情，正文说不完，那就该上 `assets/` 了。** 这也是「最小」的边界。

---

## 五、下一步修正

1. **内容类规则要用模板兜底，不能只写散文。**
   加 `assets/checkin-template.md`，让正文说「按模板第三段的样子写」，
   而不是「逐条贴实际输出」。这是 Basic 的第一件事，也是 4.5 的直接修正。

2. **description 只测了「命中」，没测「漏用 / 误用」。**
   现在这条描述很长（三个触发词）。收窄它会不会漏掉「整理一下今天的实验」这种说法？
   加宽它会不会把「写周报」也吸进来？改一个变量跑同一批请求才算数（Advanced）。

3. **对照组只有一条，样本太小。**
   应该准备一组**不该命中**的请求（写代码审查、翻译、算数、写周报），
   统计误用率；再准备一组**该命中但说法不同**的请求（「这周的记录整理一下」），统计漏用率。

4. **没区分「输入带原始输出」和「输入只有概括」。**
   4.5 的结论被这一条卡住了：材料里没有一行原始输出，我无法判断是 skill 的锅还是输入的锅。
   下次要拿同一份 Skill，换两种输入各跑一次（单变量），才能说清。

5. **只用了 `FilesystemBackend`，没试另外两种注入方式。**
   `StateBackend` 走 `files` 参数、`StoreBackend` 走 `store.put`，
   以及「自定义子 Agent 不继承主 Agent 的 Skills」这条规则，这次都没验证。

6. **只有一个 Skill，没有选择压力。**
   一个 Skill 时命中是必然的。放两个功能相近的 Skill（比如「打卡文档」和「技术笔记」），
   才看得出 `description` 有没有区分度 —— 这也是误匹配最容易发生的地方。

---

## 运行方式

在 `deepagents-practice` 目录下运行（**需要真实模型**，读 `../my_deepagent/.env` 的 `BUB_*`）：

```powershell
cd deepagents-practice
.\.venv\Scripts\python.exe -X utf8 task05-skills\step08_skill_matching.py
```

一次运行 = 2 次对话（正向 + 对照），约 5 次模型请求。
日志：[`runs/run02-v2-skill.txt`](runs/run02-v2-skill.txt)、[`runs/run03-v3-skill.txt`](runs/run03-v3-skill.txt)。
第 1 次（v1 正文）的日志没有落盘，上文摘录的是当时终端里的原文。

本次环境：Windows / Python 3.12 / deepagents 0.7.22 / langchain 1.4.3 /
硅基流动 `Qwen/Qwen3-Coder-30B-A3B-Instruct`（temperature=0）。

---

## 引用资料

- 《Deep Agents 实战》第 7 章「Skills — 可复用的 Agent 能力包」：
  <https://datawhalechina.github.io/deepagents-in-action/>
- 课程仓库（含本章正文与 Notebook）：
  <https://github.com/datawhalechina/deepagents-in-action>
- 第 7 章配套实验 Notebook（请求录制、披露顺序核对的手法）：
  <https://github.com/datawhalechina/deepagents-in-action/blob/main/notebooks/ch07/01-skills-progressive-disclosure.ipynb>
- Agent Skills 规范（`SKILL.md` 的字段定义，本章引用的开放标准）：
  <https://agentskills.io/specification>
