import { type VariantProps, cva } from "class-variance-authority";
import * as React from "react";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
  {
    variants: {
      tone: {
        success: "border-forest/30 bg-forest/10 text-forest-700",
        warning: "border-warning/30 bg-warning/15 text-[#8C6B1F]",
        danger: "border-rose/30 bg-rose/10 text-rose-700",
        info: "border-info/30 bg-info/10 text-info",
        neutral: "border-ink/15 bg-surface-muted text-ink-muted",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, tone, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}
