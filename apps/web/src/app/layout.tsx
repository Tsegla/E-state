import { Inter } from "next/font/google";
import type { Metadata } from "next";
import type * as React from "react";

import { QueryProvider } from "@/components/query-provider";
import { uk } from "@/i18n/uk";

import "./globals.css";

const inter = Inter({
  subsets: ["latin", "cyrillic"],
  variable: "--font-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: `${uk.app.name} — ${uk.app.tagline}`,
  description:
    "Автоматична звірка ДЗК та ДРРП для об'єднаних територіальних громад України.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="uk" className={inter.variable}>
      <body className="antialiased">
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
