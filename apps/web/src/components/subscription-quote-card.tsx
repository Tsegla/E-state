"use client";

import { Copy, Percent } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCurrency, formatInt } from "@/i18n/format";
import { uk } from "@/i18n/uk";
import type { SubscriptionQuote } from "@/lib/api/types";

interface SubscriptionQuoteCardProps {
  quote: SubscriptionQuote;
  showCopyAction?: boolean;
}

function tierLabel(tier: SubscriptionQuote["tier"]): string {
  return uk.pricing.tier[tier];
}

function purposeLabel(purpose: string): string {
  return uk.pricing.purpose[purpose as keyof typeof uk.pricing.purpose] ?? purpose;
}

function sharePercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function buildCommercialOfferText(quote: SubscriptionQuote): string {
  return [
    `${uk.pricing.resultTitle}`,
    `${uk.pricing.yearlyPrice}: ${formatCurrency(quote.yearly_price_uah)}`,
    `${uk.pricing.projectedRevenue}: ${formatCurrency(quote.projected_recoverable_revenue_uah)}`,
    `${uk.pricing.concentrationShare}: ${sharePercent(quote.top10_percent_area_share)}`,
    `${uk.pricing.concentrationMultiplier}: ${quote.concentration_multiplier.toFixed(2)}x`,
    `${uk.pricing.totalParcels}: ${formatInt(quote.total_parcels)}`,
    `${uk.pricing.totalOwners}: ${formatInt(quote.total_owners)}`,
    `${uk.pricing.totalArea}: ${quote.total_area_ha.toLocaleString("uk-UA", {
      maximumFractionDigits: 2,
    })}`,
  ].join("\n");
}

export function SubscriptionQuoteCard({
  quote,
  showCopyAction = false,
}: SubscriptionQuoteCardProps) {
  const [copied, setCopied] = useState(false);
  const concentrationWidth = Math.max(2, Math.min(100, quote.top10_percent_area_share * 100));

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle>{uk.pricing.resultTitle}</CardTitle>
            <CardDescription>{uk.pricing.resultHint}</CardDescription>
          </div>
          <span className="rounded-full border border-ink/10 bg-surface-muted px-3 py-1 text-xs font-medium text-ink">
            {tierLabel(quote.tier)}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-xl border border-ink/10 bg-surface-muted p-4">
            <p className="text-xs text-ink-muted">{uk.pricing.yearlyPrice}</p>
            <p className="mt-1 text-2xl font-semibold text-forest-700">
              {formatCurrency(quote.yearly_price_uah)}
            </p>
          </div>
          <div className="rounded-xl border border-ink/10 bg-surface-muted p-4">
            <p className="text-xs text-ink-muted">{uk.pricing.projectedRevenue}</p>
            <p className="mt-1 text-2xl font-semibold text-ink">
              {formatCurrency(quote.projected_recoverable_revenue_uah)}
            </p>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <Stat label={uk.pricing.totalParcels} value={formatInt(quote.total_parcels)} />
          <Stat label={uk.pricing.totalOwners} value={formatInt(quote.total_owners)} />
          <Stat
            label={uk.pricing.totalArea}
            value={quote.total_area_ha.toLocaleString("uk-UA", { maximumFractionDigits: 2 })}
          />
        </div>

        <div className="rounded-xl border border-ink/10 p-4">
          <div className="mb-2 flex items-center gap-2">
            <Percent className="h-4 w-4 text-ink-muted" />
            <p className="text-sm font-semibold text-ink">{uk.pricing.concentrationTitle}</p>
          </div>
          <p className="text-xs text-ink-muted">{uk.pricing.concentrationHint}</p>
          <div className="mt-3 h-2 rounded-full bg-surface-muted">
            <div
              className="h-2 rounded-full bg-forest"
              style={{ width: `${concentrationWidth}%` }}
              aria-label={uk.pricing.concentrationShare}
            />
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-4 text-sm text-ink">
            <span>
              {uk.pricing.concentrationShare}:{" "}
              <strong>{sharePercent(quote.top10_percent_area_share)}</strong>
            </span>
            <span>
              {uk.pricing.concentrationMultiplier}:{" "}
              <strong>{quote.concentration_multiplier.toFixed(2)}x</strong>
            </span>
          </div>
        </div>

        <div className="rounded-xl border border-ink/10 p-4">
          <p className="text-sm font-semibold text-ink">{uk.pricing.revenueByPurpose}</p>
          <div className="mt-3 grid gap-2 md:grid-cols-2">
            {Object.entries(quote.revenue_by_purpose).map(([purpose, value]) => (
              <div
                key={purpose}
                className="flex items-center justify-between rounded-lg bg-surface-muted px-3 py-2 text-sm"
              >
                <span>{purposeLabel(purpose)}</span>
                <span className="font-medium text-forest-700">{formatCurrency(value)}</span>
              </div>
            ))}
          </div>
        </div>

        {quote.caveats.length > 0 && (
          <div className="rounded-xl border border-ink/10 p-4">
            <p className="text-sm font-semibold text-ink">{uk.pricing.caveatsTitle}</p>
            <ul className="mt-2 space-y-1 text-xs text-ink-muted">
              {quote.caveats.map((caveat) => (
                <li key={caveat}>- {caveat}</li>
              ))}
            </ul>
          </div>
        )}

        {showCopyAction && (
          <div className="flex items-center justify-end gap-3">
            {copied && <span className="text-xs text-forest-700">{uk.pricing.copied}</span>}
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                void navigator.clipboard.writeText(buildCommercialOfferText(quote));
                setCopied(true);
                window.setTimeout(() => setCopied(false), 2000);
              }}
            >
              <Copy className="h-4 w-4" />
              {uk.pricing.copyOffer}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-ink/10 bg-surface-muted p-3">
      <p className="text-xs text-ink-muted">{label}</p>
      <p className="mt-1 text-lg font-semibold text-ink">{value}</p>
    </div>
  );
}
