# GitHub 推送指南

国内网络环境下 HTTPS 直连 GitHub 经常超时，改用 SSH 协议可稳定推送。以下为完整流程。

## 前置检查

```bash
# 1. 确认远程地址
git remote -v

# 2. 确认有本地提交
git log --oneline -5

# 3. 测试 SSH 连通性（不需要密钥也能测 TCP 是否通）
ssh -o ConnectTimeout=10 -T git@github.com
# 返回 "Permission denied (publickey)" = 端口通，只是缺密钥
# 返回 "Connection timed out"     = 端口也不通，需要代理
```

## 步骤一：生成 SSH 密钥（仅首次）

```bash
# 生成 ED25519 密钥
ssh-keygen -t ed25519 -C "你的邮箱或标识" -f ~/.ssh/id_ed25519 -N ""

# 查看公钥
cat ~/.ssh/id_ed25519.pub
```

将公钥添加到 GitHub：https://github.com/settings/keys → New SSH Key

## 步骤二：添加 GitHub Host Key（仅首次）

```bash
ssh-keyscan -t rsa github.com >> ~/.ssh/known_hosts
```

## 步骤三：验证 SSH 认证

```bash
ssh -T git@github.com
# 成功会显示: Hi <用户名>! You've successfully authenticated...
```

## 步骤四：切换到 SSH 远程地址

```bash
git remote set-url origin git@github.com:<用户名>/<仓库名>.git
```

## 步骤五：处理历史冲突（如有）

如果本地和远程是两条独立历史（`git merge-base` 返回空）：

```bash
# 检查是否有共同祖先
git merge-base main origin/main

# 无共同祖先时，拉取合并
git pull origin main --allow-unrelated-histories --no-edit
```

## 步骤六：推送

```bash
git push -u origin main
```

## 步骤七：克隆验证（推荐）

推送后在空目录验证他人能否正常使用：

```bash
git clone --recurse-submodules git@github.com:<用户名>/<仓库名>.git
cd <仓库名>
git submodule update --init --recursive   # 若上一步未加 --recurse-submodules
uv sync --dev
uv run pytest tests/ -q --ignore=tests/test_docker_health.py
```

## 常见问题

| 现象 | 原因 | 解决 |
|------|------|------|
| HTTPS push 超时 | 443 端口被墙 | 切换 SSH |
| `Permission denied (publickey)` | 未配置密钥或未添加到 GitHub | 执行步骤一 |
| `Host key verification failed` | known_hosts 缺少 GitHub | 执行步骤二 |
| `rejected: fetch first` | 远程有新提交 | 先 `git pull` |
| `fatal: refusing to merge unrelated histories` | 历史独立 | 加 `--allow-unrelated-histories` |
