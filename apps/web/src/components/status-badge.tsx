"use client";

import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { uk } from "@/i18n/uk";
import type { FindingStatus, Severity } from "@/lib/api/types";

interface SeverityBadgeProps {
  severity: Severity;
}

const SEVERITY_TONE: Record<Severity, "danger" | "warning" | "info"> = {
  critical: "danger",
  warning: "warning",
  info: "info",
};

export function SeverityBadge({ severity }: SeverityBadgeProps) {
  return (
    <Badge tone={SEVERITY_TONE[severity]} dot>
      {uk.severity[severity]}
    </Badge>
  );
}

const STATUS_TONE: Record<FindingStatus, "info" | "warning" | "success" | "neutral"> = {
  open: "info",
  in_review: "warning",
  resolved: "success",
  dismissed: "neutral",
};

export function StatusBadge({ status }: { status: FindingStatus }) {
  return (
    <Badge tone={STATUS_TONE[status]} dot>
      {uk.status[status]}
    </Badge>
  );
}
