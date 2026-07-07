const CURRENT_SESSION_KEY = "sheldon_current_session_id";

function scopedKey(userId: string): string {
  return `${CURRENT_SESSION_KEY}:${userId}`;
}

export function saveCurrentSessionId(id: string, userId: string): void {
  try {
    localStorage.setItem(scopedKey(userId), id);
  } catch {
    /* private mode / quota */
  }
}

export function loadCurrentSessionId(userId: string): string | null {
  try {
    const scoped = localStorage.getItem(scopedKey(userId));
    if (scoped) return scoped;
    const legacy = localStorage.getItem(CURRENT_SESSION_KEY);
    if (legacy) {
      localStorage.setItem(scopedKey(userId), legacy);
      localStorage.removeItem(CURRENT_SESSION_KEY);
      return legacy;
    }
    return null;
  } catch {
    return null;
  }
}

export function clearCurrentSessionId(userId?: string): void {
  try {
    if (userId) {
      localStorage.removeItem(scopedKey(userId));
    }
    localStorage.removeItem(CURRENT_SESSION_KEY);
  } catch {
    /* ignore */
  }
}
