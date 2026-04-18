import { Building2 } from "lucide-react";
import Link from "next/link";
import type * as React from "react";

import { uk } from "@/i18n/uk";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon?: React.ReactNode;
}

interface AppShellProps {
  nav: NavItem[];
  activeHref?: string;
  children: React.ReactNode;
  surface?: "back-office" | "citizen" | "inspector";
}

export function AppShell({ nav, activeHref, children }: AppShellProps) {
  return (
    <div className="min-h-screen bg-surface-muted">
      <header className="sticky top-0 z-40 border-b border-ink/[0.06] bg-surface/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-6 px-4 py-3.5 lg:px-8">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-forest text-surface shadow-[0_1px_2px_rgba(31,36,33,0.12)]">
              <Building2 className="h-[18px] w-[18px]" strokeWidth={2.25} />
            </span>
            <span className="flex flex-col leading-tight">
              <span className="text-[15px] font-semibold text-ink">{uk.app.name}</span>
              <span className="text-[11px] font-medium uppercase tracking-wide text-ink-muted">
                {uk.app.tagline}
              </span>
            </span>
          </Link>
          <nav className="flex items-center gap-1">
            {nav.map((item) => {
              const isActive = activeHref === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-sm font-medium transition-all",
                    isActive
                      ? "bg-forest text-surface shadow-[0_1px_2px_rgba(31,36,33,0.12)]"
                      : "text-ink-muted hover:bg-surface-muted hover:text-ink",
                  )}
                >
                  {item.icon}
                  <span className="hidden sm:inline">{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8 lg:px-8">{children}</main>
      <footer className="border-t border-ink/[0.06] bg-surface">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2 px-4 py-4 text-small lg:px-8">
          <span>
            © {new Date().getFullYear()} {uk.app.name}
          </span>
          <span>{uk.app.footerLegal}</span>
          <Link href="/legal" className="text-forest-700 hover:underline">
            {uk.nav.legal}
          </Link>
        </div>
      </footer>
    </div>
  );
}
