"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Database, Files, Upload, Users } from "lucide-react";
import Link from "next/link";

import { BackOfficeShell } from "@/components/back-office-shell";
import { MetricCard } from "@/components/metric-card";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { uk } from "@/i18n/uk";
import { formatDateTime, formatInt } from "@/i18n/format";
import { listDatasets, listFindings } from "@/lib/api/endpoints";

export default function DashboardPage() {
  const datasetsQuery = useQuery({
    queryKey: ["datasets"],
    queryFn: listDatasets,
  });

  const latest = datasetsQuery.data?.[0];

  const findingsQuery = useQuery({
    queryKey: ["findings", latest?.id, "summary"],
    queryFn: () => listFindings({ datasetId: latest!.id, limit: 1 }),
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
        critical: critical.length,
        warning: warning.length,
        info: info.length,
      };
    },
    enabled: !!latest?.id,
  });

  const findingsTotal = findingsQuery.data ? latest?.findings_total ?? 0 : latest?.findings_total ?? 0;

  return (
    <BackOfficeShell>
      <div className="flex flex-col gap-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="flex flex-col gap-1">
            <h1 className="text-display text-ink">{uk.dashboard.title}</h1>
            <p className="text-small">{uk.dashboard.subtitle}</p>
          </div>
          <Button asChild variant="primary">
            <Link href="/upload" className="flex items-center gap-2">
              <Upload className="h-4 w-4" />
              {uk.nav.upload}
            </Link>
          </Button>
        </div>

        {datasetsQuery.isLoading ? (
          <div className="rounded-xl border border-ink/5 bg-surface p-10 text-center text-small shadow-soft">
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
            <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <MetricCard
                label={uk.dashboard.metrics.landParcels}
                value={formatInt(latest.zem_rows)}
                icon={<Database className="h-5 w-5" />}
              />
              <MetricCard
                label={uk.dashboard.metrics.realEstate}
                value={formatInt(latest.ner_rows)}
                icon={<Files className="h-5 w-5" />}
              />
              <MetricCard
                label={uk.dashboard.metrics.persons}
                value={formatInt(latest.zem_rows + latest.ner_rows)}
                icon={<Users className="h-5 w-5" />}
                hint={`Набір: ${latest.label}`}
              />
              <MetricCard
                label={uk.dashboard.metrics.findings}
                value={formatInt(findingsTotal)}
                tone="critical"
                icon={<AlertTriangle className="h-5 w-5" />}
              />
            </section>

            <section className="grid gap-4 md:grid-cols-3">
              <MetricCard
                label={uk.dashboard.metrics.critical}
                value={formatInt(countsQuery.data?.critical)}
                tone="critical"
              />
              <MetricCard
                label={uk.dashboard.metrics.warning}
                value={formatInt(countsQuery.data?.warning)}
                tone="warning"
              />
              <MetricCard
                label={uk.dashboard.metrics.info}
                value={formatInt(countsQuery.data?.info)}
              />
            </section>

            <Card>
              <CardHeader>
                <CardTitle>{uk.dashboard.lastDataset}</CardTitle>
                <CardDescription>
                  {latest.label} · {formatDateTime(latest.uploaded_at)}
                </CardDescription>
              </CardHeader>
              <CardFooter className="flex flex-wrap gap-2">
                <Button asChild variant="primary">
                  <Link href={`/findings?dataset=${latest.id}`}>
                    {uk.dashboard.actions.openFindings}
                  </Link>
                </Button>
                <Button asChild variant="secondary">
                  <Link href={`/reports?dataset=${latest.id}`}>
                    {uk.dashboard.actions.budgetImpact}
                  </Link>
                </Button>
              </CardFooter>
            </Card>
          </>
        )}
      </div>
    </BackOfficeShell>
  );
}
