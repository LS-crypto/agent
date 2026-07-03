import type { ToolLogEntry } from "../types";

interface Props {
  entries: ToolLogEntry[];
  open: boolean;
  onToggle: () => void;
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

export function ToolPanel({ entries, open, onToggle }: Props) {
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
            <h2>活动</h2>
            <span className="agent-panel-count">{entries.length}</span>
          </header>

          <div className="agent-timeline">
            {entries.length === 0 ? (
              <p className="agent-empty">
                推理步骤、工具调用与结果会显示在这里。使用 Max 模型可看到分步思考。
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
                        <div className="timeline-title">{entry.tool}</div>
                        <pre className="timeline-code">
                          {JSON.stringify(entry.args, null, 2)}
                        </pre>
                      </>
                    )}
                    {entry.kind === "tool_result" && (
                      <details open>
                        <summary>结果 · {entry.success ? "成功" : "失败"}</summary>
                        <pre className="timeline-code">{entry.preview}</pre>
                      </details>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </aside>
  );
}
