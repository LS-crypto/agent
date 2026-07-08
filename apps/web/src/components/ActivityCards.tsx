import { memo, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { ToolLogEntry } from "../types";

const TOOL_VERBS: Record<string, string> = {
  read_file: "Read",
  write_file: "Write",
  edit_file: "Edit",
  list_dir: "List",
  grep: "Grep",
  glob_file_search: "Glob",
  execute_command: "Shell",
  git_status: "Git status",
  git_diff: "Git diff",
  git_commit: "Git commit",
  fetch_url: "Fetch",
  calculate: "Calculate",
  get_current_time: "Time",
  brave_web_search: "Search web",
  brave_news_search: "Search news",
  github_search_issues: "GitHub issues",
  github_get_issue: "GitHub issue",
  github_list_pulls: "GitHub PRs",
  github_get_pull: "GitHub PR",
  github_search_code: "GitHub code",
  memory_note_save: "Save note",
  memory_note_search: "Search notes",
  memory_note_list: "List notes",
};

type ToolRow = {
  type: "tool";
  tool: string;
  args: Record<string, unknown>;
  status: "running" | "ok" | "fail";
  preview?: string;
  filePath?: string;
  round?: number;
};

type ThinkingRow = {
  type: "thinking";
  stepType: "thought" | "revision" | "conclusion";
  content: string;
  round?: number;
};

type ActivityRow = ToolRow | ThinkingRow;

function toolVerb(tool: string): string {
  return TOOL_VERBS[tool] ?? tool.replace(/_/g, " ");
}

function toolTarget(_tool: string, args: Record<string, unknown>): string {
  if (typeof args.file_path === "string" && args.file_path) return args.file_path;
  if (typeof args.dir_path === "string") return args.dir_path || ".";
  if (typeof args.path === "string" && args.path) return args.path;
  if (typeof args.pattern === "string" && args.pattern) return args.pattern;
  if (typeof args.command === "string" && args.command) {
    const cmd = args.command.trim();
    return cmd.length > 52 ? `${cmd.slice(0, 52)}…` : cmd;
  }
  if (typeof args.query === "string" && args.query) return args.query;
  if (typeof args.title === "string" && args.title) return args.title;
  if (typeof args.message === "string" && args.message) {
    const msg = args.message.trim();
    return msg.length > 40 ? `${msg.slice(0, 40)}…` : msg;
  }
  return "";
}

export function formatToolLabel(
  tool: string,
  args: Record<string, unknown>,
  round?: number,
): string {
  const verb = toolVerb(tool);
  const target = toolTarget(tool, args);
  const core = target ? `${verb} ${target}` : verb;
  if (round != null && round > 0) {
    return `第 ${round} 轮 · ${core}`;
  }
  return core;
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

function processEntries(entries: ToolLogEntry[]): ActivityRow[] {
  const rows: ActivityRow[] = [];
  let currentRound: number | undefined;
  let pendingCall: Extract<ToolLogEntry, { kind: "tool_call" }> | null = null;

  for (const entry of entries) {
    if (entry.kind === "loop_round") {
      currentRound = entry.round;
      continue;
    }
    if (entry.kind === "thinking_step") {
      rows.push({
        type: "thinking",
        stepType: entry.stepType,
        content: entry.content,
        round: entry.round ?? currentRound,
      });
      continue;
    }
    if (entry.kind === "tool_call") {
      pendingCall = entry;
      continue;
    }
    if (entry.kind === "tool_result") {
      const call = pendingCall;
      pendingCall = null;
      rows.push({
        type: "tool",
        tool: call?.tool ?? entry.tool ?? "tool",
        args: call?.args ?? {},
        status: entry.success ? "ok" : "fail",
        preview: entry.preview,
        filePath: entry.filePath,
        round: currentRound,
      });
    }
  }

  if (pendingCall) {
    rows.push({
      type: "tool",
      tool: pendingCall.tool,
      args: pendingCall.args,
      status: "running",
      round: currentRound,
    });
  }

  return rows;
}

function Spinner() {
  return (
    <svg
      className="tool-activity-spinner"
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden
    >
      <circle
        cx="12"
        cy="12"
        r="9"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeDasharray="42 20"
      />
    </svg>
  );
}

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      className={`tool-activity-chevron${open ? " open" : ""}`}
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
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

function ToolStatusIcon({ status }: { status: ToolRow["status"] }) {
  if (status === "running") return <Spinner />;
  if (status === "ok") {
    return (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
        <path
          d="M5 12l4 4L19 6"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    );
  }
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M6 6l12 12M18 6L6 18"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function ToolActivityRow({
  row,
  onOpenFile,
}: {
  row: ToolRow;
  onOpenFile?: (path: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const label = formatToolLabel(row.tool, row.args, row.round);
  const running = row.status === "running";
  const hasDetails =
    Object.keys(row.args).length > 0 || Boolean(row.preview) || Boolean(row.filePath);

  return (
    <div
      className={`tool-activity-row tool-row-${row.status}${expanded ? " expanded" : ""}${
        isMcpTool(row.tool) ? " mcp" : ""
      }`}
    >
      <button
        type="button"
        className="tool-activity-row-main"
        onClick={() => hasDetails && setExpanded((v) => !v)}
        disabled={!hasDetails}
        aria-expanded={hasDetails ? expanded : undefined}
      >
        <span className={`tool-activity-icon status-${row.status}`}>
          <ToolStatusIcon status={row.status} />
        </span>
        <span className="tool-activity-label">
          {running ? (
            <>
              <span className="tool-activity-running-prefix">Running</span>
              {label}
            </>
          ) : (
            label
          )}
        </span>
        {hasDetails && <ChevronIcon open={expanded} />}
      </button>
      {expanded && hasDetails && (
        <div className="tool-activity-details">
          {row.filePath && onOpenFile && (
            <button
              type="button"
              className="tool-activity-file-link"
              onClick={() => onOpenFile(row.filePath!)}
            >
              打开 {row.filePath}
            </button>
          )}
          {Object.keys(row.args).length > 0 && (
            <pre className="tool-activity-args">{JSON.stringify(row.args, null, 2)}</pre>
          )}
          {row.preview && (
            <pre className="tool-activity-preview">{row.preview}</pre>
          )}
        </div>
      )}
    </div>
  );
}

function ThinkingActivityRow({ row }: { row: ThinkingRow }) {
  const [expanded, setExpanded] = useState(false);
  const preview =
    row.content.length > 72 ? `${row.content.slice(0, 72)}…` : row.content;
  const badge = stepLabel(row.stepType);

  return (
    <div className={`tool-activity-row thinking-row${expanded ? " expanded" : ""}`}>
      <button
        type="button"
        className="tool-activity-row-main"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        <span className="tool-activity-icon status-thinking">
          <span className="thinking-dot" />
        </span>
        <span className="tool-activity-label">
          {row.round ? `第 ${row.round} 轮 · ` : ""}
          {badge}
          {!expanded && preview ? ` · ${preview}` : ""}
        </span>
        <ChevronIcon open={expanded} />
      </button>
      {expanded && (
        <div className="tool-activity-details">
          <p className="tool-activity-thinking-text">{row.content}</p>
        </div>
      )}
    </div>
  );
}

interface Props {
  entries: ToolLogEntry[];
  sending?: boolean;
  onOpenFile?: (path: string) => void;
}

export const ActivityCards = memo(function ActivityCards({
  entries,
  sending,
  onOpenFile,
}: Props) {
  const rows = useMemo(() => processEntries(entries), [entries]);
  const [collapsed, setCollapsed] = useState(false);

  // 新一轮开始时自动展开
  useEffect(() => {
    if (sending) setCollapsed(false);
  }, [sending]);

  if (rows.length === 0) return null;

  const rendered: ReactNode[] = rows.map((row, i) => {
    const key = `row-${i}`;
    if (row.type === "thinking") {
      return <ThinkingActivityRow key={key} row={row} />;
    }
    return <ToolActivityRow key={key} row={row} onOpenFile={onOpenFile} />;
  });

  return (
    <div
      className={`tool-activity-strip${sending ? " is-live" : ""}${collapsed ? " is-collapsed" : ""}`}
      aria-label="Agent 工具调用"
      aria-live="polite"
    >
      <button
        type="button"
        className="tool-activity-strip-header"
        onClick={() => setCollapsed((v) => !v)}
        aria-expanded={!collapsed}
      >
        <span className="tool-activity-strip-title">
          {sending ? "Agent 活动中" : "本轮活动"}
          <span className="tool-activity-strip-count">{rows.length}</span>
        </span>
        <svg
          className={`tool-activity-strip-chevron${collapsed ? "" : " open"}`}
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
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
      </button>
      {!collapsed && rendered}
    </div>
  );
});

// 保留导出供测试或其他组件引用
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
    <ThinkingActivityRow row={{ type: "thinking", stepType, content, round }} />
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
  const status: ToolRow["status"] =
    success === undefined ? "running" : success ? "ok" : "fail";
  return (
    <ToolActivityRow
      row={{
        type: "tool",
        tool,
        args: args ?? {},
        status,
        preview,
        filePath,
      }}
      onOpenFile={onOpenFile}
    />
  );
}
