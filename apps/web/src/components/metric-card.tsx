import type * as React from "react";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: string;
  hint?: string;
  badge?: string;
  tone?: "default" | "critical" | "warning" | "success" | "info";
  icon?: React.ReactNode;
  /**
   * When `filled`, the card uses a solid tone surface (used for "Detection rate"
   * and "Last analysis" hero cards). Defaults to a neutral white tile.
   */
  variant?: "tile" | "filled-success" | "filled-sand";
}

const TONE_BG: Record<NonNullable<MetricCardProps["tone"]>, string> = {
  default: "bg-surface-muted",
  critical: "bg-rose/12",
  warning: "bg-warning/15",
  success: "bg-forest/10",
  info: "bg-info/10",
};

const TONE_TEXT: Record<NonNullable<MetricCardProps["tone"]>, string> = {
  default: "text-ink-muted",
  critical: "text-rose-700",
  warning: "text-[#8C6B1F]",
  success: "text-forest-700",
  info: "text-info",
};

export function MetricCard({
  label,
  value,
  hint,
  badge,
  tone = "default",
  icon,
  variant = "tile",
}: MetricCardProps) {
  if (variant === "filled-success") {
    return (
      <div className="flex flex-col justify-between gap-3 rounded-2xl bg-forest p-6 text-surface shadow-card">
        <span className="text-[11px] font-medium uppercase tracking-wider text-surface/70">
          {label}
        </span>
        <span className="text-5xl font-semibold tabular leading-none">{value}</span>
        {hint ? <span className="text-sm text-surface/80">{hint}</span> : null}
      </div>
    );
  }

  if (variant === "filled-sand") {
    return (
      <div className="flex flex-col gap-2 rounded-2xl bg-sand-300 p-6 text-ink shadow-card">
        {label ? (
          <span className="text-[11px] font-medium uppercase tracking-wider text-ink-muted">
            {label}
          </span>
        ) : null}
        <span className="text-2xl font-semibold tabular leading-tight">{value}</span>
        {hint ? <span className="text-sm text-ink/80">{hint}</span> : null}
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-col gap-4 rounded-2xl border border-ink/[0.06] bg-surface p-5 shadow-card",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        {icon ? (
          <span
            className={cn(
              "flex h-10 w-10 items-center justify-center rounded-xl",
              TONE_BG[tone],
              TONE_TEXT[tone],
            )}
          >
            {icon}
          </span>
        ) : null}
        {badge ? (
          <span className="text-[11px] font-medium uppercase tracking-wide text-ink-muted">
            {badge}
          </span>
        ) : null}
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-3xl font-semibold tabular leading-none text-ink">
          {value}
        </span>
        <span className="text-sm text-ink-muted">{label}</span>
        {hint ? <span className="text-xs text-ink-muted">{hint}</span> : null}
      </div>
    </div>
  );
}
