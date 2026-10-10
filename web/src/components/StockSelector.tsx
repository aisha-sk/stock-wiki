"use client";

import { usePathname, useRouter } from "next/navigation";
import { useSelectedStock } from "@/lib/useSelectedStock";
import { ErrorCard } from "./ui/ErrorCard";

export function StockSelector() {
  const router = useRouter();
  const pathname = usePathname();
  const { tickers, selected, requested, isFallback } = useSelectedStock();

  if (tickers.status === "loading") {
    return <div className="h-11 w-72 animate-pulse rounded-full bg-line" aria-label="Loading stocks" />;
  }
  if (tickers.status === "error") {
    return <ErrorCard what="the stock list" error={tickers.error} onRetry={tickers.reload} />;
  }

  return (
    <div className="flex flex-col gap-2">
      <div role="group" aria-label="Choose a stock" className="flex flex-wrap items-center gap-2">
      <span className="mr-2 text-sm text-muted">Tracking</span>
      {tickers.data.tickers.map((ticker) => {
        const active = ticker.symbol === selected?.symbol;
        return (
          <button
            key={ticker.symbol}
            title={ticker.name}
            aria-pressed={active}
            onClick={() => router.replace(`${pathname}?symbol=${ticker.symbol}`, { scroll: false })}
            className={`min-h-11 rounded-full border px-5 text-[15px] font-medium ${
              active ? "border-ink bg-ink text-white" : "border-control bg-card text-ink hover:border-ink"
            }`}
          >
            {ticker.symbol}
          </button>
        );
      })}
      </div>
      {isFallback && selected && (
        <p role="status" className="text-[13px] text-muted">
          We don&apos;t track {requested}. Showing {selected.symbol} instead.
        </p>
      )}
    </div>
  );
}
