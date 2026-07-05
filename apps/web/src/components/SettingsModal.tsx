import { useEffect, useState } from "react";
import {
  deleteUserApiKey,
  fetchApiKeyStatus,
  saveUserApiKey,
  type ApiKeyStatus,
} from "../api/client";
import "./SettingsModal.css";

interface Props {
  open: boolean;
  onClose: () => void;
  userRole: string;
  onUpdated: (status: ApiKeyStatus) => void;
}

export function SettingsModal({ open, onClose, userRole, onUpdated }: Props) {
  const [status, setStatus] = useState<ApiKeyStatus | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setError(null);
    void fetchApiKeyStatus()
      .then((s) => {
        setStatus(s);
        onUpdated(s);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "加载失败");
      })
      .finally(() => setLoading(false));
  }, [open, onUpdated]);

  if (!open) return null;

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const next = await saveUserApiKey(apiKey);
      setStatus(next);
      setApiKey("");
      onUpdated(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    setSubmitting(true);
    setError(null);
    try {
      const next = await deleteUserApiKey();
      setStatus(next);
      onUpdated(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="settings-overlay" onClick={onClose} role="presentation">
      <div
        className="settings-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-labelledby="settings-title"
      >
        <div className="settings-header">
          <h2 id="settings-title">API Key 设置</h2>
          <button type="button" className="settings-close" onClick={onClose} aria-label="关闭">
            ×
          </button>
        </div>

        {userRole === "admin" && (
          <p className="settings-note">
            管理员默认使用服务器平台 Key；也可在此保存个人 Key 作为备用。
          </p>
        )}

        {userRole !== "admin" && (
          <p className="settings-note">
            请填写你在阿里云百炼控制台的 DashScope API Key。Key 加密存储，界面不会显示完整内容。
          </p>
        )}

        {loading && <div className="settings-muted">加载中…</div>}

        {!loading && status && (
          <div className="settings-status">
            状态：{status.configured ? "已配置" : "未配置"}
            {status.hint ? ` · ${status.hint}` : ""}
            {status.uses_platform_key ? " · 平台 Key" : ""}
          </div>
        )}

        <form className="settings-form" onSubmit={(e) => void handleSave(e)}>
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
          {error && <div className="settings-error">{error}</div>}
          <div className="settings-actions">
            <button type="submit" disabled={submitting || apiKey.length < 8}>
              {submitting ? "保存中…" : "保存 Key"}
            </button>
            {status?.configured && !status.uses_platform_key && (
              <button
                type="button"
                className="settings-danger"
                disabled={submitting}
                onClick={() => void handleDelete()}
              >
                删除 Key
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
