import { useCallback, useEffect, useRef, useState } from "react";
import {
  fetchAdminActivity,
  fetchAdminStats,
  fetchAdminUserDetail,
  fetchAdminUsers,
  listModels,
  setAdminUserStatus,
  type AdminActivityEvent,
  type AdminUserSummary,
} from "../api/client";
import { API_BASE } from "../config";
import { getAuthHeaders, onUnauthorized } from "../auth";
import type { AgentModel } from "../types";
import "./AdminPanel.css";

interface Props {
  open: boolean;
  onClose: () => void;
}

type Tab = "users" | "live" | "models";

function formatEventLine(ev: AdminActivityEvent): string {
  switch (ev.event) {
    case "user_message":
      return `提问：${ev.content ?? ""}`;
    case "tool_call":
      return `工具 ${ev.tool ?? "?"} ${JSON.stringify(ev.args ?? {})}`;
    case "tool_result":
      return `结果：${(ev.preview ?? "").slice(0, 120)}`;
    case "assistant_reply":
      return `回复：${(ev.content ?? "").slice(0, 120)}`;
    case "error":
      return `错误：${ev.message ?? ""}`;
    case "heartbeat":
      return "—";
    default:
      return ev.event;
  }
}

export function AdminPanel({ open, onClose }: Props) {
  const [tab, setTab] = useState<Tab>("users");
  const [users, setUsers] = useState<AdminUserSummary[]>([]);
  const [stats, setStats] = useState<{
    total_users: number;
    active_users: number;
    banned_users: number;
    with_api_key: number;
  } | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [questions, setQuestions] = useState<Array<{ time?: string; content: string }>>([]);
  const [liveEvents, setLiveEvents] = useState<AdminActivityEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState(false);
  const [catalogModels, setCatalogModels] = useState<AgentModel[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  const refreshModels = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const catalog = await listModels(false);
      setCatalogModels(catalog.models.filter((m) => m.id !== "auto"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "模型列表加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [userRes, statRes] = await Promise.all([
        fetchAdminUsers(),
        fetchAdminStats(),
      ]);
      setUsers(userRes.users);
      setStats(statRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadUserDetail = useCallback(async (userId: string) => {
    setSelectedId(userId);
    try {
      const detail = await fetchAdminUserDetail(userId);
      setQuestions(detail.recent_questions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载用户详情失败");
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    void refreshUsers();
    void refreshModels();
  }, [open, refreshUsers, refreshModels]);

  useEffect(() => {
    if (!open || tab !== "live") {
      abortRef.current?.abort();
      abortRef.current = null;
      return;
    }

    const controller = new AbortController();
    abortRef.current = controller;
    setLiveEvents([]);

    async function run() {
      try {
        const res = await fetch(`${API_BASE}/admin/activity/live`, {
          headers: getAuthHeaders(),
          signal: controller.signal,
        });
        if (res.status === 401) {
          onUnauthorized();
          return;
        }
        if (!res.ok || !res.body) {
          throw new Error(`实时活动连接失败 (${res.status})`);
        }
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n\n");
          buffer = parts.pop() ?? "";
          for (const part of parts) {
            const line = part
              .split("\n")
              .map((l) => l.trim())
              .find((l) => l.startsWith("data: "));
            if (!line) continue;
            const ev = JSON.parse(line.slice(6)) as AdminActivityEvent;
            if (ev.event === "heartbeat") continue;
            setLiveEvents((prev) => [ev, ...prev].slice(0, 200));
          }
        }
      } catch (err) {
        if (controller.signal.aborted) return;
        setError(err instanceof Error ? err.message : "实时活动断开");
      }
    }

    void run();
    return () => controller.abort();
  }, [open, tab]);

  async function handleBanToggle(user: AdminUserSummary) {
    if (user.role === "admin") return;
    const next = user.status === "banned" ? "active" : "banned";
    const label = next === "banned" ? "拉黑" : "解除拉黑";
    if (!window.confirm(`确定${label}用户 ${user.email}？`)) return;
    setActionBusy(true);
    try {
      await setAdminUserStatus(user.id, next);
      await refreshUsers();
      if (selectedId === user.id) {
        await loadUserDetail(user.id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    } finally {
      setActionBusy(false);
    }
  }

  async function handleLoadHistory() {
    setLoading(true);
    try {
      const res = await fetchAdminActivity({
        limit: 100,
        event: "user_message,tool_call,error",
      });
      setLiveEvents(res.events.reverse());
      setTab("live");
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载活动失败");
    } finally {
      setLoading(false);
    }
  }

  if (!open) return null;

  return (
    <div className="admin-overlay" onClick={onClose} role="presentation">
      <div
        className="admin-panel"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-labelledby="admin-title"
      >
        <div className="admin-header">
          <div>
            <h2 id="admin-title">主管后台</h2>
            {stats && (
              <p className="admin-stats-line">
                用户 {stats.total_users} · 活跃 {stats.active_users} · 已配置 Key{" "}
                {stats.with_api_key} · 拉黑 {stats.banned_users}
              </p>
            )}
          </div>
          <button type="button" className="admin-close" onClick={onClose} aria-label="关闭">
            ×
          </button>
        </div>

        <div className="admin-tabs">
          <button
            type="button"
            className={tab === "users" ? "active" : ""}
            onClick={() => setTab("users")}
          >
            用户管理
          </button>
          <button
            type="button"
            className={tab === "live" ? "active" : ""}
            onClick={() => setTab("live")}
          >
            实时活动
          </button>
          <button
            type="button"
            className={tab === "models" ? "active" : ""}
            onClick={() => setTab("models")}
          >
            模型
          </button>
          <button type="button" className="admin-ghost" onClick={() => void handleLoadHistory()}>
            加载今日记录
          </button>
        </div>

        {error && <div className="admin-error">{error}</div>}
        {loading && <div className="admin-muted">加载中…</div>}

        {tab === "users" && (
          <div className="admin-layout">
            <div className="admin-user-list">
              {users.map((u) => (
                <button
                  key={u.id}
                  type="button"
                  className={
                    selectedId === u.id ? "admin-user-item active" : "admin-user-item"
                  }
                  onClick={() => void loadUserDetail(u.id)}
                >
                  <span className="admin-user-email">{u.email}</span>
                  <span className="admin-user-meta">
                    {u.role} · {u.status} · Key:{u.has_api_key ? "有" : "无"} · 会话
                    {u.session_count}
                  </span>
                  {u.db_path && (
                    <span className="admin-user-db" title={u.db_path}>
                      库: …{u.db_path.slice(-40)}
                    </span>
                  )}
                </button>
              ))}
            </div>
            <div className="admin-detail">
              {!selectedId && <p className="admin-muted">选择用户查看提问记录</p>}
              {selectedId && (
                <>
                  {(() => {
                    const u = users.find((x) => x.id === selectedId);
                    if (!u) return null;
                    return (
                      <div className="admin-detail-head">
                        <div>
                          <strong>{u.email}</strong>
                          {u.workspace_dir && (
                            <p className="admin-storage-line" title={u.workspace_dir}>
                              工作区: {u.workspace_dir}
                            </p>
                          )}
                          {u.db_path && (
                            <p className="admin-storage-line" title={u.db_path}>
                              会话库: {u.db_path}
                            </p>
                          )}
                        </div>
                        {u.role !== "admin" && (
                          <button
                            type="button"
                            disabled={actionBusy}
                            onClick={() => void handleBanToggle(u)}
                          >
                            {u.status === "banned" ? "解除拉黑" : "拉黑"}
                          </button>
                        )}
                      </div>
                    );
                  })()}
                  <h3>最近提问</h3>
                  <ul className="admin-questions">
                    {questions.length === 0 && (
                      <li className="admin-muted">暂无提问记录</li>
                    )}
                    {questions.map((q, i) => (
                      <li key={`${q.time ?? ""}-${i}`}>
                        <time>{q.time ?? ""}</time>
                        <p>{q.content}</p>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          </div>
        )}

        {tab === "live" && (
          <div className="admin-live">
            {liveEvents.length === 0 && (
              <p className="admin-muted">等待用户活动…（提问、工具调用会实时显示）</p>
            )}
            {liveEvents.map((ev, i) => (
              <div key={`${ev.time ?? ""}-${ev.user_id ?? ""}-${i}`} className="admin-live-row">
                <span className="admin-live-time">{ev.time ?? ""}</span>
                <span className="admin-live-user">{ev.user_id ?? "?"}</span>
                <span className="admin-live-event">{ev.event}</span>
                <span className="admin-live-text">{formatEventLine(ev)}</span>
              </div>
            ))}
          </div>
        )}

        {tab === "models" && (
          <div className="admin-models">
            <p className="admin-muted admin-models-hint">
              聊天区 Composer 下拉可切换模型；标有「普通用户」的 12 款对注册用户开放。
            </p>
            <div className="admin-models-table-wrap">
              <table className="admin-models-table">
                <thead>
                  <tr>
                    <th>模型</th>
                    <th>类型</th>
                    <th>账号开通</th>
                    <th>普通用户</th>
                  </tr>
                </thead>
                <tbody>
                  {catalogModels.length === 0 && (
                    <tr>
                      <td colSpan={4} className="admin-muted">
                        暂无模型数据
                      </td>
                    </tr>
                  )}
                  {catalogModels.map((m) => (
                    <tr key={m.id} className={m.available ? "" : "admin-models-unavailable"}>
                      <td>
                        <span className="admin-models-name">{m.label}</span>
                        <span className="admin-models-id">{m.id}</span>
                      </td>
                      <td>
                        {m.group}
                        {m.supports_vision ? " · 视觉" : ""}
                      </td>
                      <td>{m.available ? "已开通" : "未开通"}</td>
                      <td>{m.in_user_whitelist ? "✓" : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
