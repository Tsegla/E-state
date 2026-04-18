"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowLeft, Camera, LocateFixed } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { BackOfficeShell } from "@/components/back-office-shell";
import { SeverityBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { uk } from "@/i18n/uk";
import { createInspectorVisit, getFinding } from "@/lib/api/endpoints";
import type { FindingStatus } from "@/lib/api/types";

export default function InspectorFindingPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [actualObjectType, setActualObjectType] = useState("");
  const [actualAreaM2, setActualAreaM2] = useState<string>("");
  const [actualUse, setActualUse] = useState("");
  const [notes, setNotes] = useState("");
  const [gps, setGps] = useState<{ lat: number; lng: number } | null>(null);
  const [resolution, setResolution] = useState<FindingStatus>("resolved");

  const findingQuery = useQuery({
    queryKey: ["finding", id],
    queryFn: () => getFinding(id),
    enabled: !!id,
  });

  const visitMut = useMutation({
    mutationFn: () =>
      createInspectorVisit({
        finding_id: id,
        actual_object_type: actualObjectType || null,
        actual_area_m2: actualAreaM2 ? Number(actualAreaM2) : null,
        actual_use: actualUse || null,
        notes: notes || null,
        gps,
        resolution,
      }),
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

  if (findingQuery.isLoading || !findingQuery.data) {
    return (
      <BackOfficeShell>
        <p className="py-10 text-center text-small">{uk.common.loading}</p>
      </BackOfficeShell>
    );
  }

  const finding = findingQuery.data;

  return (
    <BackOfficeShell>
      <div className="mx-auto flex max-w-xl flex-col gap-4">
        <Link href="/inspector" className="inline-flex items-center gap-1.5 text-small hover:text-forest-700">
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
              {finding.person_tax_id_masked}
            </CardDescription>
          </CardHeader>
          <CardContent className="text-small">
            <dl className="grid grid-cols-2 gap-2">
              {Object.entries(finding.computed_metrics).slice(0, 4).map(([k, v]) => (
                <div key={k}>
                  <dt className="text-meta">{k}</dt>
                  <dd className="truncate text-ink">{Array.isArray(v) ? v.join(", ") : String(v)}</dd>
                </div>
              ))}
            </dl>
          </CardContent>
        </Card>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            visitMut.mutate();
          }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="text-h2">{uk.nav.inspector}</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="actual-type">{uk.inspector.form.actualObjectType}</Label>
                <Input
                  id="actual-type"
                  value={actualObjectType}
                  onChange={(e) => setActualObjectType(e.target.value)}
                  placeholder="житловий будинок"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="actual-area">{uk.inspector.form.actualArea}</Label>
                <Input
                  id="actual-area"
                  type="number"
                  inputMode="decimal"
                  step="0.01"
                  value={actualAreaM2}
                  onChange={(e) => setActualAreaM2(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="actual-use">{uk.inspector.form.actualUse}</Label>
                <Input
                  id="actual-use"
                  value={actualUse}
                  onChange={(e) => setActualUse(e.target.value)}
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
              <Button type="button" variant="ghost" disabled className="w-full justify-start">
                <Camera className="h-4 w-4" />
                {uk.inspector.form.photos}
                <span className="ml-auto text-meta">MVP: coming soon</span>
              </Button>
              {visitMut.error ? (
                <p className="text-sm text-rose-700">{(visitMut.error as Error).message}</p>
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
