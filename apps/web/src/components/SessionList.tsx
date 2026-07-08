import { useEffect, useRef, useState } from "react";
import type { SessionSummary } from "../types";
import { WorkspacePanel } from "./WorkspacePanel";
import { SplitHandle } from "./SplitHandle";
import { useSplitPane } from "../useSplitPane";

interface Props {
  sessions: SessionSummary[];
  currentId: string | null;
  loading: boolean;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onDelete: (id: string) => void;
  onRename: (id: string, title: string) => void;
  workspaceRefreshToken: number;
  workspaceHighlightPath?: string | null;
  onWorkspaceUploadSuccess?: (
    result: import("../api/client").WorkspaceUploadResult,
  ) => void;
}

function PlusIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2v10z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function SessionList({
  sessions,
  currentId,
  loading,
  onSelect,
  onCreate,
  onDelete,
  onRename,
  workspaceRefreshToken,
  workspaceHighlightPath,
  onWorkspaceUploadSuccess,
}: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const { containerRef: sidebarBodyRef, size: workspaceHeight, startDrag } =
    useSplitPane({
      storageKey: "sheldon_sidebar_workspace_h",
      defaultSize: 380,
      minSize: 160,
      maxRatio: 0.78,
    });

  useEffect(() => {
    if (editingId) inputRef.current?.focus();
  }, [editingId]);

  function startEdit(s: SessionSummary, e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (loading) return;
    setEditingId(s.id);
    setEditTitle(s.title);
  }

  function cancelEdit() {
    setEditingId(null);
    setEditTitle("");
  }

  function commitEdit(sessionId: string) {
    const title = editTitle.trim();
    cancelEdit();
    if (!title) return;
    onRename(sessionId, title);
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="brand-mark">S</span>
        <span className="brand-text">烁士生</span>
      </div>

      <button
        type="button"
        className="sidebar-new-chat"
        onClick={onCreate}
        disabled={loading}
      >
        <PlusIcon />
        <span>新对话</span>
      </button>

      <div className="sidebar-section-label">历史</div>

      <div className="sidebar-body" ref={sidebarBodyRef}>
        <ul className="sidebar-chats">
          {sessions.map((s) => (
            <li
              key={s.id}
              className={s.id === currentId ? "chat-row active" : "chat-row"}
            >
              {editingId === s.id ? (
                <input
                  ref={inputRef}
                  className="chat-row-edit"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") commitEdit(s.id);
                    if (e.key === "Escape") cancelEdit();
                  }}
                  onBlur={() => commitEdit(s.id)}
                />
              ) : (
                <button
                  type="button"
                  className="chat-row-btn"
                  onClick={() => onSelect(s.id)}
                  title={`${s.title}（双击重命名）`}
                >
                  <ChatIcon />
                  <span
                    className="chat-row-title"
                    onDoubleClick={(e) => startEdit(s, e)}
                  >
                    {s.title}
                  </span>
                </button>
              )}
              <button
                type="button"
                className="chat-row-delete"
                onClick={() => onDelete(s.id)}
                disabled={loading}
                title="删除"
              >
                ×
              </button>
            </li>
          ))}
        </ul>

        <SplitHandle
          onPointerDown={startDrag}
          label="拖动调整工作区高度"
        />

        <div
          className="sidebar-workspace"
          style={{ height: workspaceHeight }}
        >
          <div className="sidebar-section-label sidebar-section-label-inline">
            工作区
          </div>
          <WorkspacePanel
            refreshToken={workspaceRefreshToken}
            highlightPath={workspaceHighlightPath}
            onUploadSuccess={onWorkspaceUploadSuccess}
          />
        </div>
      </div>
    </aside>
  );
}
