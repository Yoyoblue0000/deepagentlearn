# Task 5：把经验做成可复用的 Skill

**第 7 章 · 3 天** —— 从这一章开始，Agent 学会「复用别人写好的能力」。

前四个 Task 解决的是：能调工具、成果能落地、任务能按计划推进、能委派。
这一章解决另一个问题：**我把这套经验写下来，Agent 怎么才能用上？**

答案是 Skill：一个目录 + 一份 `SKILL.md`。启动时只有 `name` / `description` / 路径
进系统提示，模型觉得这活儿归它管，才自己 `read_file` 去取正文——
Agent 的装配代码里没有一个字提到这个能力。

## 目标档次

| 档次 | 要求 |
| --- | --- |
| Lite | 写出第一个最小 `SKILL.md`，并让它被成功匹配一次；写清验证什么、改了什么、实际结果、证据与解释、下一步修正 |
| Basic | 在主项目的 skills 目录里改造或新增一种内容流程，交出 SKILL.md、匹配请求、正文读取记录和实际产物 |
| Advanced | 比一比 description 或输入变化带来的漏用 / 误用（单变量），说清为什么 |
| 学有余力 | 写一个能跨 Task 复用的 Skill，拿到 Skills 集市分享 |

## 打卡

**Lite 打卡级** → [`CHECKIN.md`](CHECKIN.md)

本次只做 Lite，Basic / Advanced / 学有余力 未做。

## 本次用到的文件

| 文件 | 做什么 |
| --- | --- |
| [`skills/checkin-writer/SKILL.md`](skills/checkin-writer/SKILL.md) | 本次的 Skill：把一次实验记录整理成五段式打卡文档 |
| [`step08_skill_matching.py`](step08_skill_matching.py) | 用真实模型验证「匹配」：正向请求 + 无关请求对照，记录每次模型请求与工具调用 |
| [`out/task05-checkin-draft.md`](out/task05-checkin-draft.md) | 脚本跑出来的产物（由 Agent 按 Skill 正文写成） |
| [`runs/`](runs/) | 第 2、3 次运行的完整终端日志 |

这个 Task 和前面几个不一样：**需要真实模型**（读 `../my_deepagent/.env` 的 `BUB_*`）。
脚本模型只能证明「机制跑通了」，证明不了「description 能不能命中」——
教案自己也写了，脚本模型按公开规则发读取请求，它没有判断「该不该用这个 Skill」的能力。
