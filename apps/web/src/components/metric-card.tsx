import type * as React from "react";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: string;
  hint?: string;
  tone?: "default" | "critical" | "warning" | "success";
  icon?: React.ReactNode;
}

const TONE_BG: Record<NonNullable<MetricCardProps["tone"]>, string> = {
  default: "bg-sand-300/70",
  critical: "bg-rose/10",
  warning: "bg-warning/10",
  success: "bg-forest/10",
};

const TONE_TEXT: Record<NonNullable<MetricCardProps["tone"]>, string> = {
  default: "text-ink",
  critical: "text-rose-700",
  warning: "text-[#8C6B1F]",
  success: "text-forest-700",
};

export function MetricCard({ label, value, hint, tone = "default", icon }: MetricCardProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-2 rounded-xl border border-ink/5 p-6 shadow-soft",
        TONE_BG[tone],
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-meta text-ink-muted">{label}</span>
        {icon ? <span className={cn("opacity-70", TONE_TEXT[tone])}>{icon}</span> : null}
      </div>
      <span className={cn("text-display tabular", TONE_TEXT[tone])}>{value}</span>
      {hint ? <span className="text-small">{hint}</span> : null}
    </div>
  );
}
