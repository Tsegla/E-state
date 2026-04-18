"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";

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
const FINDINGS_PAGE_SIZE = 100;

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
  const router = useRouter();
  const searchParams = useSearchParams();
  const datasetFromQuery = searchParams.get("dataset") ?? undefined;

  const [severity, setSeverity] = useState<Severity | "">("");
  const [status, setStatus] = useState<FindingStatus | "">("");
  const [page, setPage] = useState(1);

  const datasetsQuery = useQuery({ queryKey: ["datasets"], queryFn: listDatasets });
  const datasetId = useMemo(
    () => datasetFromQuery ?? datasetsQuery.data?.[0]?.id,
    [datasetFromQuery, datasetsQuery.data],
  );

  const findingsQuery = useQuery({
    queryKey: ["findings", datasetId, severity, status, page],
    queryFn: () =>
      listFindings({
        datasetId: datasetId!,
        severity: severity || undefined,
        status: status || undefined,
        page,
        limit: FINDINGS_PAGE_SIZE,
      }),
    enabled: !!datasetId,
  });

  useEffect(() => {
    setPage(1);
  }, [datasetId, severity, status]);

  const rows = findingsQuery.data?.data ?? [];
  const total = findingsQuery.data?.meta?.total ?? rows.length;
  const shownStart = total === 0 ? 0 : (page - 1) * FINDINGS_PAGE_SIZE + 1;
  const shownEnd = total === 0 ? 0 : Math.min(page * FINDINGS_PAGE_SIZE, total);
  const canGoPrev = page > 1;
  const canGoNext = shownEnd < total;
  const dataset = datasetsQuery.data?.find((d) => d.id === datasetId);

  return (
    <BackOfficeShell>
      <div className="flex flex-col gap-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="flex flex-col gap-1">
            <h1 className="text-display text-ink">{uk.findings.title}</h1>
            <p className="text-small">{uk.findings.subtitle}</p>
            <p className="text-meta text-ink-muted">
              {dataset ? `${dataset.label} · ${formatDateTime(dataset.uploaded_at)}` : uk.common.loading}
            </p>
          </div>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-h2">{uk.findings.filtersTitle}</CardTitle>
            <p className="text-small text-ink/70">{uk.findings.filtersHint}</p>
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
            <p className="mt-3 text-meta text-ink-muted">
              {uk.findings.pagination.showing
                .replace("{start}", String(shownStart))
                .replace("{end}", String(shownEnd))
                .replace("{total}", String(total))}
            </p>
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
                      onClick={() => router.push(`/findings/${finding.id}`)}
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
            <div className="mt-4 flex items-center justify-end gap-2">
              <Button
                size="sm"
                variant="secondary"
                disabled={!canGoPrev || findingsQuery.isLoading}
                onClick={() => setPage((prev) => Math.max(1, prev - 1))}
              >
                {uk.findings.pagination.prev}
              </Button>
              <Button
                size="sm"
                variant="secondary"
                disabled={!canGoNext || findingsQuery.isLoading}
                onClick={() => setPage((prev) => prev + 1)}
              >
                {uk.findings.pagination.next}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </BackOfficeShell>
  );
}
