---
name: safe-shell
description: 沙箱内安全命令行：白名单、确认流程与常见场景
---

# 安全 Shell 操作

## 原则
- 仅在沙箱 `projects/` 目录内执行命令
- 优先 `python`/`pytest`/`npm run`/`git status` 等白名单前缀
- 删除类命令（rm/del）被策略永久禁止

## 常见安全场景
| 需求 | 推荐命令 |
|------|----------|
| 跑测试 | `pytest` 或 `python -m pytest` |
| 运行脚本 | `python script.py` |
| 看目录 | `dir`（Windows）或 `ls` |
| Git 状态 | `git status` |

## 需用户确认
`execute_command` 在「平衡/保守」档位下会弹确认，并附带风险说明。向用户解释命令用途后再请求确认。

## 磁盘空间
优先 `get_disk_usage`，不要用未白名单的 PowerShell/WMI 除非权限档位为「宽松」且用户已确认。
