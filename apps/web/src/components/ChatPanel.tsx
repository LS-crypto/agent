import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";

import type { AgentModel, ChatMessage, PermissionTier, ToolLogEntry } from "../types";
import { deriveAgentStatusHint } from "../agentStatusHint";
import { formatModelOptionLabel } from "../modelLabels";
import { CHAT_MAX_IMAGES, readImageFiles, snapshotFiles } from "../imageAttach";

import { MessageContent } from "./MessageContent";
import { ActivityCards } from "./ActivityCards";



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

  pendingImages?: string[];

  onPendingImagesChange?: (images: string[]) => void;

  onAttachError?: (message: string) => void;

  onAttachSuccess?: (count: number) => void;

  onSend: () => void;

  onCancelSend?: () => void;

  onEditLastMessage?: () => void;

  editBusy?: boolean;

  onReset: () => void;

  onToggleSidebar?: () => void;

  userEmail?: string;

  userDisplayName?: string | null;

  userAvatar?: string | null;

  onOpenSettings?: () => void;

  onOpenAdmin?: () => void;

  activityEntries?: ToolLogEntry[];

  onOpenFile?: (path: string) => void;

}



function ImageAttachIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect x="4" y="5" width="16" height="14" rx="2" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="9" cy="10" r="1.5" fill="currentColor" />
      <path d="M4 16l4.5-4.5 3 3L14 12l6 6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
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

  pendingImages = [],

  onPendingImagesChange,

  onAttachError,

  onAttachSuccess,

  onSend,

  onCancelSend,

  onEditLastMessage,

  editBusy = false,

  onReset,

  onToggleSidebar,

  userEmail,

  userDisplayName,

  userAvatar,

  onOpenSettings,

  onOpenAdmin,

  activityEntries = [],

  onOpenFile,

}: Props) {

  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const lastScrollAtRef = useRef(0);
  const activityCount = activityEntries.length;
  const [imageLoading, setImageLoading] = useState<{
    percent: number;
    label: string;
  } | null>(null);
  const [attachError, setAttachError] = useState<string | null>(null);

  const busy = sending || loading || imageLoading !== null;
  const canSend = Boolean(input.trim() || pendingImages.length > 0);
  const attachDisabled =
    sending || imageLoading !== null || pendingImages.length >= CHAT_MAX_IMAGES;

  const agentStatusHint = useMemo(
    () =>
      deriveAgentStatusHint(activityEntries, {
        sending,
        streamingText,
        awaitingConfirm,
      }),
    [activityEntries, sending, streamingText, awaitingConfirm],
  );



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

    if (found) return formatModelOptionLabel(found);

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
    const now = Date.now();
    if (sending && now - lastScrollAtRef.current < 120) return;
    lastScrollAtRef.current = now;
    bottomRef.current?.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });
  }, [messages, streamingText, sending, activityCount]);



  const lastUserIndex = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (messages[i].role === "user") return i;
    }
    return -1;
  }, [messages]);

  const canEditLast =
    lastUserIndex >= 0 &&
    Boolean(onEditLastMessage) &&
    !editBusy &&
    !awaitingConfirm;

  function renderMessageBody(m: ChatMessage, editable: boolean) {
    const inner = (
      <>
        {m.images && m.images.length > 0 && (
          <div className="msg-images">
            {m.images.map((src, j) => (
              <img key={j} src={src} alt="" className="msg-image" loading="lazy" />
            ))}
          </div>
        )}
        {m.content.trim() ? <MessageContent content={m.content} /> : null}
      </>
    );

    if (!editable) {
      return <div className="msg-content">{inner}</div>;
    }

    return (
      <div
        className="msg-content msg-content-editable"
        role="button"
        tabIndex={editBusy ? -1 : 0}
        aria-disabled={editBusy}
        aria-label="点击编辑并重新发送"
        onClick={() => {
          if (editBusy) return;
          onEditLastMessage?.();
        }}
        onKeyDown={(e) => {
          if (editBusy) return;
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onEditLastMessage?.();
          }
        }}
      >
        {inner}
      </div>
    );
  }



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

      if (!sending && canSend) onSend();

    }

  }



  async function ingestImageFiles(files: File[]) {
    if (!files.length || !onPendingImagesChange) {
      setAttachError("无法添加图片：组件未就绪");
      return;
    }

    setAttachError(null);
    setImageLoading({ percent: 0, label: "准备读取图片…" });
    try {
      const urls = await readImageFiles(files, pendingImages.length, (p) => {
        setImageLoading({
          percent: p.percent,
          label: `正在读取 ${p.currentFile}（${p.fileIndex}/${p.fileCount}）`,
        });
      });
      onPendingImagesChange([...pendingImages, ...urls].slice(0, CHAT_MAX_IMAGES));
      onAttachSuccess?.(urls.length);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "添加图片失败";
      setAttachError(msg);
      onAttachError?.(msg);
    } finally {
      setImageLoading(null);
    }
  }

  async function handleImagePick(e: React.ChangeEvent<HTMLInputElement>) {
    const picked = snapshotFiles(e.target.files);
    e.target.value = "";
    await ingestImageFiles(picked);
  }

  async function handleComposerPaste(e: React.ClipboardEvent) {
    const items = e.clipboardData?.items;
    if (!items?.length) return;
    const imageFiles: File[] = [];
    for (let i = 0; i < items.length; i += 1) {
      const item = items[i];
      if (item.kind !== "file") continue;
      const file = item.getAsFile();
      if (file) imageFiles.push(file);
    }
    if (!imageFiles.length) return;
    e.preventDefault();
    await ingestImageFiles(imageFiles);
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

          {onOpenSettings && (
            <button
              type="button"
              className="chat-settings-btn"
              onClick={onOpenSettings}
              title="设置"
            >
              <span className="chat-settings-avatar" aria-hidden>
                {userAvatar ?? "🦊"}
              </span>
              <span className="chat-settings-label">
                {userDisplayName?.trim() || userEmail?.split("@")[0] || "设置"}
              </span>
            </button>
          )}

          {onOpenAdmin && (
            <button
              type="button"
              className="chat-icon-btn chat-admin-btn"
              onClick={onOpenAdmin}
              title="主管后台"
            >
              后台
            </button>
          )}

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

          {sending && !awaitingConfirm && agentStatusHint && (

            <span className="chat-status">

              <span className="pulse-dot" />

              <span className="chat-status-label">{agentStatusHint}</span>

            </span>

          )}

          {sending && onCancelSend && (

            <button

              type="button"

              className="chat-action-btn chat-cancel-btn"

              onClick={onCancelSend}

              title="停止等待（不会中断后端已开始的任务）"

              aria-label="停止等待"

            >

              停止

            </button>

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

              <p className="chat-welcome-eyebrow">烁士生</p>

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



          {messages.map((m, i) => {
            const editable = m.role === "user" && i === lastUserIndex && canEditLast;

            return (
            <div key={i} className="msg-group">

            <article

              className={`msg msg-${m.role}${editable ? " msg-editable" : ""}`}

              style={{ "--msg-index": i } as CSSProperties}

            >

              <div className="msg-avatar" aria-hidden>

                {m.role === "user" ? <UserAvatarIcon /> : <AgentAvatarIcon />}

              </div>

              <div className="msg-body">

                <div className="msg-label">

                  {m.role === "user" ? "You" : "Agent"}

                  {editable && <span className="msg-edit-hint">点击编辑</span>}

                </div>

                {renderMessageBody(m, editable)}

              </div>

            </article>

            {m.role === "user" &&
              i === lastUserIndex &&
              activityEntries.length > 0 &&
              (sending || messages[i + 1]?.role === "assistant") && (
                <ActivityCards
                  entries={activityEntries}
                  sending={sending}
                  onOpenFile={onOpenFile}
                />
              )}

            </div>

          );
          })}



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

                    <span className="agent-thinking-hint" aria-live="polite">
                      <span className="thinking-shimmer" aria-hidden>
                        <span />
                        <span />
                        <span />
                      </span>
                      <span className="agent-thinking-text">
                        {agentStatusHint ?? "准备下一步…"}
                      </span>
                    </span>

                  )}

                  {streamingText ? <span className="cursor">▍</span> : null}

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

        <div className="composer-box" onPaste={(e) => void handleComposerPaste(e)}>

          {attachError && (
            <div className="composer-image-error" role="alert">
              {attachError}
            </div>
          )}

          {imageLoading && (
            <div className="composer-image-progress" role="status" aria-live="polite">
              <div className="composer-image-progress-label">{imageLoading.label}</div>
              <div className="composer-image-progress-bar">
                <div
                  className="composer-image-progress-fill"
                  style={{ width: `${Math.max(imageLoading.percent, 4)}%` }}
                />
              </div>
            </div>
          )}

          {pendingImages.length > 0 && (
            <div className="composer-image-strip">
              {pendingImages.map((src, i) => (
                <div key={i} className="composer-image-chip">
                  <img src={src} alt="" className="composer-image-thumb" />
                  <button
                    type="button"
                    className="composer-image-remove"
                    onClick={() =>
                      onPendingImagesChange?.(pendingImages.filter((_, j) => j !== i))
                    }
                    disabled={sending}
                    aria-label="移除图片"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}

          <textarea

            ref={textareaRef}

            value={input}

            onChange={(e) => onInputChange(e.target.value)}

            onKeyDown={handleKeyDown}

            placeholder="输入消息 · Enter 发送 · Ctrl+L 聚焦 · Ctrl+K 清空"

            rows={1}

            disabled={sending || imageLoading !== null}

          />

          <div className="composer-footer">

            {!attachDisabled ? (
              <label className="composer-attach-wrap" title={`添加图片（最多 ${CHAT_MAX_IMAGES} 张）`}>
                <span className="composer-attach" aria-hidden>
                  <ImageAttachIcon />
                </span>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/gif,image/webp,.jpg,.jpeg,.png,.gif,.webp"
                  multiple
                  className="composer-file-input"
                  aria-label="添加图片"
                  onChange={(e) => void handleImagePick(e)}
                />
              </label>
            ) : (
              <span
                className="composer-attach is-disabled"
                title={
                  pendingImages.length >= CHAT_MAX_IMAGES
                    ? `已达 ${CHAT_MAX_IMAGES} 张上限`
                    : imageLoading
                      ? "正在读取图片…"
                      : "请等待当前操作完成"
                }
                aria-label="添加图片（不可用）"
              >
                <ImageAttachIcon />
              </span>
            )}

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

                            {formatModelOptionLabel(m)}

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

              disabled={sending || !canSend}

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

