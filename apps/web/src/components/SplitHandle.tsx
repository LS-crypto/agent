interface Props {
  onPointerDown: (event: React.PointerEvent<HTMLElement>) => void;
  /** horizontal = bar between top/bottom panes */
  orientation?: "horizontal" | "vertical";
  label?: string;
}

export function SplitHandle({
  onPointerDown,
  orientation = "horizontal",
  label = "拖动调整大小",
}: Props) {
  return (
    <div
      role="separator"
      aria-orientation={orientation}
      aria-label={label}
      className={
        orientation === "horizontal"
          ? "split-handle split-handle-row"
          : "split-handle split-handle-col"
      }
      onPointerDown={onPointerDown}
      title={label}
    >
      <span className="split-handle-grip" aria-hidden />
    </div>
  );
}
