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
