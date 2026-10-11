import { Suspense } from "react";
import { StockSelector } from "@/components/StockSelector";

/** The product pages: every one of them is about the stock chosen in the selector. */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col gap-6 p-6">
      {/* The selector reads ?symbol=, so it renders on the client inside Suspense. */}
      <Suspense fallback={<div className="h-11" />}>
        <StockSelector />
      </Suspense>
      <Suspense>{children}</Suspense>
    </main>
  );
}
