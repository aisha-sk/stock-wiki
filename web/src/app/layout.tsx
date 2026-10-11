import type { Metadata } from "next";
// Fonts are bundled from npm so the build never depends on fetching them from Google.
import "@fontsource/ibm-plex-sans/400.css";
import "@fontsource/ibm-plex-sans/500.css";
import "@fontsource/ibm-plex-sans/600.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "@fontsource/newsreader/400.css";
import "@fontsource/newsreader/400-italic.css";
import "@fontsource/newsreader/500.css";
import { Suspense } from "react";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "SentiFi", template: "%s · SentiFi" },
  description:
    "See how different groups feel about a stock, how far apart they are, and a 5-day large-move forecast that is graded in public.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col font-sans">
        {/* The header reads ?symbol=, so it renders on the client inside Suspense. */}
        <Suspense fallback={<div className="h-[69px] border-b border-line bg-card" />}>
          <Header />
        </Suspense>
        <div className="flex flex-1 flex-col">{children}</div>
        <div className="mx-auto w-full max-w-[1200px] px-6">
          <Footer />
        </div>
      </body>
    </html>
  );
}
