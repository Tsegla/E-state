"use client";

import { FileBarChart2, LayoutDashboard, ListFilter, UploadCloud } from "lucide-react";
import { usePathname } from "next/navigation";
import type * as React from "react";

import { AppShell } from "@/components/app-shell";
import { uk } from "@/i18n/uk";

export function BackOfficeShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const activeHref = [
    "/",
    "/upload",
    "/findings",
    "/reports",
    "/inspector",
    "/citizen",
  ].find((href) => (href === "/" ? pathname === "/" : pathname.startsWith(href)));

  return (
    <AppShell
      activeHref={activeHref}
      nav={[
        { href: "/", label: uk.nav.dashboard, icon: <LayoutDashboard className="h-4 w-4" /> },
        { href: "/upload", label: uk.nav.upload, icon: <UploadCloud className="h-4 w-4" /> },
        { href: "/findings", label: uk.nav.findings, icon: <ListFilter className="h-4 w-4" /> },
        { href: "/reports", label: uk.nav.reports, icon: <FileBarChart2 className="h-4 w-4" /> },
        { href: "/inspector", label: uk.nav.inspector },
        { href: "/citizen", label: uk.nav.citizen },
      ]}
    >
      {children}
    </AppShell>
  );
}
