import { type VariantProps, cva } from "class-variance-authority";
import * as React from "react";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
  {
    variants: {
      tone: {
        success: "border-forest/20 bg-forest/10 text-forest-700",
        warning: "border-warning/25 bg-warning/12 text-[#8C6B1F]",
        danger: "border-rose/25 bg-rose/10 text-rose-700",
        info: "border-info/25 bg-info/10 text-info",
        neutral: "border-ink/10 bg-surface-muted text-ink-muted",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

const DOT_COLOR: Record<NonNullable<VariantProps<typeof badgeVariants>["tone"]>, string> = {
  success: "bg-forest",
  warning: "bg-warning",
  danger: "bg-rose",
  info: "bg-info",
  neutral: "bg-ink-muted",
};

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  /** Render a small leading status dot instead of an icon-child. */
  dot?: boolean;
}

export function Badge({ className, tone, dot, children, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ tone }), className)} {...props}>
      {dot ? (
        <span
          aria-hidden
          className={cn("inline-block h-1.5 w-1.5 rounded-full", DOT_COLOR[tone ?? "neutral"])}
        />
      ) : null}
      {children}
    </span>
  );
}
