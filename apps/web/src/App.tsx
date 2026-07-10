import { useCallback, useEffect, useRef, useState } from "react";
import {
  checkHealth,
  createSession,
  deleteSession,
  fetchApiKeyStatus,
  fetchMe,
  getSession,
  listModels,
  listPermissions,
  listSessions,
  messagesFromSession,
  renameSession,
  resetSession,
  rollbackLastTurn,
  setSessionModel,
  setSessionPermission,
  submitConfirmation,
} from "./api/client";
import { streamChat } from "./api/sse";
import { ChatPanel } from "./components/ChatPanel";
import { ConfirmDialog } from "./components/ConfirmDialog";
import { LoginPage } from "./components/LoginPage";
import { SettingsModal } from "./components/SettingsModal";
import { AdminPanel } from "./components/AdminPanel";
import { SessionList } from "./components/SessionList";
import { ToolPanel } from "./components/ToolPanel";
import type {
  AgentModel,
  ChatMessage,
  PendingConfirmation,
  PermissionTier,
  SessionSummary,
  SseEvent,
} from "./types";
import type { ApiKeyStatus, WorkspaceUploadResult } from "./api/client";
import {
  clearAuth,
  getToken,
  loadStoredUser,
  updateStoredUser,
  type AuthUser,
} from "./auth";
import { applyTheme, loadStoredTheme, saveTheme, type ThemeMode } from "./theme";
import {
  clearCurrentSessionId,
  loadCurrentSessionId,
  saveCurrentSessionId,
} from "./sessionStore";
import { useBatchedToolEntries, useThrottledStreamingText } from "./streamBatch";
import { useColumnResize } from "./useColumnResize";
import { InstallPrompt } from "./components/InstallPrompt";
import { CHAT_MAX_IMAGES } from "./imageAttach";
import "./App.css";

export default function App() {
  const [authUser, setAuthUser] = useState<AuthUser | null>(() => loadStoredUser());
  const [authReady, setAuthReady] = useState(false);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const { entries: toolEntries, append: appendToolEntry, reset: resetToolEntries } =
    useBatchedToolEntries();
  const {
    text: streamingText,
    setThrottled: setStreamingThrottled,
    flush: flushStreamingText,
    clear: clearStreamingText,
  } = useThrottledStreamingText();
  const [input, setInput] = useState("");
  const [pendingImages, setPendingImages] = useState<string[]>([]);
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [editRollingBack, setEditRollingBack] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [backendOk, setBackendOk] = useState(true);
  const [toolsOpen, setToolsOpen] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [pendingConfirm, setPendingConfirm] = useState<PendingConfirmation | null>(
    null,
  );
  const [confirmSubmitting, setConfirmSubmitting] = useState(false);
  const [awaitingConfirm, setAwaitingConfirm] = useState(false);
  const [models, setModels] = useState<AgentModel[]>([]);
  const [selectedModelId, setSelectedModelId] = useState("auto");
  const [autoModelId, setAutoModelId] = useState("auto");
  const [permissionTiers, setPermissionTiers] = useState<PermissionTier[]>([]);
  const [selectedPermissionId, setSelectedPermissionId] = useState("balanced");
  const [themeMode, setThemeMode] = useState<ThemeMode>(() => loadStoredTheme());
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [adminOpen, setAdminOpen] = useState(false);
  const [apiKeyStatus, setApiKeyStatus] = useState<ApiKeyStatus | null>(null);
  const [workspaceRefreshToken, setWorkspaceRefreshToken] = useState(0);
  const [workspaceHighlightPath, setWorkspaceHighlightPath] = useState<string | null>(
    null,
  );
  const chatAbortRef = useRef<AbortController | null>(null);
  const {
    containerRef: layoutRef,
    startSidebarDrag,
    startAgentDrag,
  } = useColumnResize({ defaultSidebar: 280, defaultAgent: 340 });

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setAuthUser(null);
      setAuthReady(true);
      return;
    }
    void fetchMe()
      .then((user) => setAuthUser(user))
      .catch(() => {
        clearAuth();
        setAuthUser(null);
      })
      .finally(() => setAuthReady(true));
  }, []);

  useEffect(() => {
    if (!authUser) {
      setApiKeyStatus(null);
      return;
    }
    void fetchApiKeyStatus()
      .then(setApiKeyStatus)
      .catch(() => setApiKeyStatus(null));
  }, [authUser]);

  useEffect(() => {
    applyTheme(themeMode);
    saveTheme(themeMode);
  }, [themeMode]);

  useEffect(() => {
    if (themeMode !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => applyTheme("system");
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [themeMode]);

  const currentTitle =
    sessions.find((s) => s.id === currentId)?.title ?? "新对话";

  const showToast = useCallback((msg: string) => {
    setToast(msg);
    window.setTimeout(() => setToast(null), 2500);
  }, []);

  const handleWorkspaceUploadSuccess = useCallback(
    (result: WorkspaceUploadResult) => {
      setWorkspaceRefreshToken((t) => t + 1);
      if (result.root_entry) {
        setWorkspaceHighlightPath(result.root_entry);
      }
      let msg = `已导入 ${result.files_written} 个文件（${result.total_size}）`;
      if (result.skipped_files > 0) {
        msg += `，跳过 ${result.skipped_files} 个敏感/非法文件`;
      }
      if (result.switched_to_sandbox) {
        msg += "；已切换至云端沙箱视图";
      }
      showToast(msg);
    },
    [showToast],
  );

  const refreshSessions = useCallback(async () => {
    const list = await listSessions();
    setSessions(list);
    return list;
  }, []);

  const loadSession = useCallback(
    async (sessionId: string, role?: string, defaultModel?: string) => {
      const detail = await getSession(sessionId);
      setMessages(messagesFromSession(detail));
      setCurrentId(sessionId);
      if (authUser?.id) {
        saveCurrentSessionId(sessionId, authUser.id);
      }
      let modelId = detail.model ?? defaultModel ?? "auto";
      if (role && role !== "admin" && (modelId === "auto" || !modelId)) {
        modelId = defaultModel ?? "qwen3.6-flash";
        if (detail.model !== modelId) {
          try {
            await setSessionModel(sessionId, modelId);
          } catch {
            /* 会话模型修正失败不阻断加载 */
          }
        }
      }
      setSelectedModelId(modelId);
      setSelectedPermissionId(detail.permission ?? "balanced");
      setError(null);
    },
    [authUser?.id],
  );

  const ensureSession = useCallback(async () => {
    setLoading(true);
    try {
      const ok = await checkHealth();
      setBackendOk(ok);
      if (!ok) {
        setError("后端未就绪，请先启动 uv run python -m server");
        return;
      }

      let defaultModel = "auto";
      try {
        const catalog = await listModels(false);
        setModels(catalog.models);
        setAutoModelId(catalog.auto_model_id);
        if (catalog.default_model) {
          defaultModel = catalog.default_model;
        }
        if (catalog.role_restricted && catalog.default_model) {
          setSelectedModelId(catalog.default_model);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "模型列表加载失败");
      }

      try {
        const perm = await listPermissions();
        setPermissionTiers(perm.tiers);
      } catch {
        /* 权限档位加载失败不阻断 */
      }

      const list = await refreshSessions();
      const role = authUser?.role;
      const savedId = authUser?.id ? loadCurrentSessionId(authUser.id) : null;
      const pickId =
        savedId && list.some((s) => s.id === savedId) ? savedId : list[0]?.id;
      if (!pickId) {
        const created = await createSession(
          "新会话",
          role !== "admin" ? defaultModel : undefined,
        );
        await refreshSessions();
        await loadSession(created.id, role, defaultModel);
      } else {
        await loadSession(pickId, role, defaultModel);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, [authUser, loadSession, refreshSessions]);

  useEffect(() => {
    if (!authUser) return;
    void ensureSession();
  }, [authUser, ensureSession]);

  const awaitingServerReply =
    messages.length > 0 && messages[messages.length - 1]?.role === "user";

  useEffect(() => {
    if (!currentId || sending || loading || !authUser || !awaitingServerReply) return;

    const timer = window.setInterval(() => {
      void getSession(currentId)
        .then((detail) => {
          const fromServer = messagesFromSession(detail);
          setMessages((prev) => {
            if (fromServer.length <= prev.length) return prev;
            return fromServer;
          });
        })
        .catch(() => {
          /* 轮询失败静默 */
        });
    }, 4000);

    return () => window.clearInterval(timer);
  }, [authUser, awaitingServerReply, currentId, loading, sending]);

  function handleLogout() {
    clearAuth();
    if (authUser?.id) {
      clearCurrentSessionId(authUser.id);
    }
    setAuthUser(null);
    setSessions([]);
    setCurrentId(null);
    setMessages([]);
    resetToolEntries();
    setError(null);
  }

  if (!authReady) {
    return (
      <div className="app-shell">
        <div className="login-shell">
          <div className="login-card">正在验证登录…</div>
        </div>
      </div>
    );
  }

  if (!authUser) {
    return (
      <>
        <LoginPage onSuccess={setAuthUser} />
        <InstallPrompt />
      </>
    );
  }

  const user = authUser;

  async function handleSelect(sessionId: string) {
    if (sessionId === currentId || sending) return;
    setLoading(true);
    setSidebarOpen(false);
    try {
      await loadSession(sessionId, user.role, selectedModelId);
      resetToolEntries();
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载会话失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate() {
    if (sending) return;
    setLoading(true);
    try {
      const created = await createSession(
        "新会话",
        user.role !== "admin" ? selectedModelId : undefined,
      );
      await refreshSessions();
      await loadSession(created.id, user.role, selectedModelId);
      resetToolEntries();
      setSidebarOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建会话失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(sessionId: string) {
    if (sending) return;
    setLoading(true);
    try {
      await deleteSession(sessionId);
      const list = await refreshSessions();
      if (list.length === 0) {
        const created = await createSession(
          "新会话",
          user.role !== "admin" ? selectedModelId : undefined,
        );
        await refreshSessions();
        await loadSession(created.id, user.role, selectedModelId);
      } else if (sessionId === currentId) {
        await loadSession(list[0].id, user.role, selectedModelId);
      }
      resetToolEntries();
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除会话失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleRename(sessionId: string, title: string) {
    if (sending) return;
    try {
      await renameSession(sessionId, title);
      await refreshSessions();
      showToast("会话已重命名");
    } catch (e) {
      setError(e instanceof Error ? e.message : "重命名失败");
    }
  }

  async function handleReset() {
    if (!currentId || sending || loading) return;
    if (!window.confirm("确定清空当前会话的所有消息？此操作不可撤销。")) return;

    setLoading(true);
    setError(null);
    try {
      await resetSession(currentId);
      setMessages([]);
      resetToolEntries();
      showToast("对话已清空");
    } catch (e) {
      setError(e instanceof Error ? e.message : "清空失败");
    } finally {
      setLoading(false);
    }
  }

  async function handlePermissionChange(permissionId: string) {
    if (!currentId || sending || permissionId === selectedPermissionId) return;
    const prev = selectedPermissionId;
    setSelectedPermissionId(permissionId);
    try {
      await setSessionPermission(currentId, permissionId);
      await refreshSessions();
    } catch (e) {
      setSelectedPermissionId(prev);
      setError(e instanceof Error ? e.message : "切换权限失败");
    }
  }

  async function handleModelChange(modelId: string) {
    if (!currentId || sending || modelId === selectedModelId) return;
    const prev = selectedModelId;
    setSelectedModelId(modelId);
    try {
      await setSessionModel(currentId, modelId);
      await refreshSessions();
    } catch (e) {
      setSelectedModelId(prev);
      setError(e instanceof Error ? e.message : "切换模型失败");
    }
  }

  async function handleSend() {
    const text = input.trim();
    if ((!text && pendingImages.length === 0) || !currentId || sending) return;

    if (
      user.role !== "admin" &&
      apiKeyStatus &&
      !apiKeyStatus.configured
    ) {
      setError("请先在设置中保存你的 DashScope API Key");
      setSettingsOpen(true);
      return;
    }

    const chatModel =
      user.role === "admin"
        ? selectedModelId
        : selectedModelId === autoModelId
          ? (models[0]?.id ?? "qwen3.6-flash")
          : selectedModelId;

    const imagesToSend = pendingImages.slice(0, CHAT_MAX_IMAGES);
    setInput("");
    setPendingImages([]);
    setError(null);
    resetToolEntries();
    clearStreamingText();
    if (authUser?.id) {
      saveCurrentSessionId(currentId, authUser.id);
    }
    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        content: text,
        images: imagesToSend.length ? imagesToSend : undefined,
      },
    ]);
    setSending(true);
    setAwaitingConfirm(false);
    setPendingConfirm(null);

    chatAbortRef.current?.abort();
    const abortController = new AbortController();
    chatAbortRef.current = abortController;

    let reply = "";
    let streamError: string | null = null;
    let lastToolCall: { tool: string; args: Record<string, unknown> } | null = null;

    const bumpWorkspaceForFileTool = (tool: string, args: Record<string, unknown>) => {
      if (tool !== "write_file" && tool !== "edit_file") return;
      const filePath = args.file_path;
      if (typeof filePath !== "string" || !filePath) return;
      setWorkspaceRefreshToken((n) => n + 1);
      setWorkspaceHighlightPath(filePath);
    };

    try {
      await streamChat(
        {
          session_id: currentId,
          message: text,
          images: imagesToSend.length ? imagesToSend : undefined,
          model: chatModel,
          permission: selectedPermissionId,
        },
        (event: SseEvent) => {
          switch (event.event) {
            case "confirmation_required":
              setAwaitingConfirm(true);
              setPendingConfirm({
                confirmation_id: event.confirmation_id ?? "",
                tool: event.tool ?? "?",
                args: event.args ?? {},
                risk: event.risk ?? "review",
                summary: event.summary ?? "需要确认工具执行",
                explanation: event.explanation,
                impact: event.impact,
                severity: event.severity as PendingConfirmation["severity"],
                permission_tier: event.permission_tier,
              });
              break;
            case "loop_round":
              appendToolEntry({
                kind: "loop_round",
                round: event.round ?? 0,
                toolCount: event.tool_count ?? 0,
                time: event.time,
              });
              break;
            case "tool_call": {
              const call = {
                tool: event.tool ?? "?",
                args: event.args ?? {},
              };
              lastToolCall = call;
              appendToolEntry({
                kind: "tool_call",
                tool: call.tool,
                args: call.args,
                time: event.time,
              });
              break;
            }
            case "tool_result": {
              setAwaitingConfirm(false);
              setPendingConfirm(null);
              const pending = lastToolCall;
              const toolName = pending?.tool;
              const filePath =
                pending &&
                toolName &&
                (toolName === "write_file" || toolName === "edit_file") &&
                typeof pending.args.file_path === "string"
                  ? pending.args.file_path
                  : undefined;
              if (Boolean(event.success) && filePath && pending) {
                bumpWorkspaceForFileTool(pending.tool, pending.args);
              }
              appendToolEntry({
                kind: "tool_result",
                success: Boolean(event.success),
                preview: event.preview ?? event.result ?? "",
                tool: toolName,
                filePath,
                time: event.time,
              });
              lastToolCall = null;
              break;
            }
            case "thinking_step":
              appendToolEntry({
                kind: "thinking_step",
                stepType: (event.step_type as "thought" | "revision" | "conclusion") ?? "thought",
                content: event.content ?? "",
                round: event.round,
                time: event.time,
              });
              break;
            case "assistant_reply":
              reply = event.content ?? "";
              setStreamingThrottled(reply);
              break;
            case "done":
              if (event.content) {
                reply = event.content;
                flushStreamingText(event.content);
              }
              break;
            case "heartbeat":
              break;
            case "error":
              streamError = event.message ?? "未知错误";
              setError(streamError);
              break;
            default:
              break;
          }
        },
        abortController.signal,
      );

      if (!streamError) {
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant" && last.content === (reply || "（无回复）")) {
            return prev;
          }
          return [...prev, { role: "assistant", content: reply || "（无回复）" }];
        });
        await refreshSessions();
      }
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") {
        showToast("已停止等待 Agent 回复");
      } else {
        setError(e instanceof Error ? e.message : "发送失败");
      }
    } finally {
      if (chatAbortRef.current === abortController) {
        chatAbortRef.current = null;
      }
      clearStreamingText();
      setSending(false);
      setAwaitingConfirm(false);
      setPendingConfirm(null);
    }
  }

  function handleCancelSend() {
    chatAbortRef.current?.abort();
    clearStreamingText();
    setSending(false);
    setAwaitingConfirm(false);
    setPendingConfirm(null);
    showToast("已停止等待 Agent 回复");
  }

  async function handleEditLastMessage() {
    if (!currentId || editRollingBack) return;

    if (sending) {
      chatAbortRef.current?.abort();
      clearStreamingText();
      setSending(false);
    }
    setAwaitingConfirm(false);
    setPendingConfirm(null);

    setEditRollingBack(true);
    setError(null);
    try {
      const result = await rollbackLastTurn(currentId);
      setMessages(messagesFromSession(result.session));
      resetToolEntries();
      setInput(result.message);
      setPendingImages(result.images.slice(0, CHAT_MAX_IMAGES));
      window.setTimeout(() => {
        document.querySelector<HTMLTextAreaElement>(".composer-box textarea")?.focus();
      }, 0);
      await refreshSessions();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "编辑失败";
      setError(msg.includes("404") ? `${msg} · 请重启后端 server` : msg);
    } finally {
      setEditRollingBack(false);
    }
  }

  async function handleConfirm(allowed: boolean) {
    if (!currentId || !pendingConfirm) return;
    setConfirmSubmitting(true);
    try {
      await submitConfirmation(
        currentId,
        pendingConfirm.confirmation_id,
        allowed,
      );
      setPendingConfirm(null);
      setAwaitingConfirm(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "确认提交失败");
    } finally {
      setConfirmSubmitting(false);
    }
  }

  return (
    <div className="app-shell">
      {!backendOk && (
        <div className="notice-bar notice-banner">
          后端未连接 · 请运行 <code>uv run python -m server</code>
        </div>
      )}

      {toast && <div className="app-toast">{toast}</div>}

      <InstallPrompt />

      {user.role !== "admin" &&
        apiKeyStatus &&
        !apiKeyStatus.configured && (
          <div className="notice-bar notice-banner">
            尚未配置 DashScope API Key ·{" "}
            <button
              type="button"
              className="notice-link"
              onClick={() => setSettingsOpen(true)}
            >
              去设置
            </button>
          </div>
        )}

      <SettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        user={user}
        userRole={user.role}
        themeMode={themeMode}
        onThemeChange={setThemeMode}
        onLogout={handleLogout}
        onApiKeyUpdated={setApiKeyStatus}
        onProfileUpdated={(u) => {
          setAuthUser(u);
          updateStoredUser(u);
        }}
      />

      {user.role === "admin" && (
        <AdminPanel open={adminOpen} onClose={() => setAdminOpen(false)} />
      )}

      {pendingConfirm && (
        <ConfirmDialog
          pending={pendingConfirm}
          submitting={confirmSubmitting}
          onAllow={() => void handleConfirm(true)}
          onDeny={() => void handleConfirm(false)}
        />
      )}

      <div ref={layoutRef} className="app-layout app-layout-three">
        {sidebarOpen && (
          <button
            type="button"
            className="sidebar-backdrop"
            aria-label="关闭侧栏"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        <div className={sidebarOpen ? "sidebar-wrap open" : "sidebar-wrap"}>
          <SessionList
            sessions={sessions}
            currentId={currentId}
            loading={loading || sending}
            onSelect={handleSelect}
            onCreate={handleCreate}
            onDelete={handleDelete}
            onRename={handleRename}
            workspaceRefreshToken={workspaceRefreshToken}
            workspaceHighlightPath={workspaceHighlightPath}
            onWorkspaceUploadSuccess={handleWorkspaceUploadSuccess}
          />
        </div>

        <div
          role="separator"
          aria-orientation="vertical"
          aria-label="拖动调整左栏宽度"
          className="split-handle split-handle-col"
          onPointerDown={startSidebarDrag}
          title="拖动调整宽度"
        >
          <span className="split-handle-grip-v" aria-hidden />
        </div>

        <ChatPanel
          sessionTitle={currentTitle}
          messages={messages}
          input={input}
          sending={sending}
          loading={loading}
          awaitingConfirm={awaitingConfirm}
          streamingText={streamingText}
          error={error}
          models={models}
          selectedModelId={selectedModelId}
          autoModelId={autoModelId}
          permissionTiers={permissionTiers}
          selectedPermissionId={selectedPermissionId}
          onModelChange={(id) => void handleModelChange(id)}
          onPermissionChange={(id) => void handlePermissionChange(id)}
          onInputChange={setInput}
          pendingImages={pendingImages}
          onPendingImagesChange={setPendingImages}
          onAttachError={(msg) => setError(msg)}
          onAttachSuccess={(n) => setToast(`已添加 ${n} 张图片`)}
          onSend={() => void handleSend()}
          onCancelSend={handleCancelSend}
          onEditLastMessage={() => void handleEditLastMessage()}
          editBusy={editRollingBack}
          onReset={() => void handleReset()}
          onToggleSidebar={() => setSidebarOpen((v) => !v)}
          userEmail={user.email}
          userDisplayName={user.display_name}
          userAvatar={user.avatar}
          onOpenSettings={() => setSettingsOpen(true)}
          onOpenAdmin={
            user.role === "admin" ? () => setAdminOpen(true) : undefined
          }
          activityEntries={toolEntries}
          onOpenFile={(path) => {
            setWorkspaceRefreshToken((n) => n + 1);
            setWorkspaceHighlightPath(path);
            setSidebarOpen(true);
          }}
        />

        <div
          role="separator"
          aria-orientation="vertical"
          aria-label="拖动调整右栏宽度"
          className="split-handle split-handle-col"
          onPointerDown={startAgentDrag}
          title="拖动调整宽度"
        >
          <span className="split-handle-grip-v" aria-hidden />
        </div>

        <ToolPanel
          entries={toolEntries}
          open={toolsOpen}
          onToggle={() => setToolsOpen((v) => !v)}
          onOpenFile={(path) => {
            setWorkspaceRefreshToken((n) => n + 1);
            setWorkspaceHighlightPath(path);
            setSidebarOpen(true);
          }}
        />
      </div>
    </div>
  );
}
