import { useCallback, useRef, useState } from "react";
import type { ToolLogEntry } from "./types";

const MAX_TOOL_ENTRIES = 48;

/** 合并 SSE 工具事件，避免大任务时每帧数十次 setState 卡死 UI。 */
export function useBatchedToolEntries() {
  const [entries, setEntries] = useState<ToolLogEntry[]>([]);
  const pendingRef = useRef<ToolLogEntry[]>([]);
  const flushIdRef = useRef<number | null>(null);

  const flush = useCallback(() => {
    flushIdRef.current = null;
    const batch = pendingRef.current;
    pendingRef.current = [];
    if (batch.length === 0) return;
    setEntries((prev) => {
      const next = [...prev, ...batch];
      return next.length > MAX_TOOL_ENTRIES
        ? next.slice(-MAX_TOOL_ENTRIES)
        : next;
    });
  }, []);

  const append = useCallback(
    (entry: ToolLogEntry) => {
      pendingRef.current.push(entry);
      if (flushIdRef.current != null) return;
      flushIdRef.current = requestAnimationFrame(flush);
    },
    [flush],
  );

  const reset = useCallback(() => {
    pendingRef.current = [];
    if (flushIdRef.current != null) {
      cancelAnimationFrame(flushIdRef.current);
      flushIdRef.current = null;
    }
    setEntries([]);
  }, []);

  return { entries, append, reset };
}

/** 节流流式文本更新，降低 MessageContent 重绘频率。 */
export function useThrottledStreamingText() {
  const [text, setText] = useState("");
  const latestRef = useRef("");
  const rafRef = useRef<number | null>(null);

  const setThrottled = useCallback((value: string) => {
    latestRef.current = value;
    if (rafRef.current != null) return;
    rafRef.current = requestAnimationFrame(() => {
      rafRef.current = null;
      setText(latestRef.current);
    });
  }, []);

  const flush = useCallback((value?: string) => {
    if (rafRef.current != null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    const final = value ?? latestRef.current;
    latestRef.current = final;
    setText(final);
  }, []);

  const clear = useCallback(() => {
    if (rafRef.current != null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    latestRef.current = "";
    setText("");
  }, []);

  return { text, setThrottled, flush, clear };
}
