import { useState } from "react";
import { API_BASE } from "../config";
import type { AuthTokenResponse, AuthUser } from "../auth";
import { setAuth } from "../auth";
import "./LoginPage.css";

interface Props {
  onSuccess: (user: AuthUser) => void;
}

export function LoginPage({ onSuccess }: Props) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const path = mode === "login" ? "/auth/login" : "/auth/register";
      const res = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const text = await res.text();
      if (!res.ok) {
        let detail = text;
        try {
          const parsed = JSON.parse(text) as { detail?: string };
          if (parsed.detail) detail = parsed.detail;
        } catch {
          /* keep raw text */
        }
        throw new Error(detail || `HTTP ${res.status}`);
      }
      const data = JSON.parse(text) as AuthTokenResponse;
      setAuth(data.access_token, data.user);
      onSuccess(data.user);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "登录失败";
      if (/failed to fetch|networkerror|load failed/i.test(msg)) {
        setError("无法连接服务器，请检查网络或稍后重试");
      } else {
        setError(msg);
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-shell">
      <div className="login-card">
        <div className="login-brand">
          <h1>烁士生</h1>
          <p>请先登录或注册，再进入你的专属工作区</p>
        </div>

        <div className="login-tabs">
          <button
            type="button"
            className={mode === "login" ? "active" : ""}
            onClick={() => setMode("login")}
          >
            登录
          </button>
          <button
            type="button"
            className={mode === "register" ? "active" : ""}
            onClick={() => setMode("register")}
          >
            注册
          </button>
        </div>

        <form className="login-form" onSubmit={(e) => void handleSubmit(e)}>
          <label>
            <span>邮箱</span>
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
            />
          </label>
          <label>
            <span>密码</span>
            <input
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={mode === "register" ? "至少 8 位" : "请输入密码"}
              minLength={mode === "register" ? 8 : 1}
              required
            />
          </label>

          {error && <div className="login-error">{error}</div>}

          <button type="submit" className="login-submit" disabled={submitting}>
            {submitting ? "请稍候…" : mode === "login" ? "登录" : "注册并登录"}
          </button>
        </form>
      </div>
    </div>
  );
}
