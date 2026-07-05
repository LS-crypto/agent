import { useEffect, useState } from "react";
import { fetchMcpStatus, type McpStatusItem } from "../api/client";
import type { ToolLogEntry } from "../types";

interface Props {
  entries: ToolLogEntry[];
  open: boolean;
  onToggle: () => void;
  onOpenFile?: (path: string) => void;
}

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      className={open ? "chevron open" : "chevron"}
      aria-hidden
    >
      <path
        d="M9 6l6 6-6 6"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function stepBadgeClass(stepType: string): string {
  if (stepType === "revision") return "timeline-badge badge-revision";
  if (stepType === "conclusion") return "timeline-badge badge-conclusion";
  return "timeline-badge badge-thought";
}

function stepLabel(stepType: string): string {
  if (stepType === "revision") return "修订";
  if (stepType === "conclusion") return "结论";
  return "思考";
}

function dotClass(entry: ToolLogEntry): string {
  if (entry.kind === "thinking_step") {
    return `timeline-dot dot-thinking_step step-${entry.stepType}`;
  }
  return `timeline-dot dot-${entry.kind}`;
}

function isMcpTool(name: string): boolean {
  return name.startsWith("github_") || name.startsWith("brave_");
}

function McpStatusStrip({ services }: { services: McpStatusItem[] }) {
  if (services.length === 0) return null;
  return (
    <div className="agent-mcp-strip" aria-label="MCP 状态">
      {services.map((s) => (
        <span
          key={s.id}
          className={
            s.connected
              ? "agent-mcp-chip ok"
              : s.configured
                ? "agent-mcp-chip warn"
                : "agent-mcp-chip off"
          }
          title={s.message ?? s.name}
        >
          {s.id === "sheldon-builtin" ? "内置" : s.id}
        </span>
      ))}
    </div>
  );
}

export function ToolPanel({ entries, open, onToggle, onOpenFile }: Props) {
  const [timelineOpen, setTimelineOpen] = useState(true);
  const [mcpServices, setMcpServices] = useState<McpStatusItem[]>([]);

  useEffect(() => {
    if (!open) return;
    void fetchMcpStatus(false)
      .then((data) => setMcpServices(data.services ?? []))
      .catch(() => setMcpServices([]));
  }, [open]);

  useEffect(() => {
    if (entries.length > 0) {
      setTimelineOpen(true);
    }
  }, [entries.length]);

  return (
    <aside className={open ? "agent-panel open" : "agent-panel collapsed"}>
      <button
        type="button"
        className="agent-panel-toggle"
        onClick={onToggle}
        title={open ? "收起面板" : "展开面板"}
        aria-expanded={open}
      >
        <ChevronIcon open={open} />
      </button>

      {open && (
        <div className="agent-panel-body">
          <header className="agent-panel-header">
            <div className="agent-panel-header-main">
              <h2>活动 / MCP</h2>
              <span className="agent-panel-count">{entries.length}</span>
            </div>
            {entries.length > 0 && (
              <button
                type="button"
                className="agent-timeline-fold"
                onClick={() => setTimelineOpen((v) => !v)}
              >
                {timelineOpen ? "折叠" : "展开"}
              </button>
            )}
          </header>

          <McpStatusStrip services={mcpServices} />

          {timelineOpen && (
            <div className="agent-timeline">
              {entries.length === 0 ? (
                <p className="agent-empty">
                  推理步骤、工具/MCP 调用会同步显示在对话区与这里。Flash 为简版思考，Max
                  为完整分步。
                </p>
              ) : (
                entries.map((entry, i) => (
                  <div key={i} className="timeline-item">
                    <div className="timeline-rail">
                      <span className={dotClass(entry)} />
                      {i < entries.length - 1 && <span className="timeline-line" />}
                    </div>
                    <div className="timeline-card">
                      {entry.kind === "loop_round" && (
                        <>
                          <div className="timeline-title">第 {entry.round} 轮</div>
                          <div className="timeline-meta">{entry.toolCount} 个工具可用</div>
                        </>
                      )}
                      {entry.kind === "thinking_step" && (
                        <>
                          <span className={stepBadgeClass(entry.stepType)}>
                            {stepLabel(entry.stepType)}
                            {entry.round ? ` · R${entry.round}` : ""}
                          </span>
                          <div className="timeline-meta">{entry.content}</div>
                        </>
                      )}
                      {entry.kind === "tool_call" && (
                        <>
                          <div className="timeline-title">
                            {entry.tool}
                            {isMcpTool(entry.tool) && (
                              <span className="inline-tool-tag">MCP</span>
                            )}
                          </div>
                          {(entry.tool === "write_file" || entry.tool === "edit_file") &&
                            typeof entry.args.file_path === "string" && (
                              <button
                                type="button"
                                className="timeline-file-link"
                                onClick={() =>
                                  onOpenFile?.(entry.args.file_path as string)
                                }
                              >
                                目标文件 · {String(entry.args.file_path)}
                              </button>
                            )}
                          <pre className="timeline-code">
                            {JSON.stringify(entry.args, null, 2)}
                          </pre>
                        </>
                      )}
                      {entry.kind === "tool_result" && (
                        <details open>
                          <summary>
                            结果 · {entry.success ? "成功" : "失败"}
                            {entry.filePath && entry.success && onOpenFile && (
                              <>
                                {" · "}
                                <button
                                  type="button"
                                  className="timeline-file-link inline"
                                  onClick={(e) => {
                                    e.preventDefault();
                                    onOpenFile(entry.filePath!);
                                  }}
                                >
                                  查看 {entry.filePath}
                                </button>
                              </>
                            )}
                          </summary>
                          <pre className="timeline-code">{entry.preview}</pre>
                        </details>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      )}
    </aside>
  );
}
