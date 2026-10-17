# Task 2：让成果留在文件里（虚拟文件系统）

**第 3 章 · 3 天** —— Deep Agents 的 Context Engineering 核心。

第 1–2 章解决了「Agent 能调用工具」，这一章解决「成果留在哪」。
虚拟文件系统 = **7 个文件工具**（能做什么）+ **Backend**（存到哪）+ **路径**（怎么找）。

## 目标档次

| 档次 | 要求 |
| --- | --- |
| Lite | 让 Agent 完成一次「写入 — 读回 — 修改」，再亲手在项目目录里找到那份产物 |
| Basic | 沿用主模板的文件后端保存、读回、修改资料与报告，讲清文件路径和 Backend 之间的关系 |
| Advanced | 挑两种 Backend 做对比（如 State 与 Filesystem 的生命周期差异），或验证文件覆盖前后的差别，留下可复现记录 |
| 学有余力 | 再加一种后端（Store 或沙箱）做三角对比 |

## 打卡

**Lite 打卡级** → [`CHECKIN.md`](CHECKIN.md)

本次只做 Lite，Basic / Advanced / 学有余力 未做。

## 本次用到的脚本

| 脚本 | 做什么 | 后端 |
| --- | --- | --- |
| [`step04_vfs.py`](step04_vfs.py) | 写一个文件，从 Agent 状态里读回来 —— 磁盘上找不到 | 默认 `StateBackend` |
| [`step05_filesystem.py`](step05_filesystem.py) | 写入 → 读回 → 修改，产物落到项目目录 | `FilesystemBackend` |

两个脚本只差一行 `backend=...`。

产物：[`agent_workspace/report.md`](agent_workspace/report.md)（脚本生成的真文件，作为证据提交）
