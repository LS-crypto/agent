import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchWorkspaceFile,
  fetchWorkspaceFiles,
  fetchWorkspaceInfo,
  openWorkspaceFolder,
  resetWorkspaceFolder,
  type WorkspaceEntry,
  type WorkspaceInfo,
  type WorkspaceUploadResult,
} from "../api/client";
import { SplitHandle } from "./SplitHandle";
import { UploadWorkspaceModal } from "./UploadWorkspaceModal";
import { useSplitPane } from "../useSplitPane";

interface Props {
  refreshToken: number;
  highlightPath?: string | null;
  onSelectPath?: (path: string) => void;
  onUploadSuccess?: (result: WorkspaceUploadResult) => void;
}

interface TreeNode {
  name: string;
  path: string;
  type: "file" | "dir";
  size?: number;
  children: TreeNode[];
}

function buildTree(entries: WorkspaceEntry[]): TreeNode[] {
  const nodes = new Map<string, TreeNode>();

  const getOrCreateDir = (path: string): TreeNode => {
    const key = path || ".";
    const existing = nodes.get(key);
    if (existing) return existing;
    const name = key === "." ? "root" : key.split("/").pop() ?? key;
    const node: TreeNode = { name, path: key, type: "dir", children: [] };
    nodes.set(key, node);
    if (key !== ".") {
      const parentPath = key.includes("/") ? key.slice(0, key.lastIndexOf("/")) : ".";
      const parent = getOrCreateDir(parentPath);
      if (!parent.children.some((c) => c.path === key)) {
        parent.children.push(node);
      }
    }
    return node;
  };

  getOrCreateDir(".");

  for (const entry of entries) {
    if (entry.type === "dir") {
      getOrCreateDir(entry.path);
      continue;
    }
    const slash = entry.path.lastIndexOf("/");
    const parentPath = slash === -1 ? "." : entry.path.slice(0, slash);
    const parent = getOrCreateDir(parentPath);
    if (!parent.children.some((c) => c.path === entry.path)) {
      parent.children.push({
        name: entry.name,
        path: entry.path,
        type: "file",
        size: entry.size,
        children: [],
      });
    }
  }

  const root = nodes.get(".")!;
  const sortNodes = (list: TreeNode[]) => {
    list.sort((a, b) => {
      if (a.type !== b.type) return a.type === "dir" ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
    for (const n of list) {
      if (n.children.length) sortNodes(n.children);
    }
  };
  sortNodes(root.children);
  return root.children;
}

function FileIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path d="M14 2v6h6" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}

function FolderIcon({ open }: { open: boolean }) {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      {open ? (
        <path
          d="M3 7a2 2 0 012-2h5l2 2h9a1 1 0 011 1v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
      ) : (
        <path
          d="M3 7a2 2 0 012-2h5l2 2h9a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
      )}
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M6 6l12 12M18 6L6 18"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function TreeRow({
  node,
  depth,
  expanded,
  selectedPath,
  highlightPath,
  onToggle,
  onSelect,
}: {
  node: TreeNode;
  depth: number;
  expanded: Set<string>;
  selectedPath: string | null;
  highlightPath?: string | null;
  onToggle: (path: string) => void;
  onSelect: (path: string) => void;
}) {
  const isDir = node.type === "dir";
  const isOpen = isDir && expanded.has(node.path);
  const isSelected = selectedPath === node.path;
  const isHighlight = highlightPath === node.path;

  return (
    <>
      <button
        type="button"
        className={
          isSelected
            ? "ws-tree-row active"
            : isHighlight
              ? "ws-tree-row highlight"
              : "ws-tree-row"
        }
        style={{ paddingLeft: `${8 + depth * 12}px` }}
        onClick={() => {
          if (isDir) {
            onToggle(node.path);
          } else {
            onSelect(node.path);
          }
        }}
        title={node.path}
      >
        {isDir ? <FolderIcon open={isOpen} /> : <FileIcon />}
        <span className="ws-tree-name">{node.name}</span>
      </button>
      {isDir &&
        isOpen &&
        node.children.map((child) => (
          <TreeRow
            key={child.path}
            node={child}
            depth={depth + 1}
            expanded={expanded}
            selectedPath={selectedPath}
            highlightPath={highlightPath}
            onToggle={onToggle}
            onSelect={onSelect}
          />
        ))}
    </>
  );
}

function fileBaseName(path: string): string {
  const slash = path.lastIndexOf("/");
  return slash === -1 ? path : path.slice(slash + 1);
}

function fileExtension(path: string): string | null {
  const base = fileBaseName(path);
  const dot = base.lastIndexOf(".");
  if (dot <= 0) return null;
  return base.slice(dot + 1).toLowerCase();
}

function PreviewSkeleton() {
  return (
    <div className="workspace-preview-skeleton" aria-hidden>
      {Array.from({ length: 6 }, (_, i) => (
        <span
          key={i}
          className="workspace-preview-skeleton-line"
          style={{ width: `${58 + ((i * 17) % 35)}%` }}
        />
      ))}
    </div>
  );
}

export function WorkspacePanel({
  refreshToken,
  highlightPath,
  onSelectPath,
  onUploadSuccess,
}: Props) {
  const [info, setInfo] = useState<WorkspaceInfo | null>(null);
  const [entries, setEntries] = useState<WorkspaceEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set(["."]));
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [previewTruncated, setPreviewTruncated] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [folderInput, setFolderInput] = useState("");
  const [folderOpen, setFolderOpen] = useState(false);
  const [folderBusy, setFolderBusy] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);

  const { containerRef: splitRef, size: previewHeight, startDrag } = useSplitPane({
    storageKey: "sheldon_workspace_preview_h",
    defaultSize: 220,
    minSize: 88,
    maxRatio: 0.82,
  });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [wsInfo, files] = await Promise.all([
        fetchWorkspaceInfo(),
        fetchWorkspaceFiles(),
      ]);
      setInfo(wsInfo);
      setEntries(files.entries);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载工作区失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load, refreshToken]);

  useEffect(() => {
    if (!highlightPath || highlightPath.includes("/")) return;
    setExpanded((prev) => new Set(prev).add("."));
  }, [highlightPath]);

  const loadFilePreview = useCallback(async (path: string) => {
    setPreviewLoading(true);
    setPreview(null);
    try {
      const file = await fetchWorkspaceFile(path);
      setPreview(file.content);
      setPreviewTruncated(file.truncated);
      onSelectPath?.(path);
    } catch (e) {
      setPreview(e instanceof Error ? e.message : "无法读取文件");
      setPreviewTruncated(false);
    } finally {
      setPreviewLoading(false);
    }
  }, [onSelectPath]);

  useEffect(() => {
    if (!highlightPath) return;
    const parts = highlightPath.split("/");
    setExpanded((prev) => {
      const next = new Set(prev);
      next.add(".");
      let acc = "";
      for (let i = 0; i < parts.length - 1; i += 1) {
        acc = acc ? `${acc}/${parts[i]}` : parts[i];
        next.add(acc);
      }
      return next;
    });
    setSelectedPath(highlightPath);
    void loadFilePreview(highlightPath);
  }, [highlightPath, loadFilePreview]);

  const tree = useMemo(() => buildTree(entries), [entries]);
  const previewExt = selectedPath ? fileExtension(selectedPath) : null;
  const previewLines = preview ? preview.split("\n").length : 0;

  function toggleDir(path: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }

  async function handleOpenFolder() {
    const path = folderInput.trim();
    if (!path) return;
    setFolderBusy(true);
    setError(null);
    try {
      await openWorkspaceFolder(path);
      setFolderOpen(false);
      setFolderInput("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "打开文件夹失败");
    } finally {
      setFolderBusy(false);
    }
  }

  async function handleResetFolder() {
    setFolderBusy(true);
    setError(null);
    try {
      await resetWorkspaceFolder();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "恢复沙箱失败");
    } finally {
      setFolderBusy(false);
    }
  }

  function closePreview() {
    setSelectedPath(null);
    setPreview(null);
    setPreviewTruncated(false);
    setPreviewLoading(false);
  }

  async function selectFile(path: string) {
    setSelectedPath(path);
    await loadFilePreview(path);
  }

  async function handleUploadSuccess(result: WorkspaceUploadResult) {
    await load();
    onUploadSuccess?.(result);
  }

  return (
    <div className="workspace-panel">
      <UploadWorkspaceModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        workspaceInfo={info}
        onSuccess={(result) => void handleUploadSuccess(result)}
      />
      <div className="workspace-panel-head">
        <span className="workspace-stats" title={info?.root}>
          {info
            ? info.mode === "local"
              ? `本机 · ${info.file_count} 个文件`
              : info.local_folder_enabled
                ? `云端沙箱 · ${info.file_count} 个文件`
                : info.quota_size
                  ? `云端 · ${info.file_count} 个文件 · ${info.total_size} / ${info.quota_size}`
                  : `云端 · ${info.file_count} 个文件 · ${info.total_size}`
            : "工作区"}
        </span>
        <div className="workspace-head-actions">
          <button
            type="button"
            className="workspace-upload-btn"
            onClick={() => setUploadOpen(true)}
            disabled={loading}
            title="上传 zip 到云端工作区"
          >
            上传
          </button>
          {info?.local_folder_enabled && (
            <>
              {info.mode === "local" ? (
                <button
                  type="button"
                  className="workspace-folder-btn"
                  onClick={() => void handleResetFolder()}
                  disabled={folderBusy}
                  title="恢复为沙箱目录"
                >
                  沙箱
                </button>
              ) : (
                <button
                  type="button"
                  className="workspace-folder-btn"
                  onClick={() => setFolderOpen((v) => !v)}
                  disabled={folderBusy}
                  title="打开本机文件夹"
                >
                  打开
                </button>
              )}
            </>
          )}
          <button
            type="button"
            className="workspace-refresh"
            onClick={() => void load()}
            disabled={loading}
            title="刷新文件树"
            aria-label="刷新文件树"
          >
            ↻
          </button>
        </div>
      </div>

      {folderOpen && info?.local_folder_enabled && (
        <form
          className="workspace-folder-form"
          onSubmit={(e) => {
            e.preventDefault();
            void handleOpenFolder();
          }}
        >
          <input
            type="text"
            className="workspace-folder-input"
            placeholder="D:\Projects\myapp"
            value={folderInput}
            onChange={(e) => setFolderInput(e.target.value)}
            disabled={folderBusy}
            spellCheck={false}
          />
          <button type="submit" className="workspace-folder-submit" disabled={folderBusy}>
            绑定
          </button>
        </form>
      )}

      {info?.mode === "local" && info.local_path && (
        <p className="workspace-root-hint" title={info.local_path}>
          {info.local_path}
        </p>
      )}

      {error && <p className="workspace-error">{error}</p>}

      <div className="workspace-split" ref={splitRef}>
        <div className="workspace-tree">
          {loading && entries.length === 0 ? (
            <p className="workspace-empty">加载中…</p>
          ) : tree.length === 0 ? (
            <p className="workspace-empty">
              {info?.local_folder_enabled
                ? "暂无文件，可上传 zip 或让 Agent 写代码"
                : "暂无文件，点击「上传」导入 zip，或让 Agent git clone"}
            </p>
          ) : (
            tree.map((node) => (
              <TreeRow
                key={node.path}
                node={node}
                depth={0}
                expanded={expanded}
                selectedPath={selectedPath}
                highlightPath={highlightPath}
                onToggle={toggleDir}
                onSelect={(p) => void selectFile(p)}
              />
            ))
          )}
        </div>

        {selectedPath && (
          <>
            <SplitHandle
              onPointerDown={startDrag}
              label="拖动调整文件预览高度"
            />
            <div
              className="workspace-preview"
              style={{ height: previewHeight }}
            >
              <div className="workspace-preview-head">
                <div className="workspace-preview-title">
                  <FileIcon />
                  <span className="workspace-preview-name" title={selectedPath}>
                    {fileBaseName(selectedPath)}
                  </span>
                  {previewExt && (
                    <span className="workspace-preview-ext">.{previewExt}</span>
                  )}
                </div>
                <div className="workspace-preview-meta">
                  {previewTruncated && (
                    <span className="workspace-preview-tag">已截断</span>
                  )}
                  {!previewLoading && previewLines > 0 && (
                    <span className="workspace-preview-lines">
                      {previewLines} 行
                    </span>
                  )}
                  <button
                    type="button"
                    className="workspace-preview-close"
                    onClick={closePreview}
                    title="关闭预览"
                    aria-label="关闭文件预览"
                  >
                    <CloseIcon />
                  </button>
                </div>
              </div>
              <div className="workspace-preview-body">
                {previewLoading ? (
                  <PreviewSkeleton />
                ) : (
                  <pre className="workspace-preview-code">{preview ?? ""}</pre>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
