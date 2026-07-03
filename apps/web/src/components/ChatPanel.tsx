import { useEffect, useMemo, useRef, type CSSProperties } from "react";

import type { AgentModel, PermissionTier } from "../types";

import { MessageContent } from "./MessageContent";
import { ThemeToggle } from "./ThemeToggle";
import type { ThemeMode } from "../theme";



interface ChatMessage {

  role: "user" | "assistant";

  content: string;

}



interface Props {

  sessionTitle: string;

  messages: ChatMessage[];

  input: string;

  sending: boolean;

  loading: boolean;

  awaitingConfirm?: boolean;

  streamingText: string;

  error: string | null;

  models: AgentModel[];

  selectedModelId: string;

  autoModelId: string;

  permissionTiers: PermissionTier[];

  selectedPermissionId: string;

  onModelChange: (modelId: string) => void;

  onPermissionChange: (permissionId: string) => void;

  onInputChange: (value: string) => void;

  onSend: () => void;

  onReset: () => void;

  onToggleSidebar?: () => void;

  themeMode: ThemeMode;

  onThemeChange: (mode: ThemeMode) => void;

}



function SendIcon() {

  return (

    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>

      <path

        d="M12 4l-1.5 1.5L16.2 11H4v2h12.2l-5.7 5.5L12 20l8-8-8-8z"

        fill="currentColor"

      />

    </svg>

  );

}



function MenuIcon() {

  return (

    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>

      <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />

    </svg>

  );

}



function ChevronIcon() {

  return (

    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden>

      <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />

    </svg>

  );

}



const QUICK_PROMPTS = [

  "列出当前项目目录结构",

  "在沙箱里创建一个 hello.py",

  "查看 MCP 与工具连接状态",

];



function UserAvatarIcon() {

  return (

    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>

      <circle cx="12" cy="8" r="3.5" stroke="currentColor" strokeWidth="1.6" />

      <path d="M5 20c0-3.3 3.1-6 7-6s7 2.7 7 6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />

    </svg>

  );

}



function AgentAvatarIcon() {

  return (

    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>

      <rect x="5" y="6" width="14" height="12" rx="3" stroke="currentColor" strokeWidth="1.6" />

      <path d="M9 10h6M9 14h4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />

    </svg>

  );

}



function ResetIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M4 7h16M10 11v6M14 11v6M6 7l1-3h10l1 3M9 7V4h6v3"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function PromptArrowIcon() {
  return (
    <svg className="welcome-prompt-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}



export function ChatPanel({

  sessionTitle,

  messages,

  input,

  sending,

  loading,

  awaitingConfirm = false,

  streamingText,

  error,

  models,

  selectedModelId,

  autoModelId,

  permissionTiers,

  selectedPermissionId,

  onModelChange,

  onPermissionChange,

  onInputChange,

  onSend,

  onReset,

  onToggleSidebar,

  themeMode,

  onThemeChange,

}: Props) {

  const bottomRef = useRef<HTMLDivElement>(null);

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const busy = sending || loading;



  const groupedModels = useMemo(() => {

    const map = new Map<string, AgentModel[]>();

    for (const m of models) {

      const list = map.get(m.group) ?? [];

      list.push(m);

      map.set(m.group, list);

    }

    return map;

  }, [models]);



  const selectedLabel = useMemo(() => {

    const found = models.find((m) => m.id === selectedModelId);

    if (found) return found.label;

    return selectedModelId === autoModelId ? "自动路由" : selectedModelId;

  }, [models, selectedModelId, autoModelId]);

  const permissionLabel = useMemo(() => {
    const found = permissionTiers.find((t) => t.id === selectedPermissionId);
    return found?.label ?? selectedPermissionId;
  }, [permissionTiers, selectedPermissionId]);

  const selectedModel = useMemo(
    () => models.find((m) => m.id === selectedModelId),
    [models, selectedModelId],
  );

  useEffect(() => {

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    bottomRef.current?.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });

  }, [messages, streamingText, sending]);



  useEffect(() => {

    function onGlobalKeyDown(e: KeyboardEvent) {

      const mod = e.ctrlKey || e.metaKey;

      if (!mod) return;

      const key = e.key.toLowerCase();

      if (key === "l") {

        e.preventDefault();

        const el = textareaRef.current;

        if (!el) return;

        el.focus();

        const len = el.value.length;

        el.setSelectionRange(len, len);

        return;

      }

      if (key === "k" && !busy) {

        e.preventDefault();

        onInputChange("");

        textareaRef.current?.focus();

      }

    }

    window.addEventListener("keydown", onGlobalKeyDown);

    return () => window.removeEventListener("keydown", onGlobalKeyDown);

  }, [busy, onInputChange]);



  function pickQuickPrompt(text: string) {

    if (busy) return;

    onInputChange(text);

    textareaRef.current?.focus();

  }
  useEffect(() => {

    const el = textareaRef.current;

    if (!el) return;

    el.style.height = "auto";

    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;

  }, [input]);



  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {

    if (e.key === "Enter" && !e.shiftKey) {

      e.preventDefault();

      if (!sending && input.trim()) onSend();

    }

  }



  return (

    <main className="chat-main">

      <header className="chat-topbar">

        <div className="chat-topbar-left">

          {onToggleSidebar && (

            <button

              type="button"

              className="chat-icon-btn sidebar-toggle"

              onClick={onToggleSidebar}

              title="切换侧栏"

            >

              <MenuIcon />

            </button>

          )}

          <div className="chat-topbar-title">{sessionTitle}</div>

        </div>

        <div className="chat-topbar-actions">

          <ThemeToggle mode={themeMode} onChange={onThemeChange} />

          {loading && !sending && (

            <span className="chat-status chat-status-loading">

              <span className="pulse-dot" />

              <span className="chat-status-label">加载中</span>

            </span>

          )}

          {awaitingConfirm && (

            <span className="chat-status chat-status-wait">

              <span className="pulse-dot" />

              <span className="chat-status-label">等待你的确认…</span>

            </span>

          )}

          {sending && !awaitingConfirm && (

            <span className="chat-status">

              <span className="pulse-dot" />

              <span className="chat-status-label">Agent 运行中</span>

            </span>

          )}

          <button

            type="button"

            className="chat-action-btn"

            onClick={onReset}

            disabled={busy}

            title="清空当前会话的所有消息 (Ctrl+K)"

            aria-label="清空对话"

          >

            <ResetIcon />

            <span className="chat-action-btn-label">清空对话</span>

          </button>

        </div>

      </header>



      <div className="chat-scroll">

        <div className="chat-thread">

          {messages.length === 0 && !sending && !loading && (

            <div className="chat-welcome">

              <p className="chat-welcome-eyebrow">Sheldon Agent</p>

              <h1>有什么可以帮你？</h1>

              <p className="chat-welcome-desc">

                读写文件、执行命令、调用 MCP 工具 — 从下面选一个开始，或直接输入问题。

              </p>

              <div className="chat-welcome-prompts">

                {QUICK_PROMPTS.map((prompt) => (

                  <button

                    key={prompt}

                    type="button"

                    className="welcome-prompt-chip"

                    onClick={() => pickQuickPrompt(prompt)}

                    disabled={busy}

                  >

                    <PromptArrowIcon />

                    {prompt}

                  </button>

                ))}

              </div>

            </div>

          )}



          {messages.map((m, i) => (

            <article

              key={i}

              className={`msg msg-${m.role}`}

              style={{ "--msg-index": i } as CSSProperties}

            >

              <div className="msg-avatar" aria-hidden>

                {m.role === "user" ? <UserAvatarIcon /> : <AgentAvatarIcon />}

              </div>

              <div className="msg-body">

                <div className="msg-label">

                  {m.role === "user" ? "You" : "Agent"}

                </div>

                <div className="msg-content">

                  <MessageContent content={m.content} />

                </div>

              </div>

            </article>

          ))}



          {sending && (

            <article className="msg msg-assistant msg-streaming">

              <div className="msg-avatar" aria-hidden>

                <AgentAvatarIcon />

              </div>

              <div className="msg-body">

                <div className="msg-label">Agent</div>

                <div className="msg-content">

                  {streamingText ? (

                    <MessageContent content={streamingText} />

                  ) : (

                    <span className="thinking-shimmer" aria-label="思考中">

                      <span />

                      <span />

                      <span />

                    </span>

                  )}

                  <span className="cursor">▍</span>

                </div>

              </div>

            </article>

          )}

          <div ref={bottomRef} />

        </div>

      </div>



      {error && (

        <div className="notice-bar notice-error" role="alert">

          {error}

        </div>

      )}



      <div className="composer-wrap">

        <div className="composer-box">

          <textarea

            ref={textareaRef}

            value={input}

            onChange={(e) => onInputChange(e.target.value)}

            onKeyDown={handleKeyDown}

            placeholder="输入消息 · Enter 发送 · Ctrl+L 聚焦 · Ctrl+K 清空"

            rows={1}

            disabled={sending}

          />

          <div className="composer-footer">

            <div className="composer-model-wrap">

              <label className="composer-model-select" title={selectedLabel}>

                <span className="composer-model-label">{selectedLabel}</span>

                <ChevronIcon />

                <select

                  value={selectedModelId}

                  onChange={(e) => onModelChange(e.target.value)}

                  disabled={busy || models.length === 0}

                  aria-label="选择模型"

                >

                  {models.length === 0 ? (

                    <option value={selectedModelId}>{selectedLabel}</option>

                  ) : (

                    Array.from(groupedModels.entries()).map(([group, items]) => (

                      <optgroup key={group} label={group}>

                        {items.map((m) => (

                          <option

                            key={m.id}

                            value={m.id}

                            disabled={!m.available}

                            title={
                              [
                                m.description,
                                m.tagline,
                                m.features?.length ? m.features.join(" · ") : "",
                              ]
                                .filter(Boolean)
                                .join("\n")
                            }

                          >

                            {m.label}

                            {!m.available ? " (未开通)" : ""}

                          </option>

                        ))}

                      </optgroup>

                    ))

                  )}

                </select>

              </label>

            </div>

            <div className="composer-perm-wrap">
              <label className="composer-model-select" title={permissionLabel}>
                <span className="composer-model-label">{permissionLabel}</span>
                <ChevronIcon />
                <select
                  value={selectedPermissionId}
                  onChange={(e) => onPermissionChange(e.target.value)}
                  disabled={busy || permissionTiers.length === 0}
                  aria-label="权限档位"
                >
                  {permissionTiers.length === 0 ? (
                    <option value={selectedPermissionId}>{permissionLabel}</option>
                  ) : (
                    permissionTiers.map((t) => (
                      <option key={t.id} value={t.id} title={t.description}>
                        {t.label}
                      </option>
                    ))
                  )}
                </select>
              </label>
            </div>

            <button

              type="button"

              className="composer-send"

              onClick={onSend}

              disabled={sending || !input.trim()}

              title="发送 (Enter)"

            >

              <SendIcon />

            </button>

          </div>

        </div>

        <p className="composer-hint">Shift+Enter 换行 · Ctrl+L 聚焦 · Ctrl+K 清空</p>

        {selectedModel?.features && selectedModel.features.length > 0 && (
          <div className="model-feature-bar" title={selectedModel.tagline}>
            {selectedModel.tagline && (
              <span className="model-feature-tagline">{selectedModel.tagline}</span>
            )}
            {selectedModel.features.slice(0, 4).map((f) => (
              <span key={f} className="model-feature-chip">
                {f}
              </span>
            ))}
          </div>
        )}

      </div>

    </main>

  );

}

