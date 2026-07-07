# Qwen Agent Web 前端

阶段 C：Cursor 风格三栏聊天界面（MVP + C-2 polish），对接 FastAPI + SSE 后端。

## 前置

后端需先启动：

```powershell
cd D:\system\TEST\qwen-agent
python -m backend
```

## 安装与开发

```powershell
cd D:\system\TEST\qwen-agent\frontend
npm install
npm run dev
```

浏览器打开 Vite 提示的地址（默认 `http://127.0.0.1:5173`）。

`vite.config.ts` 已将 `/api`、`/health` 代理到 `http://127.0.0.1:8765`。

## 功能

- 左侧：会话列表（新建 / 切换 / 删除 / **双击重命名**）
- 中间：聊天 + SSE 流式回复；顶栏 **「清空对话」**（confirm 后 reset）
- 右侧：Agent 活动时间线（可折叠）；`loop_round` / `tool_call` / `tool_result`
- Assistant 消息内 ` ``` ` 代码块基础样式
- ≤768px：汉堡菜单展开/收起侧栏
- **工具确认（S1）：** review 级工具弹出 ConfirmDialog → POST `/api/chat/confirm`

固定 `user_id=default`，配置见 `src/types.ts`。

## 构建

```powershell
npm run build
npm run preview
```

生产环境变量见 `.env.production.example`；Cloudflare Pages 步骤见 [docs/deploy-frontend.md](../docs/deploy-frontend.md)。
