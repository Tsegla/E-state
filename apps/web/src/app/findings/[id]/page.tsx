"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Building2, ClipboardCheck, MapPinned, UserPlus } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { BackOfficeShell } from "@/components/back-office-shell";
import { SeverityBadge, StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { uk } from "@/i18n/uk";
import { formatArea, formatDate, formatDateTime } from "@/i18n/format";
import { assignFindingToInspector, getFinding } from "@/lib/api/endpoints";

export default function FindingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [showAssignForm, setShowAssignForm] = useState(false);
  const [assignNote, setAssignNote] = useState("");

  const findingQuery = useQuery({
    queryKey: ["finding", id],
    queryFn: () => getFinding(id),
    enabled: !!id,
  });

  const assignMut = useMutation({
    mutationFn: () =>
      assignFindingToInspector(id, { note: assignNote.trim() || null }),
    onSuccess: (detail) => {
      queryClient.setQueryData(["finding", id], detail);
      queryClient.invalidateQueries({ queryKey: ["findings"] });
      queryClient.invalidateQueries({ queryKey: ["inspector"] });
      setShowAssignForm(false);
      setAssignNote("");
    },
  });

  const finding = findingQuery.data;
  const canAssign = finding?.status === "open";

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

            {finding.assigned_at ? (
              <Card className="border-forest-700/20 bg-surface-muted">
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-h2">
                    <ClipboardCheck className="h-4 w-4 text-forest-700" />
                    {uk.findings.detail.assignedBanner}
                  </CardTitle>
                  <CardDescription className="text-small">
                    {formatDateTime(finding.assigned_at)}
                  </CardDescription>
                </CardHeader>
                {finding.assignment_note ? (
                  <CardContent>
                    <p className="text-meta">
                      {uk.findings.detail.assignedNotePrefix}
                    </p>
                    <p className="whitespace-pre-wrap text-small text-ink">
                      {finding.assignment_note}
                    </p>
                  </CardContent>
                ) : null}
              </Card>
            ) : null}

            <Card>
              <CardHeader>
                <CardTitle className="text-h2">{uk.findings.detail.actions}</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                {showAssignForm ? (
                  <form
                    className="flex flex-col gap-3"
                    onSubmit={(e) => {
                      e.preventDefault();
                      assignMut.mutate();
                    }}
                  >
                    <div className="flex flex-col gap-1.5">
                      <Label htmlFor="assign-note">
                        {uk.findings.detail.assignNoteLabel}
                      </Label>
                      <Textarea
                        id="assign-note"
                        rows={4}
                        maxLength={2000}
                        placeholder={uk.findings.detail.assignNotePlaceholder}
                        value={assignNote}
                        onChange={(e) => setAssignNote(e.target.value)}
                      />
                    </div>
                    {assignMut.error ? (
                      <p className="text-sm text-rose-700">
                        {(assignMut.error as Error).message}
                      </p>
                    ) : null}
                    <div className="flex flex-wrap items-center gap-2">
                      <Button type="submit" disabled={assignMut.isPending}>
                        {assignMut.isPending
                          ? uk.common.loading
                          : uk.findings.detail.assignConfirm}
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        onClick={() => {
                          setShowAssignForm(false);
                          setAssignNote("");
                        }}
                      >
                        {uk.findings.detail.assignCancel}
                      </Button>
                    </div>
                  </form>
                ) : (
                  <div className="flex flex-col gap-2">
                    <Button
                      type="button"
                      onClick={() => setShowAssignForm(true)}
                      disabled={!canAssign}
                    >
                      <UserPlus className="h-4 w-4" />
                      {uk.findings.detail.assignInspector}
                    </Button>
                    {!canAssign ? (
                      <p className="text-meta">
                        {uk.findings.detail.assignOnlyFromOpen}
                      </p>
                    ) : null}
                  </div>
                )}
              </CardContent>
            </Card>

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
