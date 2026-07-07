import { useCallback, useEffect, useRef, useState } from "react";

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function loadStoredSize(key: string, fallback: number): number {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    const n = Number.parseInt(raw, 10);
    return Number.isFinite(n) ? n : fallback;
  } catch {
    return fallback;
  }
}

function saveStoredSize(key: string, value: number): void {
  try {
    localStorage.setItem(key, String(Math.round(value)));
  } catch {
    /* quota / private mode */
  }
}

type Axis = "vertical" | "horizontal";

interface Options {
  /** localStorage key */
  storageKey: string;
  defaultSize: number;
  minSize: number;
  /** fraction of container, e.g. 0.78 */
  maxRatio?: number;
  axis?: Axis;
}

/**
 * Drag-to-resize split pane. `size` is the trailing pane (bottom or right).
 */
export function useSplitPane({
  storageKey,
  defaultSize,
  minSize,
  maxRatio = 0.78,
  axis = "vertical",
}: Options) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sizeRef = useRef(loadStoredSize(storageKey, defaultSize));
  const [size, setSize] = useState(sizeRef.current);
  const draggingRef = useRef(false);

  const applySize = useCallback(
    (next: number) => {
      const container = containerRef.current;
      const maxSize = container
        ? Math.max(minSize, container[axis === "vertical" ? "clientHeight" : "clientWidth"] * maxRatio)
        : defaultSize * 2;
      const clamped = clamp(next, minSize, maxSize);
      sizeRef.current = clamped;
      setSize(clamped);
    },
    [axis, defaultSize, maxRatio, minSize],
  );

  const startDrag = useCallback(
    (event: React.PointerEvent<HTMLElement>) => {
      event.preventDefault();
      draggingRef.current = true;
      const startPos = axis === "vertical" ? event.clientY : event.clientX;
      const startSize = sizeRef.current;

      const cursor = axis === "vertical" ? "row-resize" : "col-resize";
      document.body.style.cursor = cursor;
      document.body.style.userSelect = "none";

      const onMove = (ev: PointerEvent) => {
        const pos = axis === "vertical" ? ev.clientY : ev.clientX;
        const delta = startPos - pos;
        applySize(startSize + delta);
      };

      const onUp = () => {
        draggingRef.current = false;
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
        document.removeEventListener("pointermove", onMove);
        document.removeEventListener("pointerup", onUp);
        saveStoredSize(storageKey, sizeRef.current);
      };

      document.addEventListener("pointermove", onMove);
      document.addEventListener("pointerup", onUp);
    },
    [applySize, axis, storageKey],
  );

  useEffect(() => {
    const el = containerRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => {
      if (draggingRef.current) return;
      applySize(sizeRef.current);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [applySize]);

  return { containerRef, size, startDrag, setSize: applySize };
}
