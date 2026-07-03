import type { ModelsResponse, PermissionTier, SessionDetail, SessionSummary } from "../types";
import { USER_ID } from "../types";
import { API_BASE, HEALTH_URL } from "../config";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
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

export function listSessions(): Promise<SessionSummary[]> {
  return request(`/sessions?user_id=${encodeURIComponent(USER_ID)}`);
}

export function createSession(title = "新会话", model = "auto"): Promise<SessionDetail> {
  return request("/sessions", {
    method: "POST",
    body: JSON.stringify({ user_id: USER_ID, title, model }),
  });
}

export function getSession(sessionId: string): Promise<SessionDetail> {
  return request(
    `/sessions/${sessionId}?user_id=${encodeURIComponent(USER_ID)}`,
  );
}

export function deleteSession(sessionId: string): Promise<void> {
  return request(`/sessions/${sessionId}?user_id=${encodeURIComponent(USER_ID)}`, {
    method: "DELETE",
  });
}

export function resetSession(sessionId: string): Promise<SessionDetail> {
  return request(
    `/sessions/${sessionId}/reset?user_id=${encodeURIComponent(USER_ID)}`,
    { method: "POST" },
  );
}

export function renameSession(
  sessionId: string,
  title: string,
): Promise<SessionDetail> {
  return request(
    `/sessions/${sessionId}?user_id=${encodeURIComponent(USER_ID)}`,
    {
      method: "PATCH",
      body: JSON.stringify({ title }),
    },
  );
}

export function listModels(checkRemote = true): Promise<ModelsResponse> {
  return request(`/models?check_remote=${checkRemote ? "true" : "false"}`);
}

export function setSessionPermission(
  sessionId: string,
  permission: string,
): Promise<SessionDetail> {
  return request(
    `/sessions/${sessionId}/permission?user_id=${encodeURIComponent(USER_ID)}`,
    {
      method: "PATCH",
      body: JSON.stringify({ permission }),
    },
  );
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
  return request(
    `/sessions/${sessionId}/model?user_id=${encodeURIComponent(USER_ID)}`,
    {
      method: "PATCH",
      body: JSON.stringify({ model }),
    },
  );
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
      user_id: USER_ID,
      session_id: sessionId,
      confirmation_id: confirmationId,
      allowed,
    }),
  });
}
