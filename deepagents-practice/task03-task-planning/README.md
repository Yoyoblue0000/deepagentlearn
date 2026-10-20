# Task 3：让项目按计划完成（任务规划与 Todo）

**第 4 章 · 3 天** —— 从这一章开始，Agent 有了「规划能力」。

第 2 章让 Agent 会调工具，第 3 章让成果留在文件里，这一章解决：
**复杂任务做到一半，Agent 怎么知道下一步该干嘛？**

答案不是一个更大的提示词，而是一份单独存起来的任务清单：
`write_todos` + Agent State 里的 `todos` 字段。

## 目标档次

| 档次 | 要求 |
| --- | --- |
| Lite | 让 Agent 用 `write_todos` 列一次计划，亲眼看它从 `pending` 走到 `completed` |
| Basic | 显式启用 `TodoListMiddleware`，给固定资料完成多步骤任务，最后逐项核对报告；计划全部 completed 不等于验收通过 |
| Advanced | 固定输入与模型，对比 Todo 开 / 关两轮的完成情况或调用轨迹；能解释结果没改善的原因也算完成 |
| 学有余力 | 加入 `SummarizationMiddleware`，观察上下文压缩与任务清单怎么配合 |

## 打卡

**Lite 打卡级** → [`CHECKIN.md`](CHECKIN.md)

本次只做 Lite，Basic / Advanced / 学有余力 未做。

## 本次用到的脚本

| 脚本 | 做什么 |
| --- | --- |
| [`step06_todo_plan.py`](step06_todo_plan.py) | 显式挂 `TodoListMiddleware`，让 Agent 制定 3 步计划，并随真实工具调用把状态从 pending 推到 completed |

脚本使用台词写死的假模型，不需要 API Key。它验证的是**框架机制**，不是真实模型的规划能力。
