"use client";

import { useQuery } from "@tanstack/react-query";
import { Coins } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { BackOfficeShell } from "@/components/back-office-shell";
import { MetricCard } from "@/components/metric-card";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { uk } from "@/i18n/uk";
import { formatCurrency } from "@/i18n/format";
import { budgetImpact, listDatasets } from "@/lib/api/endpoints";
import type { FindingType } from "@/lib/api/types";

export default function ReportsPage() {
  return (
    <Suspense fallback={<BackOfficeShell><p className="py-10 text-center text-small">{uk.common.loading}</p></BackOfficeShell>}>
      <ReportsPageInner />
    </Suspense>
  );
}

function ReportsPageInner() {
  const sp = useSearchParams();
  const datasetsQuery = useQuery({ queryKey: ["datasets"], queryFn: listDatasets });
  const datasetId = sp.get("dataset") ?? datasetsQuery.data?.[0]?.id;

  const impactQuery = useQuery({
    queryKey: ["budget-impact", datasetId],
    queryFn: () => budgetImpact(datasetId!),
    enabled: !!datasetId,
  });

  return (
    <BackOfficeShell>
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-1">
          <h1 className="text-display text-ink">{uk.reports.title}</h1>
          <p className="text-small">{uk.reports.subtitle}</p>
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
            />

            <Card>
              <CardHeader>
                <CardTitle>{uk.reports.byType}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3 md:grid-cols-2">
                  {Object.entries(impactQuery.data.by_type).map(([type, value]) => (
                    <div
                      key={type}
                      className="flex items-center justify-between rounded-lg border border-ink/5 bg-sand-300/40 px-4 py-3"
                    >
                      <span className="text-ink">{uk.findingType[type as FindingType]}</span>
                      <span className="tabular font-medium text-forest-700">
                        {formatCurrency(value)}
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </BackOfficeShell>
  );
}
