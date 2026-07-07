import type { ToolLogEntry } from "./types";

const TOOL_STATUS: Record<string, string> = {
  read_file: "正在读取文件",
  write_file: "正在写入文件",
  edit_file: "正在编辑文件",
  list_dir: "正在浏览目录",
  grep: "正在搜索代码",
  glob_file_search: "正在查找文件",
  execute_command: "正在执行命令",
  git_status: "正在查看 Git 状态",
  git_diff: "正在查看变更",
  git_commit: "正在提交更改",
  fetch_url: "正在获取网页",
  brave_web_search: "正在搜索网络",
  brave_news_search: "正在搜索新闻",
  github_search_code: "正在搜索 GitHub 代码",
  github_search_issues: "正在搜索 GitHub Issues",
  memory_note_save: "正在保存笔记",
  memory_note_search: "正在检索笔记",
};

function shortPath(value: unknown): string | null {
  if (typeof value !== "string" || !value.trim()) return null;
  const p = value.trim().replace(/\\/g, "/");
  const parts = p.split("/");
  return parts.length > 2 ? `…/${parts.slice(-2).join("/")}` : p;
}

function toolStatusHint(tool: string, args: Record<string, unknown>): string {
  const base = TOOL_STATUS[tool] ?? `正在调用 ${tool.replace(/_/g, " ")}`;
  const path =
    shortPath(args.file_path) ??
    shortPath(args.path) ??
    shortPath(args.dir_path);
  return path ? `${base} · ${path}` : `${base}…`;
}

/** Cursor 风格：根据 SSE 活动推导当前 Agent 状态文案。 */
export function deriveAgentStatusHint(
  entries: ToolLogEntry[],
  opts: {
    sending: boolean;
    streamingText: string;
    awaitingConfirm?: boolean;
  },
): string | null {
  if (!opts.sending) return null;
  if (opts.awaitingConfirm) return "等待你的确认…";
  if (opts.streamingText.trim()) return "正在生成回复…";

  for (let i = entries.length - 1; i >= 0; i--) {
    const entry = entries[i];
    if (entry.kind === "tool_call") {
      return toolStatusHint(entry.tool, entry.args);
    }
    if (entry.kind === "tool_result") {
      return "准备下一步…";
    }
    if (entry.kind === "loop_round") {
      return entry.round > 1 ? `正在规划第 ${entry.round} 轮…` : "正在思考…";
    }
    if (entry.kind === "thinking_step") {
      if (entry.stepType === "revision") return "正在修订计划…";
      if (entry.stepType === "conclusion") return "正在整理结论…";
      return "正在推理…";
    }
  }

  return "准备下一步…";
}
