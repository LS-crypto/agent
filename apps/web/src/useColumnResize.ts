import { useCallback, useEffect, useRef, useState } from "react";

function clamp(v: number, min: number, max: number) {
  return Math.min(max, Math.max(min, v));
}

function load(key: string, fallback: number): number {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    const n = Number.parseInt(raw, 10);
    return Number.isFinite(n) ? n : fallback;
  } catch {
    return fallback;
  }
}

function save(key: string, value: number) {
  try {
    localStorage.setItem(key, String(Math.round(value)));
  } catch {
    /* quota / private mode */
  }
}

/** Direct DOM update — no React re-render during drag */
function setVar(prop: string, px: number) {
  document.documentElement.style.setProperty(prop, `${px}px`);
}

interface Options {
  sidebarKey?: string;
  agentKey?: string;
  defaultSidebar?: number;
  defaultAgent?: number;
  minSidebar?: number;
  maxSidebar?: number;
  minAgent?: number;
  maxAgent?: number;
}

/**
 * Manages resizable sidebar and agent panel columns.
 *
 * Performance: during drag, CSS variables are updated directly on :root
 * (zero React re-renders). Only on pointer-up do we sync React state
 * for persistence. This gives 60 fps drag even in large component trees.
 */
export function useColumnResize(opts: Options = {}) {
  const {
    sidebarKey = "sheldon_sidebar_w",
    agentKey = "sheldon_agent_w",
    defaultSidebar = 280,
    defaultAgent = 340,
    minSidebar = 180,
    maxSidebar = 520,
    minAgent = 220,
    maxAgent = 520,
  } = opts;

  // React state only for initial render + persistence sync
  const [sidebarW, setSidebarW] = useState(() => load(sidebarKey, defaultSidebar));
  const [agentW, setAgentW] = useState(() => load(agentKey, defaultAgent));

  // Mutable refs hold the "live" values during drag
  const sidebarRef = useRef(sidebarW);
  const agentRef = useRef(agentW);
  const draggingRef = useRef(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Apply CSS variables on mount (once) so CSS can reference them
  useEffect(() => {
    setVar("--sidebar-w", sidebarW);
    setVar("--agent-w", agentW);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Sidebar drag ──────────────────────────────────────────────
  const startSidebarDrag = useCallback(
    (e: React.PointerEvent) => {
      e.preventDefault();
      draggingRef.current = true;
      const startX = e.clientX;
      const startW = sidebarRef.current;

      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";

      const onMove = (ev: PointerEvent) => {
        const maxS = Math.min(
          maxSidebar,
          Math.floor((containerRef.current?.clientWidth ?? 1200) * 0.45),
        );
        const next = clamp(startW + (ev.clientX - startX), minSidebar, maxS);
        sidebarRef.current = next;
        // Direct DOM — no re-render
        setVar("--sidebar-w", next);
      };

      const onUp = () => {
        draggingRef.current = false;
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
        document.removeEventListener("pointermove", onMove);
        document.removeEventListener("pointerup", onUp);
        // Sync React state once, for persistence
        setSidebarW(sidebarRef.current);
        save(sidebarKey, sidebarRef.current);
      };

      document.addEventListener("pointermove", onMove);
      document.addEventListener("pointerup", onUp);
    },
    [minSidebar, maxSidebar, sidebarKey],
  );

  // ── Agent panel drag ──────────────────────────────────────────
  const startAgentDrag = useCallback(
    (e: React.PointerEvent) => {
      e.preventDefault();
      draggingRef.current = true;
      const startX = e.clientX;
      const startW = agentRef.current;

      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";

      const onMove = (ev: PointerEvent) => {
        const maxA = Math.min(
          maxAgent,
          Math.floor((containerRef.current?.clientWidth ?? 1200) * 0.45),
        );
        // Dragging left → agent grows
        const next = clamp(startW - (ev.clientX - startX), minAgent, maxA);
        agentRef.current = next;
        setVar("--agent-w", next);
      };

      const onUp = () => {
        draggingRef.current = false;
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
        document.removeEventListener("pointermove", onMove);
        document.removeEventListener("pointerup", onUp);
        setAgentW(agentRef.current);
        save(agentKey, agentRef.current);
      };

      document.addEventListener("pointermove", onMove);
      document.addEventListener("pointerup", onUp);
    },
    [minAgent, maxAgent, agentKey],
  );

  // ── Auto-clamp on window resize ──────────────────────────────
  useEffect(() => {
    const el = containerRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;

    const ro = new ResizeObserver(() => {
      if (draggingRef.current) return;
      const cw = el.clientWidth;
      const maxS = Math.min(maxSidebar, Math.floor(cw * 0.45));
      const maxA = Math.min(maxAgent, Math.floor(cw * 0.45));

      const newS = clamp(sidebarRef.current, minSidebar, maxS);
      const newA = clamp(agentRef.current, minAgent, maxA);

      if (newS !== sidebarRef.current) {
        sidebarRef.current = newS;
        setVar("--sidebar-w", newS);
        setSidebarW(newS);
        save(sidebarKey, newS);
      }
      if (newA !== agentRef.current) {
        agentRef.current = newA;
        setVar("--agent-w", newA);
        setAgentW(newA);
        save(agentKey, newA);
      }
    });

    ro.observe(el);
    return () => ro.disconnect();
  }, [minSidebar, maxSidebar, minAgent, maxAgent, sidebarKey, agentKey]);

  return {
    containerRef,
    sidebarW,
    agentW,
    startSidebarDrag,
    startAgentDrag,
  };
}
