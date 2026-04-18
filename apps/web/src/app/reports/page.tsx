"use client";

import { useQuery } from "@tanstack/react-query";
import { Coins, Download, FileSpreadsheet, Info } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { BackOfficeShell } from "@/components/back-office-shell";
import { MetricCard } from "@/components/metric-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { uk } from "@/i18n/uk";
import { formatCurrency, formatDateTimeUtc } from "@/i18n/format";
import {
  budgetImpact,
  downloadExecutivePdf,
  downloadFindingsCsv,
  downloadFindingsXlsx,
  executiveSummary,
  listDatasets,
} from "@/lib/api/endpoints";
import type { FindingType } from "@/lib/api/types";

export default function ReportsPage() {
  return (
    <Suspense fallback={<BackOfficeShell><p className="py-10 text-center text-small">{uk.common.loading}</p></BackOfficeShell>}>
      <ReportsPageInner />
    </Suspense>
  );
}

function ReportsPageInner() {
  const handleDownloadError = (error: unknown) => {
    const message = error instanceof Error ? error.message : uk.common.error;
    window.alert(message);
  };
  const sp = useSearchParams();
  const datasetsQuery = useQuery({ queryKey: ["datasets"], queryFn: listDatasets });
  const datasetId = sp.get("dataset") ?? datasetsQuery.data?.[0]?.id;

  const impactQuery = useQuery({
    queryKey: ["budget-impact", datasetId],
    queryFn: () => budgetImpact(datasetId!),
    enabled: !!datasetId,
  });
  const summaryQuery = useQuery({
    queryKey: ["executive-summary", datasetId],
    queryFn: () => executiveSummary({ datasetId: datasetId! }),
    enabled: !!datasetId,
  });
  const reportGeneratedAt =
    latestDateTime(summaryQuery.data?.metadata.generated_at, impactQuery.data?.generated_at) ?? null;

  return (
    <BackOfficeShell>
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-1">
          <span className="text-[11px] font-medium uppercase tracking-wider text-ink-muted">
            {uk.eyebrow.reports}
          </span>
          <h1 className="text-display text-ink">{uk.reports.title}</h1>
          <p className="text-small">{uk.reports.subtitle}</p>
          {reportGeneratedAt && (
            <p className="text-meta text-ink-muted">
              {uk.reports.generatedAt}: {formatDateTimeUtc(reportGeneratedAt)}
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            size="sm"
            disabled={!datasetId}
            onClick={async () => {
              if (!datasetId) return;
              try {
                await downloadFindingsCsv({ datasetId });
              } catch (error) {
                handleDownloadError(error);
              }
            }}
          >
            <Download className="h-4 w-4" />
            {uk.reports.actions.downloadCsv}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            disabled={!datasetId}
            onClick={async () => {
              if (!datasetId) return;
              try {
                await downloadFindingsXlsx({ datasetId });
              } catch (error) {
                handleDownloadError(error);
              }
            }}
          >
            <FileSpreadsheet className="h-4 w-4" />
            {uk.reports.actions.downloadXlsx}
          </Button>
          <Button
            variant="primary"
            size="sm"
            disabled={!datasetId}
            onClick={async () => {
              if (!datasetId) return;
              try {
                await downloadExecutivePdf({ datasetId });
              } catch (error) {
                handleDownloadError(error);
              }
            }}
          >
            <Download className="h-4 w-4" />
            {uk.reports.actions.downloadPdf}
          </Button>
        </div>

        {!impactQuery.data ? (
          <Card>
            <CardHeader>
              <CardTitle>{uk.common.loading}</CardTitle>
              <CardDescription>{uk.reports.empty}</CardDescription>
            </CardHeader>
          </Card>
        ) : (
          <>
            <MetricCard
              label={uk.reports.totalPerYear}
              value={formatCurrency(impactQuery.data.total_uah_per_year)}
              tone="success"
              icon={<Coins className="h-5 w-5" />}
              hint={uk.reports.totalPerYearHint}
            />
            <div className="grid gap-3 md:grid-cols-3">
              <MetricCard
                label={uk.reports.unresolvedFindings}
                value={impactQuery.data.unresolved_findings.toLocaleString("uk-UA")}
                hint={uk.reports.unresolvedFindingsHint}
              />
              <MetricCard
                label={uk.reports.resolvedFindings}
                value={impactQuery.data.resolved_findings.toLocaleString("uk-UA")}
                hint={uk.reports.resolvedFindingsHint}
              />
              <MetricCard
                label={uk.reports.verifiedAssets}
                value={impactQuery.data.used_verified_assets.toLocaleString("uk-UA")}
                hint={uk.reports.verifiedAssetsHint}
              />
            </div>

            <Card>
              <CardHeader>
                <CardTitle>{uk.reports.byType}</CardTitle>
                <CardDescription>{uk.reports.byTypeHint}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3 md:grid-cols-2">
                  {Object.entries(impactQuery.data.by_type).map(([type, value]) => (
                    <div
                      key={type}
                      className="flex items-center justify-between rounded-lg border border-ink/5 bg-sand-300/40 px-4 py-3"
                    >
                      <span className="text-ink">{uk.findingType[type as FindingType] ?? type}</span>
                      <span className="tabular font-medium text-forest-700">
                        {formatCurrency(value)}
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {summaryQuery.data && (
              <Card>
                <CardHeader>
                  <CardTitle>{uk.reports.topLocalitiesTitle}</CardTitle>
                  <CardDescription>{uk.reports.topLocalitiesHint}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-3 md:grid-cols-2">
                    {summaryQuery.data.top_localities.map((item) => (
                      <div
                        key={item.koatuu}
                        className="flex items-center justify-between rounded-lg border border-ink/5 bg-sand-300/40 px-4 py-3"
                      >
                        <span className="font-mono text-xs text-ink-muted">{item.koatuu}</span>
                        <span className="tabular font-medium text-ink">{item.findings}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-h2">
                  <Info className="h-5 w-5 text-forest-700" />
                  {uk.reports.methodologyTitle}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-small text-ink/80">{uk.reports.methodology}</p>
                {impactQuery.data.caveats.length > 0 && (
                  <ul className="mt-3 space-y-1 text-meta text-ink/70">
                    {impactQuery.data.caveats.map((caveat) => (
                      <li key={caveat}>- {caveat}</li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </BackOfficeShell>
  );
}

function latestDateTime(...values: Array<string | null | undefined>): string | undefined {
  const dates = values
    .filter((value): value is string => Boolean(value))
    .map((value) => ({ raw: value, date: new Date(value) }))
    .filter((item) => !Number.isNaN(item.date.getTime()))
    .sort((a, b) => b.date.getTime() - a.date.getTime());
  return dates[0]?.raw;
}
