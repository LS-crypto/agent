import { useEffect, useState } from "react";
import {
  deleteUserApiKey,
  fetchApiKeyStatus,
  fetchProfile,
  saveUserApiKey,
  updateProfile,
  type ApiKeyStatus,
} from "../api/client";
import type { AuthUser } from "../auth";
import { ThemeToggle } from "./ThemeToggle";
import type { ThemeMode } from "../theme";
import "./SettingsModal.css";

const AVATAR_PRESETS = ["🦊", "🤖", "👨‍💻", "👩‍💻", "🐱", "🐶", "🌟", "🔥", "💎", "🎯", "🚀", "🌈"];

interface Props {
  open: boolean;
  onClose: () => void;
  user: AuthUser;
  userRole: string;
  themeMode: ThemeMode;
  onThemeChange: (mode: ThemeMode) => void;
  onLogout: () => void;
  onApiKeyUpdated: (status: ApiKeyStatus) => void;
  onProfileUpdated: (user: AuthUser) => void;
}

type Tab = "profile" | "apikey" | "appearance";

export function SettingsModal({
  open,
  onClose,
  user,
  userRole,
  themeMode,
  onThemeChange,
  onLogout,
  onApiKeyUpdated,
  onProfileUpdated,
}: Props) {
  const [tab, setTab] = useState<Tab>("profile");
  const [status, setStatus] = useState<ApiKeyStatus | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [displayName, setDisplayName] = useState(user.display_name ?? "");
  const [avatar, setAvatar] = useState(user.avatar ?? "🦊");
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setTab("profile");
    setDisplayName(user.display_name ?? "");
    setAvatar(user.avatar ?? "🦊");
    setLoading(true);
    setError(null);
    void Promise.all([fetchProfile(), fetchApiKeyStatus()])
      .then(([profile, keyStatus]) => {
        setDisplayName(profile.display_name ?? "");
        setAvatar(profile.avatar ?? "🦊");
        onProfileUpdated({ ...user, ...profile });
        setStatus(keyStatus);
        onApiKeyUpdated(keyStatus);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "加载失败");
      })
      .finally(() => setLoading(false));
  }, [open, user.id]);

  if (!open) return null;

  async function handleSaveProfile(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const updated = await updateProfile({
        display_name: displayName.trim(),
        avatar,
      });
      onProfileUpdated({ ...user, ...updated });
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSaveKey(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const next = await saveUserApiKey(apiKey);
      setStatus(next);
      setApiKey("");
      onApiKeyUpdated(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDeleteKey() {
    setSubmitting(true);
    setError(null);
    try {
      const next = await deleteUserApiKey();
      setStatus(next);
      onApiKeyUpdated(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除失败");
    } finally {
      setSubmitting(false);
    }
  }

  function handleLogoutClick() {
    onClose();
    onLogout();
  }

  const showName = displayName.trim() || user.email.split("@")[0];

  return (
    <div className="settings-overlay" onClick={onClose} role="presentation">
      <div
        className="settings-modal settings-modal-wide"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-labelledby="settings-title"
      >
        <div className="settings-header">
          <div className="settings-header-user">
            <span className="settings-avatar-lg" aria-hidden>
              {avatar}
            </span>
            <div>
              <h2 id="settings-title">设置</h2>
              <p className="settings-subtitle">{showName}</p>
            </div>
          </div>
          <button type="button" className="settings-close" onClick={onClose} aria-label="关闭">
            ×
          </button>
        </div>

        <div className="settings-tabs">
          <button
            type="button"
            className={tab === "profile" ? "active" : ""}
            onClick={() => setTab("profile")}
          >
            个人资料
          </button>
          <button
            type="button"
            className={tab === "appearance" ? "active" : ""}
            onClick={() => setTab("appearance")}
          >
            外观
          </button>
          <button
            type="button"
            className={tab === "apikey" ? "active" : ""}
            onClick={() => setTab("apikey")}
          >
            API Key
          </button>
        </div>

        {loading && <div className="settings-muted">加载中…</div>}
        {error && <div className="settings-error">{error}</div>}

        {tab === "profile" && !loading && (
          <form className="settings-form" onSubmit={(e) => void handleSaveProfile(e)}>
            <label>
              <span>显示名称</span>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="在界面中显示的名字"
                minLength={2}
                maxLength={32}
              />
            </label>
            <p className="settings-hint">
              账号 ID（系统内部标识，不可修改）：<code>{user.id}</code>
            </p>
            <div className="settings-field">
              <span className="settings-label">头像</span>
              <div className="settings-avatar-grid">
                {AVATAR_PRESETS.map((em) => (
                  <button
                    key={em}
                    type="button"
                    className={avatar === em ? "settings-avatar-opt active" : "settings-avatar-opt"}
                    onClick={() => setAvatar(em)}
                    aria-label={`头像 ${em}`}
                  >
                    {em}
                  </button>
                ))}
              </div>
            </div>
            <div className="settings-actions">
              <button type="submit" disabled={submitting || displayName.trim().length < 2}>
                {submitting ? "保存中…" : "保存资料"}
              </button>
            </div>
          </form>
        )}

        {tab === "appearance" && (
          <div className="settings-section">
            <p className="settings-note">选择界面主题，立即生效。</p>
            <ThemeToggle mode={themeMode} onChange={onThemeChange} />
          </div>
        )}

        {tab === "apikey" && !loading && (
          <>
            {userRole === "admin" && (
              <p className="settings-note">
                管理员默认使用服务器平台 Key；也可在此保存个人 Key 作为备用。
              </p>
            )}
            {userRole !== "admin" && (
              <p className="settings-note">
                请填写阿里云百炼 DashScope API Key。Key 加密存储，界面不会显示完整内容。
              </p>
            )}
            {status && (
              <div className="settings-status">
                状态：{status.configured ? "已配置" : "未配置"}
                {status.hint ? ` · ${status.hint}` : ""}
                {status.uses_platform_key ? " · 平台 Key" : ""}
              </div>
            )}
            <form className="settings-form" onSubmit={(e) => void handleSaveKey(e)}>
              <label>
                <span>DashScope API Key</span>
                <input
                  type="password"
                  autoComplete="off"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="sk-..."
                  minLength={8}
                />
              </label>
              <div className="settings-actions">
                <button type="submit" disabled={submitting || apiKey.length < 8}>
                  {submitting ? "保存中…" : "保存 Key"}
                </button>
                {status?.configured && !status.uses_platform_key && (
                  <button
                    type="button"
                    className="settings-danger"
                    disabled={submitting}
                    onClick={() => void handleDeleteKey()}
                  >
                    删除 Key
                  </button>
                )}
              </div>
            </form>
          </>
        )}

        <div className="settings-footer">
          <button type="button" className="settings-logout" onClick={handleLogoutClick}>
            退出登录
          </button>
        </div>
      </div>
    </div>
  );
}
