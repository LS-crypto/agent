# 前端部署 — Cloudflare Pages

## 架构

| 项 | 值 |
|----|-----|
| 构建产物 | `frontend/dist/` |
| 平台 | [Cloudflare Pages](https://pages.cloudflare.com/) |
| API | 通过 `VITE_API_BASE` 指向线上后端（**不要**把 `DASHSCOPE_API_KEY` 放进前端） |

## 1. 环境变量

在 Cloudflare Pages → Settings → Environment variables（Production）：

| 变量 | 示例 |
|------|------|
| `VITE_API_BASE` | `https://api.yourdomain.com/api` |

本地生产预览：

```powershell
cd frontend
copy .env.production.example .env.production
# 编辑 VITE_API_BASE
npm run build
npm run preview
```

开发环境仍用 `vite.config.ts` 的 proxy，无需 `VITE_API_BASE`。

## 2. 构建

```powershell
cd frontend
npm install
npm run build
```

输出在 `frontend/dist/`。已包含 `public/_redirects`（SPA 刷新不 404）。

## 3. Cloudflare Pages 配置

### 方式 A：连接 Git

1. Cloudflare Dashboard → Workers & Pages → Create → Connect to Git
2. 选择仓库与分支
3. 构建设置：

| 项 | 值 |
|----|-----|
| Framework preset | None |
| Build command | `cd frontend && npm install && npm run build` |
| Build output directory | `frontend/dist` |
| Root directory | `/`（仓库根） |

4. Environment variables：`VITE_API_BASE` = 你的后端 URL + `/api`

### 方式 B：Wrangler 手动上传

```powershell
cd frontend
npm run build
npx wrangler pages deploy dist --project-name=qwen-agent
```

## 4. 自定义域名

1. Pages 项目 → Custom domains → 添加 `app.yourdomain.com`
2. 按提示在 Cloudflare DNS 添加 CNAME
3. 后端 `CORS_ORIGINS` 必须包含该 HTTPS 域名（见 [deploy-backend.md](./deploy-backend.md)）

## 5. 验收

- [ ] `https://<pages-url>` 可打开 UI
- [ ] 无后端时显示「后端未连接」横幅
- [ ] 配置 `VITE_API_BASE` 后 health 通过，可创建会话、聊天
- [ ] `write_file` 触发确认弹窗，允许/拒绝正常
- [ ] 刷新页面 SPA 不 404

## 6. 安全提醒（上线前必读）

- **未做 S3 登录前不要公开推广** — 固定 `user_id=default`，任何人可访问你的 Agent
- API Key **仅在后端**环境变量，never 提交到 Git 或 Pages
- 建议：Cloudflare Access、IP 限制、或仅自用域名
- 后端 CORS 不要用 `*`，只填你的 Pages 域名

## 7. SSE 注意

- 前端直连后端域名（`VITE_API_BASE`），不经过 Pages 代理 SSE
- 若后端也套 Cloudflare 橙云代理，确保不缓冲流式响应；推荐 API 子域名 `api.xxx.com` 直连 origin（Railway/Fly）
