import type { ChatRequest, SseEvent } from "../types";
import { getAuthHeaders, onUnauthorized } from "../auth";
import { API_BASE } from "../config";

export async function streamChat(
  body: ChatRequest,
  onEvent: (event: SseEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(body),
    signal,
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

  if (!res.body) {
    throw new Error("响应体为空");
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
      onEvent(JSON.parse(line.slice(6)) as SseEvent);
    }
  }
}
