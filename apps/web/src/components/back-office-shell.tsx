"use client";

import {
  BriefcaseBusiness,
  Calculator,
  FileBarChart2,
  LayoutDashboard,
  ListFilter,
  UploadCloud,
  Users,
} from "lucide-react";
import { usePathname } from "next/navigation";
import type * as React from "react";

import { AppShell } from "@/components/app-shell";
import { uk } from "@/i18n/uk";

const exactRoutes = new Set(["/upload", "/dashboard", "/pricing", "/reports", "/citizen"]);
const prefixRoutes = ["/findings", "/inspector"];

export function BackOfficeShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const activeHref = [...exactRoutes, ...prefixRoutes].find((href) =>
    exactRoutes.has(href) ? pathname === href : pathname.startsWith(href),
  );

  return (
    <AppShell
      activeHref={activeHref}
      nav={[
        {
          href: "/upload",
          label: uk.nav.upload,
          icon: <UploadCloud className="h-4 w-4" />,
        },
        {
          href: "/dashboard",
          label: uk.nav.dashboard,
          icon: <LayoutDashboard className="h-4 w-4" />,
        },
        { href: "/pricing", label: uk.nav.pricing, icon: <Calculator className="h-4 w-4" /> },
        { href: "/findings", label: uk.nav.findings, icon: <ListFilter className="h-4 w-4" /> },
        { href: "/reports", label: uk.nav.reports, icon: <FileBarChart2 className="h-4 w-4" /> },
        {
          href: "/inspector",
          label: uk.nav.inspector,
          icon: <BriefcaseBusiness className="h-4 w-4" />,
        },
        { href: "/citizen", label: uk.nav.citizen, icon: <Users className="h-4 w-4" /> },
      ]}
    >
      {children}
    </AppShell>
  );
}
