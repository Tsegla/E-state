"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Building2, MapPinned } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { BackOfficeShell } from "@/components/back-office-shell";
import { SeverityBadge, StatusBadge } from "@/components/status-badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { uk } from "@/i18n/uk";
import { formatArea, formatDate, formatDateTime } from "@/i18n/format";
import { getFinding } from "@/lib/api/endpoints";

export default function FindingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const findingQuery = useQuery({
    queryKey: ["finding", id],
    queryFn: () => getFinding(id),
    enabled: !!id,
  });

  const finding = findingQuery.data;

  return (
    <BackOfficeShell>
      <div className="flex flex-col gap-6">
        <div>
          <Link
            href="/findings"
            className="inline-flex items-center gap-1.5 text-small hover:text-forest-700"
          >
            <ArrowLeft className="h-4 w-4" />
            {uk.findings.detail.backToList}
          </Link>
        </div>
        {findingQuery.isLoading || !finding ? (
          <p className="py-10 text-center text-small">{uk.common.loading}</p>
        ) : (
          <>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex flex-col gap-2">
                <h1 className="text-display text-ink">
                  {uk.findingType[finding.finding_type]}
                </h1>
                <div className="flex flex-wrap items-center gap-2">
                  <SeverityBadge severity={finding.severity} />
                  <StatusBadge status={finding.status} />
                  <span className="font-mono text-xs text-ink-muted">
                    {finding.person_tax_id_masked}
                  </span>
                  <span className="text-small">· {finding.person_name_masked}</span>
                  <span className="text-small">· {formatDateTime(finding.detected_at)}</span>
                </div>
              </div>
            </div>

            <section className="grid gap-4 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="text-h2">{uk.findings.detail.metrics}</CardTitle>
                </CardHeader>
                <CardContent>
                  <dl className="grid grid-cols-2 gap-3 text-small">
                    {Object.entries(finding.computed_metrics).map(([key, value]) => (
                      <div key={key} className="flex flex-col gap-0.5">
                        <dt className="text-meta">{key}</dt>
                        <dd className="text-ink">
                          {typeof value === "number" ? value.toLocaleString("uk-UA") : Array.isArray(value) ? value.join(", ") : String(value)}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </CardContent>
              </Card>
            </section>

            <section>
              <h2 className="mb-3 text-h1 text-ink">{uk.findings.detail.evidence}</h2>
              <div className="grid gap-3 md:grid-cols-2">
                {finding.evidence.map((ev, idx) => (
                  <Card key={`${ev.kind}-${ev.ref_id}-${idx}`}>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-h2">
                        {ev.kind === "land_parcel" ? (
                          <MapPinned className="h-4 w-4 text-forest-700" />
                        ) : (
                          <Building2 className="h-4 w-4 text-forest-700" />
                        )}
                        {ev.kind === "land_parcel" ? "Земельна ділянка" : "Нерухомість"}
                      </CardTitle>
                      <CardDescription className="font-mono text-xs">
                        {String(ev.snapshot.cadastral_no ?? ev.snapshot.address_raw ?? "—")}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <dl className="grid grid-cols-2 gap-2 text-small">
                        {Object.entries(ev.snapshot).map(([key, value]) => (
                          <div key={key}>
                            <dt className="text-meta">{key}</dt>
                            <dd className="truncate text-ink">
                              {key.includes("area")
                                ? formatArea(Number(value))
                                : key.includes("_at") && typeof value === "string"
                                  ? formatDate(value)
                                  : String(value ?? "—")}
                            </dd>
                          </div>
                        ))}
                      </dl>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </section>
          </>
        )}
      </div>
    </BackOfficeShell>
  );
}
