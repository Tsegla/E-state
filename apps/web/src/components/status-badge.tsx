"use client";

import {
  Circle,
  CircleCheck,
  CircleSlash,
  Clock,
  Info,
  OctagonAlert,
  TriangleAlert,
} from "lucide-react";
import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { uk } from "@/i18n/uk";
import type { FindingStatus, Severity } from "@/lib/api/types";

interface SeverityBadgeProps {
  severity: Severity;
}

const SEVERITY_MAP = {
  critical: { tone: "danger" as const, Icon: OctagonAlert },
  warning: { tone: "warning" as const, Icon: TriangleAlert },
  info: { tone: "info" as const, Icon: Info },
};

export function SeverityBadge({ severity }: SeverityBadgeProps) {
  const { tone, Icon } = SEVERITY_MAP[severity];
  return (
    <Badge tone={tone}>
      <Icon className="h-3.5 w-3.5" strokeWidth={2} />
      {uk.severity[severity]}
    </Badge>
  );
}

type IconComponent = typeof Circle;

const STATUS_MAP: Record<FindingStatus, { tone: "info" | "warning" | "success" | "neutral"; Icon: IconComponent }> = {
  open: { tone: "info", Icon: Circle },
  in_review: { tone: "warning", Icon: Clock },
  resolved: { tone: "success", Icon: CircleCheck },
  dismissed: { tone: "neutral", Icon: CircleSlash },
};

export function StatusBadge({ status }: { status: FindingStatus }) {
  const { tone, Icon } = STATUS_MAP[status];
  return (
    <Badge tone={tone}>
      <Icon className="h-3.5 w-3.5" strokeWidth={2} />
      {uk.status[status]}
    </Badge>
  );
}
