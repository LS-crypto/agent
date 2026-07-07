export interface SessionSummary {
  id: string;
  user_id: string;
  title: string;
  model?: string;
  permission?: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface SessionDetail extends SessionSummary {
  messages: Array<{
    role: string;
    content?: string;
  }>;
}

export interface ChatRequest {
  session_id: string;
  message: string;
  model?: string;
  permission?: string;
}

export interface AgentModel {
  id: string;
  label: string;
  group: string;
  tier: string;
  description: string;
  supports_tools: boolean;
  supports_vision?: boolean;
  available: boolean;
  is_default?: boolean;
  max_tokens?: number;
  tagline?: string;
  features?: string[];
  skills?: string[];
  prefer_tools?: string[];
  max_iterations?: number;
  free_quota_tokens?: number;
  free_quota_days?: number;
  in_user_whitelist?: boolean;
}

export interface ModelsResponse {
  default_model: string;
  auto_model_id: string;
  models: AgentModel[];
  remote_checked: boolean;
  role_restricted?: boolean;
  free_quota_note?: string;
}

export interface SseEvent {
  event: string;
  time?: string;
  content?: string;
  message?: string;
  round?: number;
  tool_count?: number;
  tool?: string;
  args?: Record<string, unknown>;
  success?: boolean;
  preview?: string;
  result?: string;
  session_id?: string;
  confirmation_id?: string;
  risk?: "allowed" | "review" | "blocked";
  summary?: string;
  explanation?: string;
  impact?: string;
  severity?: "low" | "medium" | "high";
  permission_tier?: string;
  step_type?: "thought" | "revision" | "conclusion";
  index?: number;
}

export interface PendingConfirmation {
  confirmation_id: string;
  tool: string;
  args: Record<string, unknown>;
  risk: "allowed" | "review" | "blocked";
  summary: string;
  explanation?: string;
  impact?: string;
  severity?: "low" | "medium" | "high";
  permission_tier?: string;
}

export interface PermissionTier {
  id: string;
  label: string;
  description: string;
  is_default?: boolean;
}

export type ToolLogEntry =
  | { kind: "loop_round"; round: number; toolCount: number; time?: string }
  | {
      kind: "tool_call";
      tool: string;
      args: Record<string, unknown>;
      time?: string;
    }
  | {
      kind: "tool_result";
      success: boolean;
      preview: string;
      tool?: string;
      filePath?: string;
      time?: string;
    }
  | {
      kind: "thinking_step";
      stepType: "thought" | "revision" | "conclusion";
      content: string;
      round?: number;
      time?: string;
    };
