import { useEffect, useState } from "react";
import type { SessionSummary } from "../types";
import {
  listArchivedSessions,
  permanentDeleteSession,
  restoreSession,
} from "../api/client";

interface Props {
  open: boolean;
  onClose: () => void;
  onRestored: (sessionId: string) => void;
  showToast: (msg: string) => void;
  setError: (msg: string | null) => void;
}

export function ArchivedSessionsModal({
  open,
  onClose,
  onRestored,
  showToast,
  setError,
}: Props) {
  const [items, setItems] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    listArchivedSessions()
      .then((rows) => setItems(rows))
      .catch((e) => setError(e instanceof Error ? e.message : "加载历史失败"))
      .finally(() => setLoading(false));
  }, [open, setError]);

  if (!open) return null;

  async function handleRestore(id: string) {
    setBusyId(id);
    try {
      await restoreSession(id);
      showToast("会话已恢复");
      setItems((prev) => prev.filter((s) => s.id !== id));
      onRestored(id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "恢复失败");
    } finally {
      setBusyId(null);
    }
  }

  async function handlePermanent(id: string, title: string) {
    if (!window.confirm(`彻底删除「${title}」？此操作不可撤销。`)) return;
    setBusyId(id);
    try {
      await permanentDeleteSession(id);
      showToast("已彻底删除");
      setItems((prev) => prev.filter((s) => s.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-panel archived-modal"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <h3>历史会话</h3>
          <button
            type="button"
            className="modal-close"
            onClick={onClose}
            aria-label="关闭"
          >
            ×
          </button>
        </div>

        <div className="modal-body">
          {loading ? (
            <div className="empty-hint">加载中…</div>
          ) : items.length === 0 ? (
            <div className="empty-hint">暂无归档的会话</div>
          ) : (
            <ul className="archived-list">
              {items.map((s) => (
                <li key={s.id} className="archived-row">
                  <div className="archived-meta">
                    <div className="archived-title">{s.title}</div>
                    <div className="archived-sub">
                      归档于 {formatTime(s.archived_at)}
                    </div>
                  </div>
                  <div className="archived-actions">
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={() => handleRestore(s.id)}
                      disabled={busyId === s.id}
                      title="恢复到侧栏"
                    >
                      ↺ 恢复
                    </button>
                    <button
                      type="button"
                      className="btn btn-danger btn-sm"
                      onClick={() => handlePermanent(s.id, s.title)}
                      disabled={busyId === s.id}
                      title="彻底删除（不可恢复）"
                    >
                      × 彻底删
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="modal-footer">
          <span className="modal-footer-hint">
            归档 = 软删除，可在侧栏隐藏后恢复；彻底删 = 不可恢复。
          </span>
        </div>
      </div>
    </div>
  );
}

function formatTime(iso?: string | null): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString("zh-CN", { hour12: false });
  } catch {
    return iso;
  }
}