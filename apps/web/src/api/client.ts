import type { ModelsResponse, PermissionTier, SessionDetail, SessionSummary } from "../types";
import type { AuthUser } from "../auth";
import { getAuthHeaders, onUnauthorized } from "../auth";
import { API_BASE, HEALTH_URL } from "../config";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
      ...init?.headers,
    },
    ...init,
  });
  if (res.status === 401) {
    onUnauthorized();
    throw new Error("登录已失效，请重新登录");
  }
  if (!res.ok) {
    const text = await res.text();
    let detail = text;
    try {
      const parsed = JSON.parse(text) as { detail?: string };
      if (parsed.detail) detail = parsed.detail;
    } catch {
      /* keep raw text */
    }
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(HEALTH_URL);
    if (!res.ok) return false;
    const data = (await res.json()) as { status?: string };
    return data.status === "ok";
  } catch {
    return false;
  }
}

export function fetchMe(): Promise<AuthUser & { created_at?: string | null; last_login_at?: string | null }> {
  return request("/auth/me");
}

export interface ApiKeyStatus {
  configured: boolean;
  hint: string | null;
  uses_platform_key?: boolean;
  updated_at?: string | null;
}

export function fetchProfile(): Promise<
  AuthUser & { created_at?: string | null; last_login_at?: string | null }
> {
  return request("/settings/profile");
}

export function updateProfile(body: {
  display_name?: string;
  avatar?: string;
}): Promise<AuthUser & { created_at?: string | null; last_login_at?: string | null }> {
  return request("/settings/profile", {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function fetchApiKeyStatus(): Promise<ApiKeyStatus> {
  return request("/settings/api-key");
}

export function saveUserApiKey(apiKey: string): Promise<ApiKeyStatus> {
  return request("/settings/api-key", {
    method: "PUT",
    body: JSON.stringify({ api_key: apiKey }),
  });
}

export function deleteUserApiKey(): Promise<ApiKeyStatus> {
  return request("/settings/api-key", { method: "DELETE" });
}

export function listSessions(): Promise<SessionSummary[]> {
  return request("/sessions");
}

export function createSession(title = "新会话", model?: string): Promise<SessionDetail> {
  const body: { title: string; model?: string } = { title };
  if (model) body.model = model;
  return request("/sessions", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getSession(sessionId: string): Promise<SessionDetail> {
  return request(`/sessions/${sessionId}`);
}

export function deleteSession(sessionId: string): Promise<void> {
  return request(`/sessions/${sessionId}`, {
    method: "DELETE",
  });
}

export function resetSession(sessionId: string): Promise<SessionDetail> {
  return request(`/sessions/${sessionId}/reset`, { method: "POST" });
}

export function renameSession(
  sessionId: string,
  title: string,
): Promise<SessionDetail> {
  return request(`/sessions/${sessionId}`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });
}

export function listModels(checkRemote = true): Promise<ModelsResponse> {
  return request(`/models?check_remote=${checkRemote ? "true" : "false"}`);
}

export function setSessionPermission(
  sessionId: string,
  permission: string,
): Promise<SessionDetail> {
  return request(`/sessions/${sessionId}/permission`, {
    method: "PATCH",
    body: JSON.stringify({ permission }),
  });
}

export function listPermissions(): Promise<{ tiers: PermissionTier[] }> {
  return request("/permissions");
}

export function listSkillsApi(): Promise<{
  skills: Array<{ name: string; description: string }>;
  count: number;
}> {
  return request("/skills");
}

export function setSessionModel(
  sessionId: string,
  model: string,
): Promise<SessionDetail> {
  return request(`/sessions/${sessionId}/model`, {
    method: "PATCH",
    body: JSON.stringify({ model }),
  });
}

export function messagesFromSession(session: SessionDetail) {
  return session.messages
    .filter(
      (m): m is { role: "user" | "assistant"; content: string } =>
        (m.role === "user" || m.role === "assistant") &&
        typeof m.content === "string" &&
        m.content.length > 0,
    )
    .map((m) => ({ role: m.role, content: m.content }));
}

export function submitConfirmation(
  sessionId: string,
  confirmationId: string,
  allowed: boolean,
): Promise<{ ok: boolean }> {
  return request("/chat/confirm", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      confirmation_id: confirmationId,
      allowed,
    }),
  });
}

export interface AdminUserSummary {
  id: string;
  email: string;
  role: string;
  status: string;
  created_at?: string | null;
  last_login_at?: string | null;
  has_api_key: boolean;
  session_count: number;
  workspace_dir?: string | null;
  projects_dir?: string | null;
  db_path?: string | null;
}

export interface AdminActivityEvent {
  time?: string;
  user_id?: string;
  event: string;
  content?: string;
  tool?: string;
  args?: Record<string, unknown>;
  preview?: string;
  message?: string;
}

export function fetchAdminUsers(): Promise<{ users: AdminUserSummary[]; total: number }> {
  return request("/admin/users");
}

export function fetchAdminStats(): Promise<{
  total_users: number;
  active_users: number;
  banned_users: number;
  with_api_key: number;
}> {
  return request("/admin/stats");
}

export function fetchAdminUserDetail(userId: string): Promise<{
  user: AdminUserSummary;
  sessions: Array<{ id: string; title: string; updated_at?: string }>;
  recent_questions: Array<{ time?: string; content: string }>;
}> {
  return request(`/admin/users/${userId}`);
}

export function setAdminUserStatus(
  userId: string,
  status: "active" | "banned",
): Promise<{ ok: boolean; user: AdminUserSummary }> {
  return request(`/admin/users/${userId}/status`, {
    method: "POST",
    body: JSON.stringify({ status }),
  });
}

export function fetchAdminActivity(params?: {
  date?: string;
  user_id?: string;
  limit?: number;
  event?: string;
}): Promise<{ date: string; events: AdminActivityEvent[]; total: number }> {
  const qs = new URLSearchParams();
  if (params?.date) qs.set("date", params.date);
  if (params?.user_id) qs.set("user_id", params.user_id);
  if (params?.limit) qs.set("limit", String(params.limit));
  if (params?.event) qs.set("event", params.event);
  const q = qs.toString();
  return request(`/admin/activity${q ? `?${q}` : ""}`);
}

export interface WorkspaceEntry {
  path: string;
  name: string;
  type: string;
  size?: number;
}

export interface WorkspaceInfo {
  root: string;
  projects_dir: string;
  file_count: number;
  total_bytes: number;
  total_size: string;
  largest_file?: string | null;
  mode?: string;
  sandbox_path?: string | null;
  local_path?: string | null;
  local_folder_enabled?: boolean;
  quota_bytes?: number | null;
  quota_size?: string | null;
  quota_remaining_bytes?: number | null;
  quota_remaining_size?: string | null;
  quota_percent_used?: number | null;
}

export interface WorkspaceBinding {
  mode: string;
  root: string;
  sandbox_path: string;
  local_path?: string | null;
  local_folder_enabled: boolean;
}

export function fetchWorkspaceBinding(): Promise<WorkspaceBinding> {
  return request("/workspace/binding");
}

export function openWorkspaceFolder(path: string): Promise<WorkspaceBinding> {
  return request("/workspace/open-folder", {
    method: "POST",
    body: JSON.stringify({ path }),
  });
}

export function resetWorkspaceFolder(): Promise<WorkspaceBinding> {
  return request("/workspace/reset-folder", { method: "POST" });
}

export function fetchWorkspaceInfo(): Promise<WorkspaceInfo> {
  return request("/workspace");
}

export function fetchWorkspaceFiles(path = "."): Promise<{
  path: string;
  entries: WorkspaceEntry[];
  count: number;
  truncated: boolean;
}> {
  const qs = new URLSearchParams({ path });
  return request(`/workspace/files?${qs.toString()}`);
}

export function fetchWorkspaceFile(path: string): Promise<{
  path: string;
  content: string;
  truncated: boolean;
}> {
  const qs = new URLSearchParams({ path });
  return request(`/workspace/file?${qs.toString()}`);
}

export interface McpStatusItem {
  id: string;
  name: string;
  configured: boolean;
  connected?: boolean;
  message?: string;
}

export function fetchMcpStatus(ping = false): Promise<{
  services: McpStatusItem[];
  any_configured_external?: boolean;
  ping_performed?: boolean;
  hint?: string;
}> {
  return request(`/mcp/status?ping=${ping ? "true" : "false"}`);
}
