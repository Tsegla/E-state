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

export function AppShell({ nav, activeHref, children, surface = "back-office" }: AppShellProps) {
  return (
    <div className="min-h-screen bg-surface-muted">
      <header className="border-b border-ink/5 bg-surface">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 lg:px-8">
          <Link href="/" className="flex items-baseline gap-2">
            <span className="text-h1 text-forest">{uk.app.name}</span>
            <span className="text-small hidden md:inline">{uk.app.tagline}</span>
          </Link>
          <nav className="flex items-center gap-1">
            {nav.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  activeHref === item.href
                    ? "bg-forest/10 text-forest-700"
                    : "text-ink-muted hover:bg-surface-muted hover:text-ink",
                )}
              >
                <span className="flex items-center gap-1.5">
                  {item.icon}
                  {item.label}
                </span>
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8 lg:px-8">{children}</main>
      <footer className="border-t border-ink/5 bg-surface">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2 px-4 py-4 text-small lg:px-8">
          <span>© {new Date().getFullYear()} {uk.app.name}</span>
          <span>{uk.app.footerLegal}</span>
          <Link href="/legal" className="text-forest-700 hover:underline">
            {uk.nav.legal}
          </Link>
        </div>
      </footer>
    </div>
  );
}
