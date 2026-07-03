import type { ThemeMode } from "../theme";
import { themeModeLabel } from "../theme";

interface Props {
  mode: ThemeMode;
  onChange: (mode: ThemeMode) => void;
}

function SunIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.6" />
      <path
        d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M20 14.5A8.5 8.5 0 0110.5 5 7 7 0 1020 14.5z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function SystemIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect x="3" y="4" width="18" height="12" rx="2" stroke="currentColor" strokeWidth="1.6" />
      <path d="M8 20h8M12 16v4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

const MODES: ThemeMode[] = ["dark", "light", "system"];

export function ThemeToggle({ mode, onChange }: Props) {
  return (
    <div className="theme-toggle" role="group" aria-label="界面主题">
      {MODES.map((m) => (
        <button
          key={m}
          type="button"
          className={mode === m ? "theme-toggle-btn active" : "theme-toggle-btn"}
          onClick={() => onChange(m)}
          title={themeModeLabel(m)}
          aria-pressed={mode === m}
        >
          {m === "dark" && <MoonIcon />}
          {m === "light" && <SunIcon />}
          {m === "system" && <SystemIcon />}
          <span className="theme-toggle-label">{themeModeLabel(m)}</span>
        </button>
      ))}
    </div>
  );
}
