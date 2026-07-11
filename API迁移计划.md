# API 迁移计划：百炼 → DeepSeek

> 百炼免费额度即将过期，确认切换到 **DeepSeek 官方 API**。

## 现状分析

当前系统通过 **阿里云百炼（DashScope）** 提供 LLM 能力，核心集成点：

| 层级 | 文件 | 职责 |
|------|------|------|
| **配置层** | `core/config.py` | `BAILIAN_BASE_URL`、`create_client()`、`MODEL_TIERS` |
| **模型目录** | `core/models/catalog.py` | 所有模型 ID（qwen/deepseek/glm 共 18 个） |
| **模型画像** | `core/models/profiles.py` | 每个模型的调参和行为配置（20+ 条） |
| **多模态** | `core/agent/multimodal.py` | `DEFAULT_VISION_MODEL = "qwen3-vl-flash"` |
| **密钥服务** | `server/services/api_key_service.py` | 管理员读环境变量、用户 BYOK |
| **密钥存储** | `server/repositories/user_secrets.py` | `PROVIDER_DASHSCOPE` 常量 |
| **模型策略** | `server/services/model_policy.py` | 按角色过滤可用模型 |
| **前端默认值** | `apps/web/src/App.tsx` | 硬编码 `"qwen3.6-flash"` 作为 fallback |
| **前端模型列表** | `ChatPanel.tsx` | 从 `/models` API 获取，按 group 分组展示 |
| **环境变量** | `.env.example` | `DASHSCOPE_API_KEY` |

**好消息**：系统已使用 `openai` SDK + `base_url` 模式，DeepSeek 也是 OpenAI 兼容接口，核心 Agent 逻辑零改动。

---

## DeepSeek API 概况

| 项目 | 值 |
|------|-----|
| Base URL | `https://api.deepseek.com/v1` |
| 兼容格式 | OpenAI Chat Completions（`/v1/chat/completions`） |
| SDK | `openai` Python SDK 直接可用 |
| 定价 | deepseek-chat: ¥1/M input, ¥2/M output（缓存命中 ¥0.1） |
| | deepseek-reasoner: ¥4/M input, ¥16/M output |
| 控制台 | https://platform.deepseek.com |

### DeepSeek 可用模型

| 模型 ID | 说明 | 能力 |
|---------|------|------|
| `deepseek-chat` | DeepSeek-V3（通用对话） | Function Calling ✅、视觉 ❌ |
| `deepseek-reasoner` | DeepSeek-R1（深度推理） | 思考链输出、Function Calling ✅、视觉 ❌ |

> **关键限制**：DeepSeek **没有视觉模型**，发图功能需要额外方案（见 Task 5）。

---

## 迁移步骤

### Task 1：配置层 — `core/config.py`

**改动**：base_url、模型 tiers、环境变量名。

```python
# 改前
BAILIAN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_TIERS = {
    "flash": ModelConfig("qwen3.6-flash", ...),
    "plus":  ModelConfig("qwen3.7-plus", ...),
    "max":   ModelConfig("qwen-max", ...),
}

# 改后
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
MODEL_TIERS = {
    "chat":      ModelConfig("deepseek-chat", max_tokens=8192,
                             cost_input_per_1k=0.001, cost_output_per_1k=0.002),
    "reasoner":  ModelConfig("deepseek-reasoner", max_tokens=8192,
                             cost_input_per_1k=0.004, cost_output_per_1k=0.016),
}
DEFAULT_TIER = os.getenv("DEFAULT_MODEL_TIER", "chat")
```

`create_client()` 只需改环境变量名：

```python
def create_client(api_key: str | None = None) -> OpenAI:
    key = api_key or os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise ValueError("请设置环境变量 DEEPSEEK_API_KEY")
    return OpenAI(api_key=key, base_url=DEEPSEEK_BASE_URL)
```

### Task 2：模型目录 — `core/models/catalog.py`

**改动**：替换整个模型目录为 DeepSeek 模型。

```python
# 改前：18 个模型（qwen/deepseek/glm 混合）
DEFAULT_USER_MODEL_IDS = ("qwen3.6-flash", "qwen3.7-plus", ...)

# 改后：2 个模型
DEFAULT_USER_MODEL_IDS = (
    "deepseek-chat",
    "deepseek-reasoner",
)

AGENT_MODEL_CATALOG = (
    AgentModelEntry(
        id="deepseek-chat",
        label="DeepSeek V3",
        group="通用",
        tier="chat",
        max_tokens=8192,
        description="通用对话与编程，高性价比",
        supports_tools=True,
        supports_vision=False,
        is_default=True,
    ),
    AgentModelEntry(
        id="deepseek-reasoner",
        label="DeepSeek R1",
        group="推理",
        tier="reasoner",
        max_tokens=8192,
        description="深度推理，带思考链输出",
        supports_tools=True,
        supports_vision=False,
    ),
)
```

**前端影响**：
- 模型下拉从 18 个变 2 个，分组从「极速/主力/代码/旗舰/第三方/视觉」→「通用/推理」
- `AUTO_MODEL_ID` 可保留，auto 时默认走 `deepseek-chat`
- 前端 `App.tsx` 中 `"qwen3.6-flash"` fallback 改为 `"deepseek-chat"`

### Task 3：模型画像 — `core/models/profiles.py`

**改动**：替换为 DeepSeek 画像配置。

```python
_PROFILES = {
    "auto-default": ModelProfile(
        tagline="智能路由",
        features=("通用对话", "深度推理", "工具协作"),
        extra_prompt="简单问题用 chat 快速回答；复杂推理切 reasoner。",
    ),
    "chat-default": ModelProfile(
        tagline="通用编程",
        features=("代码生成", "文件读写", "快速响应"),
        skills=("karpathy-guidelines",),
        prefer_tools=("read_file", "edit_file", "execute_command", "grep"),
        extra_prompt="平衡质量与效率：改代码后尽量验证。",
    ),
    "reasoner-default": ModelProfile(
        tagline="深度推理",
        features=("多步规划", "复杂重构", "思考链可视化"),
        skills=("karpathy-guidelines", "code-review"),
        max_iterations=22,
        temperature=0.3,
        sequential_thinking=True,
        prefer_tools=("read_file", "edit_file", "execute_command", "grep"),
        extra_prompt="像 Staff Engineer：先理解需求与约束，再改代码并跑测试。",
    ),
}

_MODEL_KEYS = {
    AUTO_MODEL_ID: "auto-default",
    "deepseek-chat": "chat-default",
    "deepseek-reasoner": "reasoner-default",
}
```

### Task 4：密钥服务 — 改 provider 名

**4.1 `server/repositories/user_secrets.py`**

```python
# 改前
PROVIDER_DASHSCOPE = "dashscope"

# 改后
PROVIDER_DEEPSEEK = "deepseek"
# 保留向后兼容
PROVIDER_DASHSCOPE = "dashscope"  # 历史数据迁移用
```

**4.2 `server/services/api_key_service.py`**

```python
# 改前
platform = os.getenv("DASHSCOPE_API_KEY", "").strip()
return self._secrets.get_plaintext(user.id, PROVIDER_DASHSCOPE)

# 改后
platform = os.getenv("DEEPSEEK_API_KEY", "").strip()
return self._secrets.get_plaintext(user.id, PROVIDER_DEEPSEEK)
```

> **注意**：已有用户的 BYOK 数据（dashscope provider）需要迁移或提示重新配置。

### Task 5：多模态处理 — `core/agent/multimodal.py`

**DeepSeek 无视觉模型**，发图功能需要降级方案：

**方案 A（推荐）**：发图时友好提示

```python
def resolve_vision_model(model_id: str) -> str:
    raise ChatImageError("当前 API Provider 不支持图片理解，请移除图片后重试。")
```

**方案 B**：混合 Provider — 对话走 DeepSeek，视觉走百炼

```python
# 视觉请求转发到百炼（需同时配两个 Key）
VISION_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
VISION_API_KEY = os.getenv("VISION_API_KEY")  # 百炼 Key 单独配
```

> 方案 B 复杂度高，建议先用方案 A，后续有需要再加。

### Task 6：环境变量 — `.env.example`

```bash
# 改前
DASHSCOPE_API_KEY=sk-你的百炼密钥

# 改后
DEEPSEEK_API_KEY=sk-你的DeepSeek密钥

# 可选：视觉回退（方案 B）
# VISION_API_KEY=sk-百炼密钥（用于图片理解）
# DEFAULT_VISION_MODEL=qwen3-vl-flash
```

### Task 7：前端硬编码清理 — `apps/web/src/App.tsx`

```typescript
// 改前
modelId = defaultModel ?? "qwen3.6-flash";
? (models[0]?.id ?? "qwen3.6-flash")

// 改后
modelId = defaultModel ?? "deepseek-chat";
? (models[0]?.id ?? "deepseek-chat")
```

### Task 8：其他引用清理

| 文件 | 改动 |
|------|------|
| `server/routes/models.py` | `check_remote` 描述 "百炼 API" → "DeepSeek API" |
| `core/models/sync.py` | 远程可用性检查 URL 改为 DeepSeek |
| `apps/web/src/api/client.ts` | 无需改动（模型列表从后端获取） |

### Task 9：测试验证

- [ ] `core/config.py`：`create_client()` 生成正确 base_url
- [ ] `catalog.py`：只有 2 个模型，`get_default_model_id()` 返回 `deepseek-chat`
- [ ] `profiles.py`：`get_model_profile("deepseek-chat")` 返回正确画像
- [ ] `multimodal.py`：发图时返回友好错误提示
- [ ] `api_key_service.py`：读 `DEEPSEEK_API_KEY`
- [ ] 集成测试：端到端对话（deepseek-chat + deepseek-reasoner）
- [ ] 浏览器验收：模型下拉只有 2 项 + auto、发消息正常、reasoner 思考链显示

---

## 迁移风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| DeepSeek 无视觉模型 | 发图功能不可用 | Task 5 方案 A：友好提示 |
| 模型数从 18 → 2 | 用户选择大幅减少 | 后续可按需加回（如通过硅基流动补 Qwen） |
| BYOK 用户需重配 Key | 用户体验中断 | 前端提示"API 已切换，请重新配置 Key" |
| 历史会话模型 ID 不匹配 | 旧会话加载时模型找不到 | `loadSession` 做 fallback：model_id 不在 catalog 时用 default |
| deepseek-reasoner 思考链格式 | 前端 thinking_step 渲染可能不同 | DeepSeek R1 的 `reasoning_content` 需要适配 |
| 缓存 Token 计费差异 | DeepSeek 有缓存命中折扣 | 成本计算逻辑可能需要更新 |

---

## 执行顺序

1. **Task 1** → 配置层（base_url + tiers）
2. **Task 6** → 环境变量（`.env` 改 `DEEPSEEK_API_KEY`）
3. **Task 2** → 模型目录（catalog 替换）
4. **Task 3** → 模型画像（profiles 替换）
5. **Task 4** → 密钥服务（provider 改名）
6. **Task 5** → 多模态降级（视觉提示）
7. **Task 7-8** → 前端硬编码 + 引用清理
8. **Task 9** → 测试验证

> **预计总工时**：2-3 小时（含测试）

---

## 立即可做的准备（不改动代码）

- [ ] 注册 DeepSeek 平台：https://platform.deepseek.com
- [ ] 获取 API Key，测试 `curl https://api.deepseek.com/v1/chat/completions`
- [ ] 确认百炼额度到期日期
- [ ] 通知已有 BYOK 用户即将切换
