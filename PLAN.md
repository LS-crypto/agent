# Sheldon Agent 项目规划

> 开发进度：[开发日志.md](../开发日志.md) · 待办：[任务清单.md](../任务清单.md)

**最后更新：** 2026-07-03

## 技术栈

| 层 | 选型 |
|----|------|
| 包管理 | **uv**（`pyproject.toml` + `uv.lock`） |
| 大模型 | 百炼 Qwen（默认 **qwen3.7-plus**） |
| 核心 | Python 3.11 · `core/` |
| CLI | `apps/cli/` |
| Web 后端 | FastAPI · `server/` |
| Web 前端 | React + Vite · `apps/web/` |
| 测试 | pytest · `tests/`（与业务分离） |
| 部署 | Docker · `deploy/` → 阿里云 ECS |

## 目录结构

```
sheldon-agent/
├── apps/           # 应用入口（CLI · Web 前端）
├── core/           # 共享核心（agent · tools · skills · user）
├── server/         # Web API 服务
├── tests/          # 测试
├── deploy/         # Docker
├── docs/           # 文档
├── scripts/        # 开发脚本
├── examples/       # 示例
└── runtime/        # 运行数据（不入库）
```

## 端规划

| 端 | 目录 | 状态 |
|----|------|------|
| 命令行 | `apps/cli` | ✅ |
| Web | `apps/web` + `server` | ✅ |
| 桌面 | 待定 | 见任务清单 |
| 小程序 | 待定 | 见任务清单 |

## 阶段清单

| 阶段 | 状态 |
|------|------|
| 0–E 功能开发 | ✅ |
| 工程重组 + uv | ✅ |
| 本地联调 / ECS 部署 | ⬜ 见任务清单 |
