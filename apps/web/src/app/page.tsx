import { ArrowRight, CheckCircle2, Upload } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { uk } from "@/i18n/uk";
const landingFeatures = [
  uk.landing.features.automatedAudit,
  uk.landing.features.registryReconciliation,
  uk.landing.features.discrepancyTable,
  uk.landing.features.inspectorVerification,
  uk.landing.features.budgetImpact,
  uk.landing.features.citizenPortal,
];

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-surface-muted px-4 py-8 lg:px-8">
      <div className="mx-auto flex max-w-6xl flex-col gap-10">
        <section className="rounded-2xl border border-ink/[0.06] bg-surface p-8 shadow-card lg:p-12">
          <div className="mb-4 inline-flex rounded-full border border-forest/20 bg-forest/[0.06] px-3 py-1 text-xs font-semibold uppercase tracking-wider text-forest-700">
            {uk.landing.eyebrow}
          </div>
          <h1 className="max-w-4xl text-display text-ink">{uk.landing.title}</h1>
          <p className="mt-4 max-w-3xl text-base text-ink-muted">{uk.landing.subtitle}</p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Button asChild size="lg">
              <Link href="/dashboard" className="flex items-center gap-2">
                {uk.landing.ctaPrimary}
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button asChild variant="secondary" size="lg">
              <Link href="/upload" className="flex items-center gap-2">
                <Upload className="h-4 w-4" />
                {uk.landing.ctaSecondary}
              </Link>
            </Button>
            <Button asChild variant="ghost" size="lg">
              <Link href="/pricing">{uk.pricing.openCalculator}</Link>
            </Button>
          </div>
        </section>

        <section className="rounded-2xl border border-ink/[0.06] bg-surface p-8 shadow-card lg:p-10">
          <h2 className="text-h2 text-ink">{uk.landing.featuresTitle}</h2>
          <ul className="mt-6 grid gap-4 md:grid-cols-2">
            {landingFeatures.map((feature) => (
              <li
                key={feature.title}
                className="rounded-xl border border-ink/[0.06] bg-surface-muted p-5"
              >
                <div className="mb-2 flex items-start gap-2">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-forest-700" />
                  <h3 className="text-sm font-semibold text-ink">{feature.title}</h3>
                </div>
                <p className="text-sm text-ink-muted">{feature.description}</p>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </main>
  );
}
