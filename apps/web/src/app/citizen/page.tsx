"use client";

import { useMutation } from "@tanstack/react-query";
import { Building2, MapPinned, ShieldCheck } from "lucide-react";
import { useState } from "react";

import { BackOfficeShell } from "@/components/back-office-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { uk } from "@/i18n/uk";
import { formatArea, formatDateTime } from "@/i18n/format";
import { citizenLookup } from "@/lib/api/endpoints";

export default function CitizenPortalPage() {
  const [taxId, setTaxId] = useState("");
  const [consent, setConsent] = useState(false);

  const mut = useMutation({
    mutationFn: () =>
      citizenLookup({ tax_id: taxId.trim(), captcha_token: "hackathon-demo", consent }),
  });

  const canSubmit = /^\d{8,10}$/.test(taxId.trim()) && consent && !mut.isPending;

  return (
    <BackOfficeShell>
      <div className="mx-auto flex max-w-2xl flex-col gap-6">
        <div className="flex flex-col gap-1">
          <h1 className="text-display text-ink">{uk.citizen.title}</h1>
          <p className="text-small">{uk.citizen.subtitle}</p>
        </div>

        <Card>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              mut.mutate();
            }}
          >
            <CardHeader>
              <CardTitle className="text-h2">{uk.citizen.taxIdLabel}</CardTitle>
              <CardDescription>{uk.citizen.captchaNote}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="tax">{uk.citizen.taxIdLabel}</Label>
                <Input
                  id="tax"
                  value={taxId}
                  onChange={(e) => setTaxId(e.target.value.replace(/\D/g, ""))}
                  inputMode="numeric"
                  maxLength={10}
                  placeholder="1234567890"
                  required
                />
              </div>
              <label className="flex items-start gap-2 text-small">
                <input
                  type="checkbox"
                  className="mt-1 h-4 w-4 rounded border-ink/30"
                  checked={consent}
                  onChange={(e) => setConsent(e.target.checked)}
                />
                <span>{uk.citizen.consentLabel}</span>
              </label>
              {mut.error ? (
                <p className="text-sm text-rose-700">{(mut.error as Error).message}</p>
              ) : null}
            </CardContent>
            <CardFooter>
              <Button type="submit" disabled={!canSubmit}>
                {mut.isPending ? uk.common.loading : uk.citizen.submit}
              </Button>
            </CardFooter>
          </form>
        </Card>

        {mut.data ? (
          <Card className="animate-fade-in">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-forest-700">
                <ShieldCheck className="h-5 w-5" />
                {uk.citizen.resultTitle}
              </CardTitle>
              <CardDescription>
                {mut.data.owner_name_masked} · {uk.citizen.labels.asOf} {formatDateTime(mut.data.last_checked_at)}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg bg-sand-300/60 p-3">
                  <div className="text-meta">{uk.citizen.labels.landParcels}</div>
                  <div className="text-h2 tabular text-ink">
                    {mut.data.assets.filter((a) => a.kind === "land_parcel").length}
                  </div>
                </div>
                <div className="rounded-lg bg-sand-300/60 p-3">
                  <div className="text-meta">{uk.citizen.labels.realEstate}</div>
                  <div className="text-h2 tabular text-ink">
                    {mut.data.assets.filter((a) => a.kind === "real_estate").length}
                  </div>
                </div>
              </div>
              <div>
                <div className="mb-2 text-meta">{uk.citizen.labels.unresolved}</div>
                <div className="text-h1 text-rose-700 tabular">
                  {mut.data.unresolved_findings}
                </div>
              </div>
              <div className="flex flex-col gap-2">
                {mut.data.assets.length === 0 ? (
                  <p className="text-small">{uk.citizen.emptyAssets}</p>
                ) : (
                  mut.data.assets.map((asset, idx) => (
                    <div
                      key={`${asset.kind}-${idx}`}
                      className="flex items-center justify-between rounded-lg border border-ink/5 bg-surface-muted px-4 py-3"
                    >
                      <div className="flex items-center gap-3">
                        {asset.kind === "land_parcel" ? (
                          <MapPinned className="h-4 w-4 text-forest-700" />
                        ) : (
                          <Building2 className="h-4 w-4 text-forest-700" />
                        )}
                        <div className="flex flex-col">
                          <span className="font-medium text-ink">{asset.label}</span>
                          {asset.location_masked ? (
                            <span className="text-small">{asset.location_masked}</span>
                          ) : null}
                        </div>
                      </div>
                      <span className="tabular text-small">{formatArea(asset.area_m2)}</span>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        ) : null}
      </div>
    </BackOfficeShell>
  );
}
