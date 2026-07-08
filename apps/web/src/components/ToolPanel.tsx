import { useEffect, useState } from "react";
import { fetchMcpStatus, type McpStatusItem } from "../api/client";
import type { ToolLogEntry } from "../types";

interface Props {
  entries: ToolLogEntry[];
  open: boolean;
  onToggle: () => void;
  onOpenFile?: (path: string) => void;
}

function ActivityIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M22 12h-4l-3 9L9 3l-3 9H2"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function McpDot({ service }: { service: McpStatusItem }) {
  const cls = service.connected
    ? "mcp-dot ok"
    : service.configured
      ? "mcp-dot warn"
      : "mcp-dot off";
  return (
    <span className={cls} title={service.message ?? service.name} />
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

/** Collapsed icon bar — always visible, narrow vertical strip */
function IconBar({
  entryCount,
  mcpServices,
  onToggle,
}: {
  entryCount: number;
  mcpServices: McpStatusItem[];
  onToggle: () => void;
}) {
  return (
    <div className="agent-icon-bar" onClick={onToggle} role="button" title="展开活动面板">
      <div className="agent-icon-bar-item">
        <ActivityIcon />
        {entryCount > 0 && (
          <span className="agent-icon-bar-badge">{entryCount > 99 ? "99+" : entryCount}</span>
        )}
      </div>
      {mcpServices.length > 0 && (
        <div className="agent-icon-bar-mcp">
          {mcpServices.map((s) => (
            <McpDot key={s.id} service={s} />
          ))}
        </div>
      )}
    </div>
  );
}

export function ToolPanel({ entries, open, onToggle, onOpenFile }: Props) {
  const [timelineOpen, setTimelineOpen] = useState(true);
  const [mcpServices, setMcpServices] = useState<McpStatusItem[]>([]);

  useEffect(() => {
    void fetchMcpStatus(false)
      .then((data) => setMcpServices(data.services ?? []))
      .catch(() => setMcpServices([]));
  }, []);

  useEffect(() => {
    if (entries.length > 0) {
      setTimelineOpen(true);
    }
  }, [entries.length]);

  if (!open) {
    return (
      <aside className="agent-panel collapsed">
        <IconBar entryCount={entries.length} mcpServices={mcpServices} onToggle={onToggle} />
      </aside>
    );
  }

  return (
    <aside className="agent-panel open">
      <div className="agent-panel-body">
        <header className="agent-panel-header">
          <div className="agent-panel-header-main">
            <h2>活动</h2>
            <span className="agent-panel-count">{entries.length}</span>
          </div>
          <div className="agent-panel-header-actions">
            {entries.length > 0 && (
              <button
                type="button"
                className="agent-timeline-fold"
                onClick={() => setTimelineOpen((v) => !v)}
              >
                {timelineOpen ? "折叠" : "展开"}
              </button>
            )}
            <button
              type="button"
              className="agent-panel-collapse-btn"
              onClick={onToggle}
              title="收起面板"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
                <path
                  d="M15 6l-6 6 6 6"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          </div>
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
    </aside>
  );
}
