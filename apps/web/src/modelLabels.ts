import type { AgentModel } from "./types";

/** 格式化模型下拉：名称 + 类型（分组/视觉）。 */
export function formatModelOptionLabel(m: AgentModel): string {
  const parts = [m.label];
  if (m.group) {
    parts.push(m.group);
  }
  if (m.supports_vision) {
    parts.push("视觉");
  }
  if (!m.available) {
    parts.push("未开通");
  }
  return parts.join(" · ");
}
