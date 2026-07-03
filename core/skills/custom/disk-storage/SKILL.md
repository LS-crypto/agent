---
name: disk-storage
description: 磁盘与工作区存储分析：安全地使用 get_disk_usage / get_workspace_stats
---

# 磁盘存储分析

## 何时使用
用户询问「磁盘满了」「空间不够」「项目多大」时使用。

## 推荐流程
1. 调用 `get_disk_usage` 查看沙箱所在磁盘总量与剩余
2. 调用 `get_workspace_stats` 统计项目内文件数与占用
3. 若需找大文件，用 `glob_search` + `read_file` 或 `list_dir` 逐层排查

## 禁止
- 不要用 `execute_command` 跑 `format`、`rm -rf`、删除系统盘命令
- 磁盘信息优先用内置工具，避免 Shell
