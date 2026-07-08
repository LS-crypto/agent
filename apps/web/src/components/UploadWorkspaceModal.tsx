import { useEffect, useRef, useState } from "react";
import {
  uploadWorkspace,
  type WorkspaceInfo,
  type WorkspaceUploadResult,
} from "../api/client";
import "./UploadWorkspaceModal.css";

const MAX_ZIP_BYTES = 50 * 1024 * 1024;

type UploadMode = "merge" | "subdir" | "replace";

interface Props {
  open: boolean;
  onClose: () => void;
  workspaceInfo: WorkspaceInfo | null;
  onSuccess: (result: WorkspaceUploadResult) => void;
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function UploadWorkspaceModal({
  open,
  onClose,
  workspaceInfo,
  onSuccess,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<UploadMode>("merge");
  const [targetDir, setTargetDir] = useState("");
  const [stripRoot, setStripRoot] = useState(true);
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState<"idle" | "uploading" | "processing">("idle");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => {
    if (!open) {
      setFile(null);
      setMode("merge");
      setTargetDir("");
      setStripRoot(true);
      setBusy(false);
      setPhase("idle");
      setProgress(0);
      setError(null);
      setDragOver(false);
    }
  }, [open]);

  if (!open) return null;

  function validateSelected(next: File): string | null {
    if (!next.name.toLowerCase().endsWith(".zip")) {
      return "请选择 .zip 文件（可先将文件夹压缩为 zip）";
    }
    if (next.size > MAX_ZIP_BYTES) {
      return `文件过大（${formatBytes(next.size)}），上限 ${formatBytes(MAX_ZIP_BYTES)}`;
    }
    if (
      workspaceInfo?.quota_remaining_bytes != null &&
      next.size > workspaceInfo.quota_remaining_bytes
    ) {
      return `可能超出配额（剩余 ${workspaceInfo.quota_remaining_size ?? "—"}）`;
    }
    return null;
  }

  function pickFile(next: File | null) {
    if (!next) return;
    const msg = validateSelected(next);
    if (msg) {
      setError(msg);
      setFile(null);
      return;
    }
    setError(null);
    setFile(next);
  }

  async function handleSubmit() {
    if (!file || busy) return;
    if (mode === "replace") {
      const ok = window.confirm(
        "将清空云端工作区内的所有文件后再导入，此操作不可撤销。继续？",
      );
      if (!ok) return;
    }
    if (mode === "subdir" && !targetDir.trim()) {
      setError("请填写子目录名称");
      return;
    }

    setBusy(true);
    setError(null);
    setPhase("uploading");
    setProgress(0);

    try {
      const result = await uploadWorkspace(file, {
        mode,
        targetDir: mode === "subdir" ? targetDir.trim() : undefined,
        stripRoot,
        onProgress: (pct) => {
          setProgress(pct);
          if (pct >= 100) setPhase("processing");
        },
      });
      onSuccess(result);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "上传失败");
      setPhase("idle");
      setProgress(0);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="upload-overlay" role="dialog" aria-modal="true">
      <div className="upload-dialog">
        <header className="upload-header">
          <h3>上传项目到云端工作区</h3>
          <button
            type="button"
            className="upload-close"
            onClick={onClose}
            disabled={busy}
            aria-label="关闭"
          >
            ×
          </button>
        </header>

        <p className="upload-hint">
          {workspaceInfo?.local_folder_enabled
            ? "将 zip 导入云端沙箱；本机「打开文件夹」仅适用于本地/桌面版。"
            : "远程服务无法访问你电脑上的文件夹，请上传 zip 作为工作区（也可让 Agent git clone）。"}
        </p>

        {workspaceInfo?.quota_size && (
          <p className="upload-quota">
            配额：已用 {workspaceInfo.total_size} / {workspaceInfo.quota_size}
            {workspaceInfo.quota_remaining_size
              ? ` · 剩余 ${workspaceInfo.quota_remaining_size}`
              : null}
          </p>
        )}

        <div
          className={dragOver ? "upload-drop upload-drop-active" : "upload-drop"}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            const dropped = e.dataTransfer.files[0];
            if (dropped) pickFile(dropped);
          }}
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
          }}
          role="button"
          tabIndex={0}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".zip,application/zip"
            hidden
            onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
          />
          {file ? (
            <span>
              已选：<strong>{file.name}</strong> · {formatBytes(file.size)}
            </span>
          ) : (
            <span>拖放 zip 到此处，或点击选择文件</span>
          )}
        </div>

        <fieldset className="upload-fieldset" disabled={busy}>
          <legend>解压方式</legend>
          <label className="upload-radio">
            <input
              type="radio"
              name="upload-mode"
              checked={mode === "merge"}
              onChange={() => setMode("merge")}
            />
            合并到工作区根目录
          </label>
          <label className="upload-radio">
            <input
              type="radio"
              name="upload-mode"
              checked={mode === "subdir"}
              onChange={() => setMode("subdir")}
            />
            解压到子目录
            {mode === "subdir" && (
              <input
                type="text"
                className="upload-subdir-input"
                placeholder="例如 my-app"
                value={targetDir}
                onChange={(e) => setTargetDir(e.target.value)}
                spellCheck={false}
              />
            )}
          </label>
          <label className="upload-radio upload-radio-danger">
            <input
              type="radio"
              name="upload-mode"
              checked={mode === "replace"}
              onChange={() => setMode("replace")}
            />
            清空工作区后导入
          </label>
          <label className="upload-check">
            <input
              type="checkbox"
              checked={stripRoot}
              onChange={(e) => setStripRoot(e.target.checked)}
            />
            若 zip 只有一层根文件夹，自动展开内容
          </label>
        </fieldset>

        {busy && (
          <div className="upload-progress" aria-live="polite">
            <div className="upload-progress-bar">
              <div
                className="upload-progress-fill"
                style={{ width: `${Math.max(progress, phase === "processing" ? 100 : 0)}%` }}
              />
            </div>
            <span>
              {phase === "processing"
                ? "正在解压并写入工作区…"
                : `正在上传… ${progress}%`}
            </span>
          </div>
        )}

        {error && (
          <p className="upload-error" role="alert">
            {error}
          </p>
        )}

        <footer className="upload-footer">
          <button type="button" className="upload-btn-secondary" onClick={onClose} disabled={busy}>
            取消
          </button>
          <button
            type="button"
            className="upload-btn-primary"
            onClick={() => void handleSubmit()}
            disabled={!file || busy}
          >
            开始上传
          </button>
        </footer>
      </div>
    </div>
  );
}
