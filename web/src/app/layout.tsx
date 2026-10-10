import type { Metadata } from "next";
// Fonts are bundled from npm so the build never depends on fetching them from Google.
import "@fontsource/ibm-plex-sans/400.css";
import "@fontsource/ibm-plex-sans/500.css";
import "@fontsource/ibm-plex-sans/600.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import { Suspense } from "react";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { StockSelector } from "@/components/StockSelector";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "SentiFi", template: "%s · SentiFi" },
  description:
    "How Wall Street analysts, news media and Reddit feel about a stock, with a 5-day direction forecast and its track record.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col font-sans">
        {/* Header and selector read ?symbol=, so they render on the client inside Suspense. */}
        <Suspense fallback={<div className="h-[69px] border-b border-line bg-card" />}>
          <Header />
        </Suspense>
        <main className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col gap-6 p-6">
          <Suspense fallback={<div className="h-11" />}>
            <StockSelector />
          </Suspense>
          <Suspense>{children}</Suspense>
          <Footer />
        </main>
      </body>
    </html>
  );
}
