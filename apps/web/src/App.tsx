import { useCallback, useEffect, useState } from "react";
import {
  checkHealth,
  createSession,
  deleteSession,
  getSession,
  listModels,
  listPermissions,
  listSessions,
  messagesFromSession,
  renameSession,
  resetSession,
  setSessionModel,
  setSessionPermission,
  submitConfirmation,
} from "./api/client";
import { streamChat } from "./api/sse";
import { ChatPanel } from "./components/ChatPanel";
import { ConfirmDialog } from "./components/ConfirmDialog";
import { SessionList } from "./components/SessionList";
import { ToolPanel } from "./components/ToolPanel";
import type {
  AgentModel,
  ChatMessage,
  PendingConfirmation,
  PermissionTier,
  SessionSummary,
  SseEvent,
  ToolLogEntry,
} from "./types";
import { USER_ID } from "./types";
import { applyTheme, loadStoredTheme, saveTheme, type ThemeMode } from "./theme";
import "./App.css";

export default function App() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [toolEntries, setToolEntries] = useState<ToolLogEntry[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [loading, setLoading] = useState(true);
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

  const refreshSessions = useCallback(async () => {
    const list = await listSessions();
    setSessions(list);
    return list;
  }, []);

  const loadSession = useCallback(async (sessionId: string) => {
    const detail = await getSession(sessionId);
    setMessages(messagesFromSession(detail));
    setCurrentId(sessionId);
    setSelectedModelId(detail.model ?? "auto");
    setSelectedPermissionId(detail.permission ?? "balanced");
    setError(null);
  }, []);

  const ensureSession = useCallback(async () => {
    setLoading(true);
    try {
      const ok = await checkHealth();
      setBackendOk(ok);
      if (!ok) {
        setError("后端未就绪，请先启动 uv run python -m server");
        return;
      }

      try {
        const catalog = await listModels(false);
        setModels(catalog.models);
        setAutoModelId(catalog.auto_model_id);
      } catch {
        /* 模型目录加载失败不阻断主流程 */
      }

      try {
        const perm = await listPermissions();
        setPermissionTiers(perm.tiers);
      } catch {
        /* 权限档位加载失败不阻断 */
      }

      const list = await refreshSessions();
      if (list.length === 0) {
        const created = await createSession();
        await refreshSessions();
        await loadSession(created.id);
      } else {
        await loadSession(list[0].id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, [loadSession, refreshSessions]);

  useEffect(() => {
    void ensureSession();
  }, [ensureSession]);

  async function handleSelect(sessionId: string) {
    if (sessionId === currentId || sending) return;
    setLoading(true);
    setSidebarOpen(false);
    try {
      await loadSession(sessionId);
      setToolEntries([]);
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
      const created = await createSession();
      await refreshSessions();
      await loadSession(created.id);
      setToolEntries([]);
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
        const created = await createSession();
        await refreshSessions();
        await loadSession(created.id);
      } else if (sessionId === currentId) {
        await loadSession(list[0].id);
      }
      setToolEntries([]);
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
      setToolEntries([]);
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
    if (!text || !currentId || sending) return;

    setInput("");
    setError(null);
    setToolEntries([]);
    setStreamingText("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setSending(true);
    setAwaitingConfirm(false);
    setPendingConfirm(null);

    let reply = "";

    try {
      await streamChat(
        {
          user_id: USER_ID,
          session_id: currentId,
          message: text,
          model: selectedModelId,
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
              setToolEntries((prev) => [
                ...prev,
                {
                  kind: "loop_round",
                  round: event.round ?? 0,
                  toolCount: event.tool_count ?? 0,
                  time: event.time,
                },
              ]);
              break;
            case "tool_call":
              setToolEntries((prev) => [
                ...prev,
                {
                  kind: "tool_call",
                  tool: event.tool ?? "?",
                  args: event.args ?? {},
                  time: event.time,
                },
              ]);
              break;
            case "tool_result":
              setToolEntries((prev) => [
                ...prev,
                {
                  kind: "tool_result",
                  success: Boolean(event.success),
                  preview: event.preview ?? event.result ?? "",
                  time: event.time,
                },
              ]);
              break;
            case "thinking_step":
              setToolEntries((prev) => [
                ...prev,
                {
                  kind: "thinking_step",
                  stepType:
                    (event.step_type as "thought" | "revision" | "conclusion") ??
                    "thought",
                  content: event.content ?? "",
                  round: event.round,
                  time: event.time,
                },
              ]);
              break;
            case "assistant_reply":
              reply = event.content ?? "";
              setStreamingText(reply);
              break;
            case "error":
              setError(event.message ?? "未知错误");
              break;
            default:
              break;
          }
        },
      );

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: reply || "（无回复）" },
      ]);
      await refreshSessions();
    } catch (e) {
      setError(e instanceof Error ? e.message : "发送失败");
    } finally {
      setStreamingText("");
      setSending(false);
      setAwaitingConfirm(false);
      setPendingConfirm(null);
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

      {pendingConfirm && (
        <ConfirmDialog
          pending={pendingConfirm}
          submitting={confirmSubmitting}
          onAllow={() => void handleConfirm(true)}
          onDeny={() => void handleConfirm(false)}
        />
      )}

      <div className="app-layout">
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
          />
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
          onSend={() => void handleSend()}
          onReset={() => void handleReset()}
          onToggleSidebar={() => setSidebarOpen((v) => !v)}
          themeMode={themeMode}
          onThemeChange={setThemeMode}
        />

        <ToolPanel
          entries={toolEntries}
          open={toolsOpen}
          onToggle={() => setToolsOpen((v) => !v)}
        />
      </div>
    </div>
  );
}
