const CURRENT_SESSION_KEY = "sheldon_current_session_id";

export function saveCurrentSessionId(id: string): void {
  try {
    localStorage.setItem(CURRENT_SESSION_KEY, id);
  } catch {
    /* private mode / quota */
  }
}

export function loadCurrentSessionId(): string | null {
  try {
    return localStorage.getItem(CURRENT_SESSION_KEY);
  } catch {
    return null;
  }
}

export function clearCurrentSessionId(): void {
  try {
    localStorage.removeItem(CURRENT_SESSION_KEY);
  } catch {
    /* ignore */
  }
}
