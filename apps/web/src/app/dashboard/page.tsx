"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  ChevronRight,
  Clock,
  FileText,
  FolderOpen,
  Info,
  Upload,
} from "lucide-react";
import Link from "next/link";

import { BackOfficeShell } from "@/components/back-office-shell";
import { MetricCard } from "@/components/metric-card";
import { SeverityBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { formatDateTime, formatInt } from "@/i18n/format";
import { uk } from "@/i18n/uk";
import { listDatasets, listFindings } from "@/lib/api/endpoints";
import type { FindingSummary, Severity } from "@/lib/api/types";

const SEVERITY_ORDER: Record<Severity, number> = {
  critical: 0,
  warning: 1,
  info: 2,
};

export default function DashboardPage() {
  const datasetsQuery = useQuery({
    queryKey: ["datasets"],
    queryFn: listDatasets,
  });

  const latest = datasetsQuery.data?.[0];

  const findingsQuery = useQuery({
    queryKey: ["findings", latest?.id, "summary"],
    queryFn: () => listFindings({ datasetId: latest!.id, limit: 25 }),
    enabled: !!latest?.id,
  });

  const countsQuery = useQuery({
    queryKey: ["findings", latest?.id, "counts"],
    queryFn: async () => {
      if (!latest) return { critical: 0, warning: 0, info: 0 };
      const [critical, warning, info] = await Promise.all([
        listFindings({ datasetId: latest.id, severity: "critical", limit: 1 }),
        listFindings({ datasetId: latest.id, severity: "warning", limit: 1 }),
        listFindings({ datasetId: latest.id, severity: "info", limit: 1 }),
      ]);
      return {
        critical: critical.meta?.total ?? 0,
        warning: warning.meta?.total ?? 0,
        info: info.meta?.total ?? 0,
      };
    },
    enabled: !!latest?.id,
  });

  const findingsTotal = findingsQuery.data?.meta?.total ?? latest?.findings_total ?? 0;
  const totalRecords = latest ? latest.zem_rows + latest.ner_rows : 0;
  const detectionRate =
    totalRecords > 0 ? ((findingsTotal / totalRecords) * 100).toFixed(1) : "0.0";
  const detectionRateHint = uk.dashboard.detectionRateHint.replace("{rate}", detectionRate);

  const recentFindings: FindingSummary[] = (findingsQuery.data?.data ?? [])
    .slice()
    .sort(
      (a, b) =>
        SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity] ||
        new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime(),
    )
    .slice(0, 4);

  return (
    <BackOfficeShell>
      <div className="flex flex-col gap-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="flex flex-col gap-1">
            <span className="text-[11px] font-medium uppercase tracking-wider text-ink-muted">
              {uk.eyebrow.dashboard}
            </span>
            <h1 className="text-display text-ink">{uk.app.name}</h1>
            <p className="text-small">{uk.dashboard.subtitle}</p>
          </div>
          <Button asChild variant="secondary" size="md">
            <Link href="/upload" className="flex items-center gap-2">
              <Upload className="h-4 w-4" />
              {uk.nav.upload}
            </Link>
          </Button>
        </div>

        {datasetsQuery.isLoading ? (
          <div className="rounded-2xl border border-ink/[0.06] bg-surface p-10 text-center text-small shadow-card">
            {uk.common.loading}
          </div>
        ) : !latest ? (
          <Card>
            <CardHeader>
              <CardTitle>{uk.dashboard.noDataset}</CardTitle>
              <CardDescription>{uk.upload.subtitle}</CardDescription>
            </CardHeader>
            <CardFooter>
              <Button asChild>
                <Link href="/upload">{uk.dashboard.uploadCta}</Link>
              </Button>
            </CardFooter>
          </Card>
        ) : (
          <>
            <section className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
              <div className="flex flex-col justify-between gap-6 rounded-2xl border border-rose/25 bg-rose/[0.06] p-7 shadow-card">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex flex-col gap-1">
                    <span className="text-[11px] font-medium uppercase tracking-wider text-rose-700">
                      {uk.dashboard.requiresAttention}
                    </span>
                    <span className="text-sm text-ink-muted">
                      {uk.dashboard.metrics.findings}
                    </span>
                  </div>
                  <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-rose/15 text-rose-700">
                    <AlertTriangle className="h-5 w-5" />
                  </span>
                </div>
                <div className="flex flex-col gap-2">
                  <span className="text-[72px] font-semibold leading-none tabular text-rose-700">
                    {formatInt(findingsTotal)}
                  </span>
                  <span className="text-sm text-ink-muted">{detectionRateHint}</span>
                </div>
                <Button asChild variant="primary" size="lg" className="w-fit">
                  <Link
                    href={`/findings?dataset=${latest.id}`}
                    className="flex items-center gap-2"
                  >
                    {uk.dashboard.actions.openFindings}
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
              </div>

              <div className="flex flex-col gap-4">
                <MetricCard
                  icon={<FileText className="h-4 w-4" />}
                  label={uk.dashboard.metrics.totalRecords}
                  value={formatInt(totalRecords)}
                />
                <MetricCard
                  icon={<FolderOpen className="h-4 w-4" />}
                  label={uk.dashboard.metrics.landParcels}
                  value={formatInt(latest.zem_rows)}
                />
              </div>
            </section>

            <section className="grid gap-4 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
              <Card>
                <CardHeader className="flex-row items-start justify-between gap-4 space-y-0">
                  <div className="flex flex-col gap-1">
                    <CardTitle className="text-h2">{uk.dashboard.recentHeading}</CardTitle>
                    <CardDescription>{uk.dashboard.recentHint}</CardDescription>
                  </div>
                  <Link
                    href={`/findings?dataset=${latest.id}`}
                    className="flex items-center gap-1 text-sm font-medium text-forest-700 hover:underline"
                  >
                    {uk.dashboard.actions.openFindings}
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </CardHeader>
                <CardContent className="flex flex-col divide-y divide-ink/[0.06] p-0">
                  {recentFindings.length === 0 ? (
                    <p className="px-6 py-8 text-center text-small">
                      {uk.findings.empty}
                    </p>
                  ) : (
                    recentFindings.map((finding) => (
                      <Link
                        key={finding.id}
                        href={`/findings/${finding.id}`}
                        className="group flex cursor-pointer items-center justify-between gap-4 px-6 py-4 transition-colors hover:bg-surface-muted focus-visible:bg-surface-muted focus-visible:outline-none"
                      >
                        <div className="flex min-w-0 items-center gap-3">
                          <SeverityBadge severity={finding.severity} />
                          <div className="flex min-w-0 flex-col gap-0.5">
                            <span className="truncate text-sm font-medium text-ink">
                              {uk.findingType[finding.finding_type]}
                            </span>
                            <span className="truncate text-xs text-ink-muted">
                              {finding.person_tax_id_masked ?? "—"} ·{" "}
                              {formatDateTime(finding.detected_at)}
                            </span>
                          </div>
                        </div>
                        <ChevronRight className="h-4 w-4 flex-shrink-0 text-ink-muted transition-colors group-hover:text-ink" />
                      </Link>
                    ))
                  )}
                </CardContent>
              </Card>

              <div className="flex flex-col gap-4">
                <div className="flex flex-col gap-2 rounded-2xl border border-ink/[0.06] bg-surface p-6 shadow-card">
                  <span className="text-[11px] font-medium uppercase tracking-wider text-ink-muted">
                    {uk.dashboard.detectionRateLabel}
                  </span>
                  <div className="flex items-baseline gap-2">
                    <span className="text-4xl font-semibold tabular text-ink">
                      {detectionRate}%
                    </span>
                  </div>
                  <span className="text-sm text-ink-muted">{detectionRateHint}</span>
                </div>
                <div className="flex flex-col gap-3 rounded-2xl border border-ink/[0.06] bg-surface p-6 shadow-card">
                  <div className="flex items-center gap-2 text-[11px] font-medium uppercase tracking-wider text-ink-muted">
                    <Clock className="h-3.5 w-3.5" />
                    {uk.dashboard.lastDataset}
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <span className="text-lg font-semibold text-ink">
                      {formatDateTime(latest.uploaded_at)}
                    </span>
                    <span className="text-sm text-ink-muted">{latest.label}</span>
                  </div>
                </div>
              </div>
            </section>

            <section className="grid gap-4 md:grid-cols-3">
              <MetricCard
                label={uk.dashboard.metrics.critical}
                value={formatInt(countsQuery.data?.critical)}
                tone="critical"
                hint={uk.dashboard.metrics.criticalHint}
                icon={<AlertTriangle className="h-4 w-4" />}
              />
              <MetricCard
                label={uk.dashboard.metrics.warning}
                value={formatInt(countsQuery.data?.warning)}
                tone="warning"
                hint={uk.dashboard.metrics.warningHint}
                icon={<AlertTriangle className="h-4 w-4" />}
              />
              <MetricCard
                label={uk.dashboard.metrics.info}
                value={formatInt(countsQuery.data?.info)}
                hint={uk.dashboard.metrics.infoHint}
                icon={<Info className="h-4 w-4" />}
              />
            </section>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-h2">
                  <Info className="h-5 w-5 text-ink-muted" />
                  {uk.dashboard.legend.title}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="flex flex-col gap-2 text-small text-ink/80">
                  <li>{uk.dashboard.legend.dzk}</li>
                  <li>{uk.dashboard.legend.drrp}</li>
                  <li>{uk.dashboard.legend.findings}</li>
                </ul>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </BackOfficeShell>
  );
}
