"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  Building2,
  Camera,
  CheckCircle2,
  ClipboardList,
  LocateFixed,
  MapPinned,
} from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { BackOfficeShell } from "@/components/back-office-shell";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { uk } from "@/i18n/uk";
import { formatArea, formatDate, formatDateTime } from "@/i18n/format";
import { createInspectorVisit, getInspectorFinding } from "@/lib/api/endpoints";
import type {
  FindingDetail,
  FindingEvidence,
  FindingStatus,
  SourceOfTruth,
} from "@/lib/api/types";

const DZK_FIELDS: Array<{ key: string; label: string }> = [
  { key: "cadastral_no", label: "Кадастровий номер" },
  { key: "intended_use_label", label: "Цільове використання" },
  { key: "area_m2", label: "Площа, м²" },
  { key: "owner_name_raw", label: "Власник (ДЗК)" },
  { key: "location_admin", label: "Розташування" },
  { key: "agri_use_kind", label: "Фактичне використання" },
  { key: "registered_at", label: "Зареєстровано" },
];

const DRRP_FIELDS: Array<{ key: string; label: string }> = [
  { key: "object_type_raw", label: "Тип об'єкта" },
  { key: "object_type_norm", label: "Категорія" },
  { key: "address_raw", label: "Адреса" },
  { key: "area_m2", label: "Площа, м²" },
  { key: "owner_name_raw", label: "Власник (ДРРП)" },
  { key: "registered_at", label: "Зареєстровано" },
  { key: "terminated_at", label: "Припинено" },
];

function formatSnapshotValue(key: string, value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (key.includes("area") && typeof value !== "boolean") {
    const n = Number(value);
    if (!Number.isNaN(n)) return formatArea(n);
  }
  if (key.endsWith("_at") && typeof value === "string") {
    return formatDate(value);
  }
  return String(value);
}

function snapshotsDiffer(
  a: Record<string, unknown> | undefined,
  b: Record<string, unknown> | undefined,
  key: string,
): boolean {
  if (!a || !b) return false;
  const av = a[key];
  const bv = b[key];
  if (av === undefined && bv === undefined) return false;
  if (av === null && bv === null) return false;
  if (typeof av === "number" || typeof bv === "number") {
    return Number(av) !== Number(bv);
  }
  return String(av ?? "") !== String(bv ?? "");
}

function truthValuesFromEvidence(ev: FindingEvidence): {
  object_type: string;
  area_m2: string;
  use: string;
} {
  const s = ev.snapshot;
  if (ev.kind === "land_parcel") {
    return {
      object_type: String(s.intended_use_label ?? s.intended_use_code ?? ""),
      area_m2: s.area_m2 != null ? String(s.area_m2) : "",
      use: String(s.agri_use_kind ?? s.intended_use_label ?? ""),
    };
  }
  return {
    object_type: String(s.object_type_raw ?? s.object_type_norm ?? ""),
    area_m2: s.area_m2 != null ? String(s.area_m2) : "",
    use: String(s.object_type_norm ?? s.object_type_raw ?? ""),
  };
}

export default function InspectorFindingPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const findingQuery = useQuery({
    queryKey: ["inspector-finding", id],
    queryFn: () => getInspectorFinding(id),
    enabled: !!id,
  });
  const finding: FindingDetail | undefined = findingQuery.data;

  const dzkEvidence = useMemo(
    () => finding?.evidence.filter((e) => e.kind === "land_parcel") ?? [],
    [finding],
  );
  const drrpEvidence = useMemo(
    () => finding?.evidence.filter((e) => e.kind === "real_estate") ?? [],
    [finding],
  );

  const [truthSource, setTruthSource] = useState<SourceOfTruth | null>(null);
  const [truthEvidenceId, setTruthEvidenceId] = useState<string | null>(null);
  const [actualObjectType, setActualObjectType] = useState("");
  const [actualAreaM2, setActualAreaM2] = useState<string>("");
  const [actualUse, setActualUse] = useState("");
  const [notes, setNotes] = useState("");
  const [gps, setGps] = useState<{ lat: number; lng: number } | null>(null);
  const [resolution, setResolution] = useState<FindingStatus>("resolved");
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (!truthSource || !truthEvidenceId || truthSource === "field_override") return;
    const ev = finding?.evidence.find((e) => e.id === truthEvidenceId);
    if (!ev) return;
    const vals = truthValuesFromEvidence(ev);
    setActualObjectType(vals.object_type);
    setActualAreaM2(vals.area_m2);
    setActualUse(vals.use);
  }, [truthSource, truthEvidenceId, finding]);

  const chooseEvidence = (ev: FindingEvidence) => {
    setTruthSource(ev.kind === "land_parcel" ? "dzk" : "drrp");
    setTruthEvidenceId(ev.id);
    setValidationError(null);
  };

  const chooseFieldOverride = () => {
    setTruthSource("field_override");
    setTruthEvidenceId(null);
    setValidationError(null);
  };

  const visitMut = useMutation({
    mutationFn: () => {
      if (!truthSource) {
        throw new Error(uk.inspector.form.truthSourceRequired);
      }
      if (truthSource !== "field_override" && !truthEvidenceId) {
        throw new Error(uk.inspector.form.truthEvidenceRequired);
      }
      return createInspectorVisit({
        finding_id: id,
        actual_object_type: actualObjectType || null,
        actual_area_m2: actualAreaM2 ? Number(actualAreaM2) : null,
        actual_use: actualUse || null,
        notes: notes || null,
        gps,
        resolution,
        source_of_truth: truthSource,
        truth_evidence_id:
          truthSource === "field_override" ? null : truthEvidenceId,
      });
    },
    onSuccess: () => {
      router.push("/inspector");
    },
  });

  const requestLocation = () => {
    if (typeof window === "undefined" || !navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => setGps({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => setGps(null),
      { enableHighAccuracy: true, timeout: 10_000 },
    );
  };

  if (findingQuery.isLoading || !finding) {
    return (
      <BackOfficeShell>
        <p className="py-10 text-center text-small">{uk.common.loading}</p>
      </BackOfficeShell>
    );
  }

  const fieldsReadOnly =
    truthSource === "dzk" || truthSource === "drrp";
  const primaryDzk = dzkEvidence[0]?.snapshot;
  const primaryDrrp = drrpEvidence[0]?.snapshot;

  return (
    <BackOfficeShell>
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        <Link
          href="/inspector"
          className="inline-flex items-center gap-1.5 text-small hover:text-forest-700"
        >
          <ArrowLeft className="h-4 w-4" />
          {uk.findings.detail.backToList}
        </Link>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-start justify-between gap-2">
              <span>{uk.findingType[finding.finding_type]}</span>
              <SeverityBadge severity={finding.severity} />
            </CardTitle>
            <CardDescription className="font-mono text-xs">
              {finding.person_tax_id_masked} · {finding.person_name_masked}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-2 text-small">
            <dl className="grid grid-cols-2 gap-2">
              {Object.entries(finding.computed_metrics)
                .slice(0, 4)
                .map(([k, v]) => (
                  <div key={k}>
                    <dt className="text-meta">{k}</dt>
                    <dd className="truncate text-ink">
                      {Array.isArray(v) ? v.join(", ") : String(v)}
                    </dd>
                  </div>
                ))}
            </dl>
          </CardContent>
        </Card>

        {finding.assigned_at ? (
          <Card className="border-forest-700/20 bg-surface-muted">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-h2">
                <ClipboardList className="h-4 w-4 text-forest-700" />
                {uk.inspector.assignedNote}
              </CardTitle>
              <CardDescription className="text-small">
                {formatDateTime(finding.assigned_at)}
              </CardDescription>
            </CardHeader>
            {finding.assignment_note ? (
              <CardContent>
                <p className="whitespace-pre-wrap text-small text-ink">
                  {finding.assignment_note}
                </p>
              </CardContent>
            ) : null}
          </Card>
        ) : null}

        <section className="flex flex-col gap-2">
          <h2 className="text-h1 text-ink">{uk.inspector.compare.title}</h2>
          <p className="text-meta">{uk.inspector.compare.mismatchHint}</p>
          <div className="grid gap-3 md:grid-cols-2">
            <EvidenceColumn
              header={uk.inspector.compare.dzkHeader}
              icon={<MapPinned className="h-4 w-4 text-forest-700" />}
              evidence={dzkEvidence}
              fields={DZK_FIELDS}
              otherSide={primaryDrrp}
              selectedId={truthSource === "dzk" ? truthEvidenceId : null}
              onChoose={chooseEvidence}
            />
            <EvidenceColumn
              header={uk.inspector.compare.drrpHeader}
              icon={<Building2 className="h-4 w-4 text-forest-700" />}
              evidence={drrpEvidence}
              fields={DRRP_FIELDS}
              otherSide={primaryDzk}
              selectedId={truthSource === "drrp" ? truthEvidenceId : null}
              onChoose={chooseEvidence}
            />
          </div>
        </section>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            setValidationError(null);
            try {
              visitMut.mutate();
            } catch (err) {
              setValidationError((err as Error).message);
            }
          }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="text-h2">{uk.nav.inspector}</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex flex-col gap-2">
                <Label>{uk.inspector.form.truthSource}</Label>
                <p className="text-meta">{uk.inspector.form.truthSourceHint}</p>
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant={truthSource === "dzk" ? "primary" : "secondary"}
                    disabled={dzkEvidence.length === 0}
                    onClick={() => {
                      if (dzkEvidence[0]) chooseEvidence(dzkEvidence[0]);
                    }}
                  >
                    {uk.inspector.form.truthSourceDzk}
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant={truthSource === "drrp" ? "primary" : "secondary"}
                    disabled={drrpEvidence.length === 0}
                    onClick={() => {
                      if (drrpEvidence[0]) chooseEvidence(drrpEvidence[0]);
                    }}
                  >
                    {uk.inspector.form.truthSourceDrrp}
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant={
                      truthSource === "field_override" ? "primary" : "secondary"
                    }
                    onClick={chooseFieldOverride}
                  >
                    {uk.inspector.form.truthSourceField}
                  </Button>
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="actual-type">
                  {uk.inspector.form.actualObjectType}
                </Label>
                <Input
                  id="actual-type"
                  value={actualObjectType}
                  onChange={(e) => setActualObjectType(e.target.value)}
                  placeholder="житловий будинок"
                  readOnly={fieldsReadOnly}
                  aria-readonly={fieldsReadOnly}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="actual-area">
                  {uk.inspector.form.actualArea}
                </Label>
                <Input
                  id="actual-area"
                  type="number"
                  inputMode="decimal"
                  step="0.01"
                  value={actualAreaM2}
                  onChange={(e) => setActualAreaM2(e.target.value)}
                  readOnly={fieldsReadOnly}
                  aria-readonly={fieldsReadOnly}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="actual-use">{uk.inspector.form.actualUse}</Label>
                <Input
                  id="actual-use"
                  value={actualUse}
                  onChange={(e) => setActualUse(e.target.value)}
                  readOnly={fieldsReadOnly}
                  aria-readonly={fieldsReadOnly}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="notes">{uk.inspector.form.notes}</Label>
                <Textarea
                  id="notes"
                  rows={4}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  maxLength={2000}
                />
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Button type="button" variant="secondary" onClick={requestLocation}>
                  <LocateFixed className="h-4 w-4" />
                  {uk.inspector.form.useLocation}
                </Button>
                {gps ? (
                  <span className="text-small tabular">
                    {gps.lat.toFixed(5)}, {gps.lng.toFixed(5)}
                  </span>
                ) : null}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Label>{uk.inspector.form.resolution}</Label>
                <Button
                  type="button"
                  size="sm"
                  variant={resolution === "resolved" ? "primary" : "secondary"}
                  onClick={() => setResolution("resolved")}
                >
                  <CheckCircle2 className="h-4 w-4" />
                  {uk.inspector.form.resolvedOption}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant={resolution === "in_review" ? "primary" : "secondary"}
                  onClick={() => setResolution("in_review")}
                >
                  {uk.inspector.form.inReviewOption}
                </Button>
              </div>
              <Button
                type="button"
                variant="ghost"
                disabled
                className="w-full justify-start"
              >
                <Camera className="h-4 w-4" />
                {uk.inspector.form.photos}
                <span className="ml-auto text-meta">MVP: coming soon</span>
              </Button>
              {validationError ? (
                <p className="text-sm text-rose-700">{validationError}</p>
              ) : null}
              {visitMut.error ? (
                <p className="text-sm text-rose-700">
                  {(visitMut.error as Error).message}
                </p>
              ) : null}
              {resolution === "resolved" && truthSource ? (
                <p className="text-meta">
                  {uk.inspector.form.sentToMaster}
                </p>
              ) : null}
            </CardContent>
            <CardFooter>
              <Button type="submit" disabled={visitMut.isPending}>
                {visitMut.isPending ? uk.common.loading : uk.inspector.form.submit}
              </Button>
            </CardFooter>
          </Card>
        </form>
      </div>
    </BackOfficeShell>
  );
}

interface EvidenceColumnProps {
  header: string;
  icon: React.ReactNode;
  evidence: FindingEvidence[];
  fields: Array<{ key: string; label: string }>;
  otherSide: Record<string, unknown> | undefined;
  selectedId: string | null;
  onChoose: (ev: FindingEvidence) => void;
}

function EvidenceColumn({
  header,
  icon,
  evidence,
  fields,
  otherSide,
  selectedId,
  onChoose,
}: EvidenceColumnProps) {
  if (evidence.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-h2">
            {icon}
            {header}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-meta">{uk.inspector.compare.noEvidence}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {evidence.map((ev) => {
        const selected = ev.id === selectedId;
        return (
          <Card
            key={ev.id}
            className={
              selected
                ? "border-forest-700 ring-2 ring-forest-700/30"
                : "border-ink/5"
            }
          >
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-h2">
                {icon}
                {header}
              </CardTitle>
              <CardDescription className="font-mono text-xs">
                {String(
                  ev.snapshot.cadastral_no ??
                    ev.snapshot.address_raw ??
                    ev.ref_id,
                )}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <dl className="grid grid-cols-1 gap-1.5 text-small">
                {fields.map(({ key, label }) => {
                  const differs = snapshotsDiffer(ev.snapshot, otherSide, key);
                  return (
                    <div key={key} className="flex flex-col gap-0.5">
                      <dt className="text-meta">{label}</dt>
                      <dd
                        className={
                          differs
                            ? "rounded bg-rose/10 px-1.5 py-0.5 text-ink"
                            : "text-ink"
                        }
                      >
                        {formatSnapshotValue(key, ev.snapshot[key])}
                      </dd>
                    </div>
                  );
                })}
              </dl>
              <Button
                type="button"
                size="sm"
                variant={selected ? "primary" : "secondary"}
                onClick={() => onChoose(ev)}
              >
                {selected
                  ? uk.inspector.compare.chosenAsTruth
                  : uk.inspector.compare.chooseAsTruth}
              </Button>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
