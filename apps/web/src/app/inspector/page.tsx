"use client";

import { useQuery } from "@tanstack/react-query";
import { ClipboardList } from "lucide-react";
import Link from "next/link";

import { BackOfficeShell } from "@/components/back-office-shell";
import { SeverityBadge } from "@/components/status-badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { uk } from "@/i18n/uk";
import { formatDateTime } from "@/i18n/format";
import { inspectorFindings, listDatasets } from "@/lib/api/endpoints";

export default function InspectorQueuePage() {
  const datasetsQuery = useQuery({ queryKey: ["datasets"], queryFn: listDatasets });
  const datasetId = datasetsQuery.data?.[0]?.id;

  const findingsQuery = useQuery({
    queryKey: ["inspector", datasetId],
    queryFn: () => inspectorFindings(datasetId!),
    enabled: !!datasetId,
  });

  const rows = findingsQuery.data ?? [];

  return (
    <BackOfficeShell>
      <div className="mx-auto flex max-w-xl flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-display text-ink flex items-center gap-2">
            <ClipboardList className="h-6 w-6 text-forest-700" />
            {uk.inspector.title}
          </h1>
          <p className="text-small">{uk.inspector.subtitle}</p>
        </div>
        {findingsQuery.isLoading ? (
          <p className="py-10 text-center text-small">{uk.common.loading}</p>
        ) : rows.length === 0 ? (
          <p className="py-10 text-center text-small">{uk.inspector.empty}</p>
        ) : (
          rows.map((r) => (
            <Link key={r.id} href={`/inspector/${r.id}`}>
              <Card className="transition-transform hover:-translate-y-0.5 hover:shadow-lg">
                <CardHeader>
                  <CardTitle className="flex items-start justify-between gap-2 text-h2">
                    <div className="flex flex-col gap-0.5">
                      <span>{r.person_name || "—"}</span>
                      <span className="text-small font-normal text-meta">
                        {uk.findingType[r.finding_type]}
                      </span>
                    </div>
                    <SeverityBadge severity={r.severity} />
                  </CardTitle>
                  <CardDescription className="font-mono text-xs">
                    {r.person_tax_id_masked}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex items-center justify-between text-small">
                  <span>{formatDateTime(r.detected_at)}</span>
                </CardContent>
              </Card>
            </Link>
          ))
        )}
      </div>
    </BackOfficeShell>
  );
}
