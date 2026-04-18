"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  Building2,
  ClipboardCheck,
  MapPinned,
  UserPlus,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";

import { BackOfficeShell } from "@/components/back-office-shell";
import { SeverityBadge, StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { uk } from "@/i18n/uk";
import { formatArea, formatDate, formatDateTime } from "@/i18n/format";
import { assignFindingToInspector, getFinding } from "@/lib/api/endpoints";
import type { FindingEvidence } from "@/lib/api/types";

function formatEvidenceValue(key: string, value: unknown): string {
  if (value == null || value === "") return "—";
  if (key.includes("area")) return formatArea(Number(value));
  if (key.includes("_at") && typeof value === "string") return formatDate(value);
  return String(value);
}

function normalize(value: unknown): string {
  if (value == null) return "";
  return String(value).trim().toLowerCase();
}

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

  const mismatchedKeys = useMemo(() => {
    if (!finding) return new Set<string>();
    const keys = new Set<string>();
    const [a, b] = [finding.evidence[0], finding.evidence[1]];
    if (!a || !b) return keys;
    const allKeys = new Set<string>([
      ...Object.keys(a.snapshot ?? {}),
      ...Object.keys(b.snapshot ?? {}),
    ]);
    for (const key of allKeys) {
      const va = normalize((a.snapshot as Record<string, unknown>)?.[key]);
      const vb = normalize((b.snapshot as Record<string, unknown>)?.[key]);
      if (va && vb && va !== vb) keys.add(key);
    }
    return keys;
  }, [finding]);

  return (
    <BackOfficeShell>
      <div className="flex flex-col gap-8">
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
                <span className="text-[11px] font-medium uppercase tracking-wider text-ink-muted">
                  {uk.eyebrow.detail}
                </span>
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
                  <span className="text-small">
                    · {formatDateTime(finding.detected_at)}
                  </span>
                </div>
              </div>
            </div>

            {/* Prominent mismatch banner */}
            <div className="flex items-start gap-4 rounded-2xl border border-rose/25 bg-rose/[0.06] p-5">
              <span className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl bg-rose/15 text-rose-700">
                <AlertTriangle className="h-5 w-5" />
              </span>
              <div className="flex flex-col gap-1">
                <span className="text-lg font-semibold text-rose-700">
                  {uk.findings.detail.banner.title}: {uk.findingType[finding.finding_type]}
                </span>
                <p className="text-sm text-ink">
                  {uk.findings.detail.banner.bodyByType[finding.finding_type]}
                </p>
                <p className="text-xs text-ink-muted">
                  <span className="font-medium text-ink">
                    {uk.findings.detail.banner.issueLabel}:
                  </span>{" "}
                  {uk.findingType[finding.finding_type].toLowerCase()}
                </p>
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
                    <p className="text-meta">{uk.findings.detail.assignedNotePrefix}</p>
                    <p className="whitespace-pre-wrap text-small text-ink">
                      {finding.assignment_note}
                    </p>
                  </CardContent>
                ) : null}
              </Card>
            ) : null}

            {/* Evidence comparison — balanced two-column grid with per-field diff highlighting */}
            <section>
              <h2 className="mb-3 text-h1 text-ink">{uk.findings.detail.evidence}</h2>
              <div className="grid gap-4 lg:grid-cols-2">
                {finding.evidence.map((ev, idx) => (
                  <EvidenceCard
                    key={`${ev.kind}-${ev.ref_id}-${idx}`}
                    evidence={ev}
                    mismatchedKeys={mismatchedKeys}
                  />
                ))}
              </div>
            </section>

            <section className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
              <Card>
                <CardHeader>
                  <CardTitle className="text-h2">{uk.findings.detail.metrics}</CardTitle>
                </CardHeader>
                <CardContent>
                  <dl className="grid grid-cols-2 gap-3 text-small">
                    {Object.entries(finding.computed_metrics).map(([key, value]) => (
                      <div key={key} className="flex flex-col gap-0.5">
                        <dt className="text-meta">{key}</dt>
                        <dd className="text-ink tabular">
                          {typeof value === "number"
                            ? value.toLocaleString("uk-UA")
                            : Array.isArray(value)
                              ? value.join(", ")
                              : String(value)}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </CardContent>
              </Card>

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
            </section>
          </>
        )}
      </div>
    </BackOfficeShell>
  );
}

function EvidenceCard({
  evidence,
  mismatchedKeys,
}: {
  evidence: FindingEvidence;
  mismatchedKeys: Set<string>;
}) {
  const isLand = evidence.kind === "land_parcel";
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-h2">
          {isLand ? (
            <MapPinned className="h-4 w-4 text-forest-700" />
          ) : (
            <Building2 className="h-4 w-4 text-forest-700" />
          )}
          {isLand ? "Земельна ділянка" : "Нерухомість"}
        </CardTitle>
        <CardDescription className="font-mono text-xs">
          {String(
            evidence.snapshot.cadastral_no ?? evidence.snapshot.address_raw ?? "—",
          )}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <dl className="flex flex-col divide-y divide-ink/[0.06]">
          {Object.entries(evidence.snapshot).map(([key, value]) => {
            const isMismatch = mismatchedKeys.has(key);
            return (
              <div
                key={key}
                className={cn(
                  "flex items-start justify-between gap-4 py-3 -mx-2 px-2 rounded-lg",
                  isMismatch && "bg-rose/[0.08] ring-1 ring-inset ring-rose/25",
                )}
              >
                <dt
                  className={cn(
                    "text-xs uppercase tracking-wide",
                    isMismatch ? "text-rose-700 font-medium" : "text-ink-muted",
                  )}
                >
                  {key}
                </dt>
                <dd
                  className={cn(
                    "min-w-0 flex-1 text-right text-sm tabular",
                    isMismatch ? "font-semibold text-rose-700" : "text-ink",
                  )}
                >
                  {formatEvidenceValue(key, value)}
                </dd>
              </div>
            );
          })}
        </dl>
      </CardContent>
    </Card>
  );
}
