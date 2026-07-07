import type { PendingConfirmation } from "../types";

interface Props {
  pending: PendingConfirmation;
  onAllow: () => void;
  onDeny: () => void;
  submitting: boolean;
}

const SEV_LABEL: Record<string, string> = {
  low: "低危",
  medium: "中等",
  high: "高危",
};

export function ConfirmDialog({
  pending,
  onAllow,
  onDeny,
  submitting,
}: Props) {
  const sev = pending.severity ?? "medium";
  const sevLabel = SEV_LABEL[sev] ?? sev;

  return (
    <div className="confirm-overlay" role="dialog" aria-modal="true">
      <div className="confirm-dialog">
        <header className="confirm-header">
          <h3>需要你的确认</h3>
          <span className={`confirm-risk risk-${pending.risk} severity-${sev}`}>
            {sevLabel} · {pending.risk}
          </span>
        </header>
        <p className="confirm-summary">{pending.summary}</p>
        {pending.explanation && (
          <div className="confirm-explain">
            <strong>说明</strong>
            <p>{pending.explanation.replace(/<[^>]+>/g, "")}</p>
          </div>
        )}
        {pending.impact && (
          <div className="confirm-impact">
            <strong>可能影响</strong>
            <p>{pending.impact}</p>
          </div>
        )}
        <details className="confirm-args">
          <summary>查看参数</summary>
          <pre>{JSON.stringify(pending.args, null, 2)}</pre>
        </details>
        <div className="confirm-actions">
          <button
            type="button"
            className="confirm-btn deny"
            onClick={onDeny}
            disabled={submitting}
          >
            拒绝
          </button>
          <button
            type="button"
            className="confirm-btn allow"
            onClick={onAllow}
            disabled={submitting}
          >
            允许
          </button>
        </div>
      </div>
    </div>
  );
}
