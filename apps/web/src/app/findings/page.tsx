"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";

import { BackOfficeShell } from "@/components/back-office-shell";
import { SeverityBadge, StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { uk } from "@/i18n/uk";
import { formatDateTime, formatArea } from "@/i18n/format";
import { listDatasets, listFindings } from "@/lib/api/endpoints";
import type { FindingStatus, FindingSummary, Severity } from "@/lib/api/types";

const SEVERITY_OPTIONS: (Severity | "")[] = ["", "critical", "warning", "info"];
const STATUS_OPTIONS: (FindingStatus | "")[] = ["", "open", "in_review", "resolved", "dismissed"];

function metricsPreview(finding: FindingSummary): string {
  const m = finding.computed_metrics;
  if (finding.finding_type === "AREA_PORTFOLIO_DELTA") {
    const ratio = Number(m.ratio);
    const delta = Number(m.delta_m2);
    return `Δ ${formatArea(delta)} (×${ratio.toFixed(2)})`;
  }
  if (finding.finding_type === "LAND_NO_REAL_ESTATE") {
    return `${formatArea(Number(m.total_residential_m2))}`;
  }
  if (finding.finding_type === "OWNER_NAME_MISMATCH") {
    return `${Number(m.similarity).toFixed(2)} схожість`;
  }
  if (finding.finding_type === "DUPLICATE_REGISTRATION") {
    return `${m.distinct_owners} власника(ів)`;
  }
  if (finding.finding_type === "TERMINATED_BUT_ACTIVE") {
    return `${m.active_parcels} активних ділянок`;
  }
  return Object.entries(m)
    .slice(0, 2)
    .map(([k, v]) => `${k}: ${v}`)
    .join(" · ");
}

export default function FindingsPage() {
  return (
    <Suspense fallback={<BackOfficeShell><p className="py-10 text-center text-small">{uk.common.loading}</p></BackOfficeShell>}>
      <FindingsPageInner />
    </Suspense>
  );
}

function FindingsPageInner() {
  const searchParams = useSearchParams();
  const datasetFromQuery = searchParams.get("dataset") ?? undefined;

  const [severity, setSeverity] = useState<Severity | "">("");
  const [status, setStatus] = useState<FindingStatus | "">("");

  const datasetsQuery = useQuery({ queryKey: ["datasets"], queryFn: listDatasets });
  const datasetId = useMemo(
    () => datasetFromQuery ?? datasetsQuery.data?.[0]?.id,
    [datasetFromQuery, datasetsQuery.data],
  );

  const findingsQuery = useQuery({
    queryKey: ["findings", datasetId, severity, status],
    queryFn: () =>
      listFindings({
        datasetId: datasetId!,
        severity: severity || undefined,
        status: status || undefined,
        limit: 100,
      }),
    enabled: !!datasetId,
  });

  const rows = findingsQuery.data ?? [];
  const dataset = datasetsQuery.data?.find((d) => d.id === datasetId);

  return (
    <BackOfficeShell>
      <div className="flex flex-col gap-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="flex flex-col gap-1">
            <h1 className="text-display text-ink">{uk.findings.title}</h1>
            <p className="text-small">
              {dataset ? `${dataset.label} · ${formatDateTime(dataset.uploaded_at)}` : uk.common.loading}
            </p>
          </div>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-h2">{uk.findings.filters.severity}</CardTitle>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-small">
              {SEVERITY_OPTIONS.map((s) => (
                <Button
                  key={s || "all"}
                  size="sm"
                  variant={severity === s ? "primary" : "secondary"}
                  onClick={() => setSeverity(s)}
                >
                  {s ? uk.severity[s] : uk.findings.filters.all}
                </Button>
              ))}
              <span className="mx-2 text-ink/20">|</span>
              {STATUS_OPTIONS.map((s) => (
                <Button
                  key={s || "all-status"}
                  size="sm"
                  variant={status === s ? "primary" : "secondary"}
                  onClick={() => setStatus(s)}
                >
                  {s ? uk.status[s] : uk.findings.filters.all}
                </Button>
              ))}
            </div>
          </CardHeader>
          <CardContent>
            {findingsQuery.isLoading ? (
              <p className="py-10 text-center text-small">{uk.common.loading}</p>
            ) : rows.length === 0 ? (
              <p className="py-10 text-center text-small">{uk.findings.empty}</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{uk.findings.columns.severity}</TableHead>
                    <TableHead>{uk.findings.columns.type}</TableHead>
                    <TableHead>{uk.findings.columns.person}</TableHead>
                    <TableHead>{uk.findings.columns.metrics}</TableHead>
                    <TableHead>{uk.findings.columns.status}</TableHead>
                    <TableHead>{uk.findings.columns.detected}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((finding) => (
                    <TableRow
                      key={finding.id}
                      className="cursor-pointer"
                      onClick={() => {
                        window.location.href = `/findings/${finding.id}`;
                      }}
                    >
                      <TableCell>
                        <SeverityBadge severity={finding.severity} />
                      </TableCell>
                      <TableCell className="font-medium">
                        <Link className="hover:underline" href={`/findings/${finding.id}`}>
                          {uk.findingType[finding.finding_type]}
                        </Link>
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {finding.person_tax_id_masked}
                      </TableCell>
                      <TableCell className="text-small">{metricsPreview(finding)}</TableCell>
                      <TableCell>
                        <StatusBadge status={finding.status} />
                      </TableCell>
                      <TableCell className="text-small">{formatDateTime(finding.detected_at)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </BackOfficeShell>
  );
}
