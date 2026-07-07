# user 目录说明

用户 Agent 系统的**源码与配置**；运行/测试生成的文件在 `runtime/`（不入库）。

## 结构

```
user/
└── admin/
    └── view_activity.py    # 大总管查看脚本（源码）

runtime/                    # ← 运行生成，见 runtime/.gitkeep
├── workspaces/{user_id}/projects/   # 用户沙箱
├── workspaces/{user_id}/sessions/   # 会话（规划）
├── logs/YYYY-MM-DD/{user_id}.jsonl  # 活动日志
└── admin/activity_summary.json      # 大总管汇总
```

## 大总管查看活动

```powershell
python user/admin/view_activity.py
python user/admin/view_activity.py -u default --summary
```

## 日志与安全

- 详细过程（工具调用、Loop 轮次、完整 tool 返回值）写入 `runtime/logs/`
- CLI 默认终端只显示 You> / Agent>，查过程用 `view_activity.py`
- 工具层不得读写 `runtime/logs/`、`runtime/admin/`
- 每个用户仅能访问 `runtime/workspaces/{user_id}/`
- API Key 不得写入 runtime 或 user 目录
