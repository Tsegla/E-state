"use client";

import { useMutation } from "@tanstack/react-query";
import { ArrowRight, Loader2, UploadCloud } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { SubscriptionQuoteCard } from "@/components/subscription-quote-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { uk } from "@/i18n/uk";
import { subscriptionQuoteFromUpload } from "@/lib/api/endpoints";
import type { SubscriptionQuote } from "@/lib/api/types";

export default function PricingPage() {
  const [file, setFile] = useState<File | null>(null);
  const [quote, setQuote] = useState<SubscriptionQuote | null>(null);

  const quoteMutation = useMutation({
    mutationFn: (selectedFile: File) => subscriptionQuoteFromUpload(selectedFile),
    onSuccess: (data) => setQuote(data),
  });

  return (
    <main className="min-h-screen bg-surface-muted px-4 py-8 lg:px-8">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
        <section className="rounded-2xl border border-ink/[0.06] bg-surface p-8 shadow-card">
          <h1 className="text-display text-ink">{uk.pricing.title}</h1>
          <p className="mt-3 text-small">{uk.pricing.subtitle}</p>
        </section>

        <Card>
          <CardHeader>
            <CardTitle>{uk.pricing.uploadTitle}</CardTitle>
            <CardDescription>{uk.pricing.uploadHint}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <label className="flex cursor-pointer flex-col items-center gap-3 rounded-2xl border-2 border-dashed border-ink/15 bg-surface-muted px-6 py-10 text-center hover:border-forest/40">
              <UploadCloud className="h-8 w-8 text-ink-muted" />
              <span className="text-sm text-ink">
                {file?.name ?? uk.pricing.uploadHint}
              </span>
              <input
                type="file"
                accept=".xlsx,.xls,.csv"
                className="hidden"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
            </label>

            <div className="flex flex-wrap items-center justify-between gap-3">
              <Button
                type="button"
                disabled={!file || quoteMutation.isPending}
                onClick={() => {
                  if (!file) return;
                  quoteMutation.mutate(file);
                }}
              >
                {quoteMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {uk.pricing.uploading}
                  </>
                ) : (
                  <>
                    {uk.pricing.uploadCta}
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </Button>

              <div className="flex gap-2">
                <Button asChild variant="secondary">
                  <Link href="/dashboard">{uk.pricing.openDashboard}</Link>
                </Button>
                <Button asChild variant="ghost">
                  <a href="mailto:team@e-state.local">{uk.pricing.contact}</a>
                </Button>
              </div>
            </div>

            {quoteMutation.error ? (
              <p className="text-sm text-rose-700">
                {quoteMutation.error instanceof Error
                  ? quoteMutation.error.message
                  : uk.common.error}
              </p>
            ) : null}
          </CardContent>
        </Card>

        {quote && <SubscriptionQuoteCard quote={quote} />}
      </div>
    </main>
  );
}
