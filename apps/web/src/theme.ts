/** 主题：Cursor 深色 · gallery-airy 浅色 · 跟随系统 */

export type ThemeMode = "dark" | "light" | "system";
export type ResolvedTheme = "dark" | "light";

const STORAGE_KEY = "sheldon-agent-theme";

export function loadStoredTheme(): ThemeMode {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === "dark" || v === "light" || v === "system") return v;
  } catch {
    /* private mode */
  }
  return "dark";
}

export function saveTheme(mode: ThemeMode): void {
  try {
    localStorage.setItem(STORAGE_KEY, mode);
  } catch {
    /* ignore */
  }
}

export function resolveTheme(mode: ThemeMode): ResolvedTheme {
  if (mode === "system") {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  return mode;
}

export function applyTheme(mode: ThemeMode): ResolvedTheme {
  const resolved = resolveTheme(mode);
  document.documentElement.setAttribute("data-theme", resolved);
  document.documentElement.style.colorScheme = resolved;

  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) {
    meta.setAttribute("content", resolved === "dark" ? "#1e1e1e" : "#f9fafb");
  }
  return resolved;
}

export function themeModeLabel(mode: ThemeMode): string {
  if (mode === "dark") return "深色";
  if (mode === "light") return "浅色";
  return "跟随系统";
}

export function nextThemeMode(current: ThemeMode): ThemeMode {
  if (current === "dark") return "light";
  if (current === "light") return "system";
  return "dark";
}
