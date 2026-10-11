import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import { Suspense } from "react";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { StockSelector } from "@/components/StockSelector";
import "./globals.css";

const plexSans = IBM_Plex_Sans({
  variable: "--font-plex-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: { default: "SentiFi", template: "%s · SentiFi" },
  description:
    "How Wall Street analysts, news media and Reddit feel about a stock, with a 5-day large-move forecast and its track record.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${plexSans.variable} ${plexMono.variable} h-full antialiased`}>
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
