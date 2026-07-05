import type { ReactNode } from "react";
import type { ToolLogEntry } from "../types";

function stepBadgeClass(stepType: string): string {
  if (stepType === "revision") return "inline-step-badge badge-revision";
  if (stepType === "conclusion") return "inline-step-badge badge-conclusion";
  return "inline-step-badge badge-thought";
}

function stepLabel(stepType: string): string {
  if (stepType === "revision") return "修订";
  if (stepType === "conclusion") return "结论";
  return "思考";
}

function isMcpTool(name: string): boolean {
  return (
    name.startsWith("github_") ||
    name.startsWith("brave_") ||
    name === "get_current_time" ||
    name === "fetch_url" ||
    name === "calculate"
  );
}

export function ThinkingStepCard({
  stepType,
  content,
  round,
}: {
  stepType: "thought" | "revision" | "conclusion";
  content: string;
  round?: number;
}) {
  return (
    <div className="inline-activity-card inline-thinking-card">
      <span className={stepBadgeClass(stepType)}>
        {stepLabel(stepType)}
        {round ? ` · R${round}` : ""}
      </span>
      <p className="inline-activity-text">{content}</p>
    </div>
  );
}

export function ToolCallCard({
  tool,
  args,
  success,
  preview,
  filePath,
  onOpenFile,
}: {
  tool: string;
  args?: Record<string, unknown>;
  success?: boolean;
  preview?: string;
  filePath?: string;
  onOpenFile?: (path: string) => void;
}) {
  const mcp = isMcpTool(tool);
  const status =
    success === undefined ? null : success ? "成功" : "失败";

  return (
    <div className={`inline-activity-card inline-tool-card${mcp ? " mcp" : ""}`}>
      <div className="inline-tool-head">
        <span className="inline-tool-name">{tool}</span>
        {mcp && <span className="inline-tool-tag">MCP</span>}
        {status && (
          <span className={success ? "inline-tool-ok" : "inline-tool-fail"}>
            {status}
          </span>
        )}
      </div>
      {filePath && onOpenFile && (
        <button
          type="button"
          className="inline-tool-file-link"
          onClick={() => onOpenFile(filePath)}
        >
          查看 {filePath}
        </button>
      )}
      {args && Object.keys(args).length > 0 && (
        <pre className="inline-tool-args">{JSON.stringify(args, null, 2)}</pre>
      )}
      {preview && (
        <details className="inline-tool-result">
          <summary>工具输出</summary>
          <pre>{preview}</pre>
        </details>
      )}
    </div>
  );
}

interface Props {
  entries: ToolLogEntry[];
  onOpenFile?: (path: string) => void;
}

export function ActivityCards({ entries, onOpenFile }: Props) {
  const visible = entries.filter((e) => e.kind !== "loop_round");
  if (visible.length === 0) return null;

  const rendered: ReactNode[] = [];
  let pendingCall: Extract<ToolLogEntry, { kind: "tool_call" }> | null = null;

  for (let i = 0; i < visible.length; i += 1) {
    const entry = visible[i];
    if (entry.kind === "thinking_step") {
      rendered.push(
        <ThinkingStepCard
          key={`think-${i}`}
          stepType={entry.stepType}
          content={entry.content}
          round={entry.round}
        />,
      );
      continue;
    }
    if (entry.kind === "tool_call") {
      pendingCall = entry;
      continue;
    }
    if (entry.kind === "tool_result") {
      const call = pendingCall;
      pendingCall = null;
      rendered.push(
        <ToolCallCard
          key={`tool-${i}`}
          tool={call?.tool ?? entry.tool ?? "tool"}
          args={call?.args}
          success={entry.success}
          preview={entry.preview}
          filePath={entry.filePath}
          onOpenFile={onOpenFile}
        />,
      );
      continue;
    }
  }

  if (pendingCall) {
    rendered.push(
      <ToolCallCard
        key="tool-pending"
        tool={pendingCall.tool}
        args={pendingCall.args}
        onOpenFile={onOpenFile}
      />,
    );
  }

  return (
    <div className="inline-activity-block" aria-label="Agent 活动">
      <div className="inline-activity-label">Agent 活动</div>
      {rendered}
    </div>
  );
}
