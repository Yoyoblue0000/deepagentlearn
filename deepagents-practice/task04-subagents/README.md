# Task 4：把一项工作交给子 Agent（子 Agent 与上下文隔离）

**第 5 章 · 3 天** —— 从这一章开始，Agent 学会「委派」。

前三个 Task 解决的分别是：能调工具、成果能落地、任务能按计划推进。
这一章解决另一个问题：**主 Agent 的上下文装不下所有中间过程，怎么办？**

答案是 Context Quarantine（上下文隔离）：把整块工作交给子 Agent，
中间的工具调用留在它自己的上下文里，主 Agent 只收到一句结论。

## 目标档次

| 档次 | 要求 |
| --- | --- |
| Lite | 造一个职责明确的子 Agent，让它被主 Agent 真正调用一次；写清验证什么、改了什么、实际结果、证据与解释、下一步修正 |
| Basic | 改子 Agent 的职责、提示词或工具映射，留下 task 回传、主子消息边界和报告文件读取的证据 |
| Advanced | 再加一个角色（或改好回传内容），用同一个任务说清收益和额外成本 |
| 学有余力 | 用 `CompiledSubAgent` 把自己的工作流接进来 |

## 打卡

**Lite 打卡级** → [`CHECKIN.md`](CHECKIN.md)

本次只做 Lite，Basic / Advanced / 学有余力 未做。

## 本次用到的脚本

| 脚本 | 做什么 |
| --- | --- |
| [`step07_subagent_delegation.py`](step07_subagent_delegation.py) | 声明 `researcher` 子 Agent，主 Agent 通过 `task` 委派；分别检查消息边界、文件边界和工具集边界 |

脚本使用台词写死的脚本模型，不需要 API Key。它验证的是**委派机制与数据边界**，
不证明真实模型会主动委派。
