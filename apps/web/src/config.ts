/** API 与 health 端点（dev 用 vite proxy，生产用 VITE_API_BASE） */

export const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

/** 健康检查 URL：生产环境从 API 根去掉 /api 后缀 */
export const HEALTH_URL = import.meta.env.VITE_API_BASE
  ? import.meta.env.VITE_API_BASE.replace(/\/api\/?$/, "") + "/health"
  : "/health";
